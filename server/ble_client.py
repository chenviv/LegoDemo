import asyncio
import struct
import requests
import math
from bleak import BleakClient, BleakScanner

# BLE UUIDs from ESP32
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# Flask API endpoint
API_URL = "http://localhost:5000/api/rotation"

# Device name
DEVICE_NAME = "ESP32_MPU6050_BLE"

# Rotation state
current_rotation = {"x": 0.0, "y": 0.0, "z": 0.0}

# Axis mapping configuration
AXIS_MAPPING = {
    'unity_x': ('x', False),  # Pitch (front/back tilt)
    'unity_y': ('z', False),  # Yaw (rotation)
    'unity_z': ('y', True),  # Roll (left/right tilt)
}

class ComplementaryFilter:
    """
    Complementary filter with drift compensation
    """
    def __init__(self, alpha=0.98, gyro_deadband=2.0):
        """
        Args:
            alpha: Weight for gyroscope (0.98 = standard)
            gyro_deadband: Ignore gyro values below this (°/s) to reduce drift
        """
        self.alpha = alpha
        self.gyro_deadband = gyro_deadband
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.angle_z = 0.0
        self.stationary_counter = 0

    def update(self, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, dt=0.1):
        """
        Update filter with drift compensation
        """
        # Calculate tilt angles from accelerometer
        acc_angle_x = math.atan2(acc_y, math.sqrt(acc_x**2 + acc_z**2)) * 180 / math.pi
        acc_angle_y = math.atan2(-acc_x, math.sqrt(acc_y**2 + acc_z**2)) * 180 / math.pi

        # Apply deadband to gyroscope (ignore small values that cause drift)
        gyro_x_filtered = gyro_x if abs(gyro_x) > self.gyro_deadband else 0.0
        gyro_y_filtered = gyro_y if abs(gyro_y) > self.gyro_deadband else 0.0
        gyro_z_filtered = gyro_z if abs(gyro_z) > self.gyro_deadband else 0.0

        # Integrate gyroscope
        gyro_angle_x = self.angle_x + gyro_x_filtered * dt
        gyro_angle_y = self.angle_y + gyro_y_filtered * dt
        gyro_angle_z = self.angle_z + gyro_z_filtered * dt

        # Complementary filter
        self.angle_x = self.alpha * gyro_angle_x + (1 - self.alpha) * acc_angle_x
        self.angle_y = self.alpha * gyro_angle_y + (1 - self.alpha) * acc_angle_y

        # Yaw handling with drift compensation
        if abs(gyro_z) < self.gyro_deadband:
            self.stationary_counter += 1
            # If stationary for 2 seconds (20 updates at 100ms), slowly decay yaw
            if self.stationary_counter > 20:
                self.angle_z *= 0.98  # Decay by 2% each update
        else:
            self.stationary_counter = 0
            self.angle_z = gyro_angle_z

        # Keep yaw in range
        if self.angle_z > 360:
            self.angle_z -= 360
        elif self.angle_z < -360:
            self.angle_z += 360

        return self.angle_x, self.angle_y, self.angle_z


# Update global filter with deadband
comp_filter = ComplementaryFilter(alpha=0.98, gyro_deadband=3.0)

class SensorData:
    """Class to parse the binary sensor data from ESP32"""
    def __init__(self, data):
        # Unpack 7 floats (4 bytes each = 28 bytes total) directly into named variables
        (self.temp,
         self.acc_x, self.acc_y, self.acc_z,
         self.gyro_x, self.gyro_y, self.gyro_z) = struct.unpack('<7f', data)

    def __str__(self):
        return (f"Temp: {self.temp:.1f}°C | "
                f"Acc: X={self.acc_x:.2f} Y={self.acc_y:.2f} Z={self.acc_z:.2f} | "
                f"Gyro: X={self.gyro_x:.1f} Y={self.gyro_y:.1f} Z={self.gyro_z:.1f}")


def send_rotation_to_api():
    """Send current rotation to Flask API"""
    try:
        response = requests.post(API_URL, json=current_rotation, timeout=1)
        if response.status_code == 200:
            print(f"✓ Sent rotation: X={current_rotation['x']:.1f}° "
                  f"Y={current_rotation['y']:.1f}° Z={current_rotation['z']:.1f}°")
        else:
            print(f"✗ API error: {response.status_code}")
    except Exception as e:
        print(f"✗ Failed to send rotation: {e}")


async def notification_handler(sender, data):
    """Handle BLE notifications from ESP32"""
    try:
        # Parse the binary data
        sensor_data = SensorData(data)

        # Print raw sensor data
        print(f"RAW: {sensor_data}")

        # Apply complementary filter (returns filtered angles directly)
        angle_x, angle_y, angle_z = comp_filter.update(
            sensor_data.acc_x,
            sensor_data.acc_y,
            sensor_data.acc_z,
            sensor_data.gyro_x,
            sensor_data.gyro_y,
            sensor_data.gyro_z,
            dt=0.1  # 100ms between updates (matches ESP32 sending rate)
        )

        # Store angles for axis mapping
        filtered_angles = {
            'x': angle_x,  # Roll
            'y': angle_y,  # Pitch
            'z': angle_z   # Yaw
        }

        # Apply axis mapping to Unity coordinate system
        for unity_axis, (sensor_axis, invert) in AXIS_MAPPING.items():
            value = filtered_angles.get(sensor_axis, 0)
            if invert:
                value = -value
            current_rotation[unity_axis.split('_')[1]] = value

        # Print filtered rotation
        print(f"FILTERED: X={current_rotation['x']:.1f}° "
              f"Y={current_rotation['y']:.1f}° Z={current_rotation['z']:.1f}°")

        # Send to Flask API
        send_rotation_to_api()

    except Exception as e:
        print(f"Error processing notification: {e}")


async def find_device():
    """Scan for and find the ESP32 device"""
    print(f"Scanning for '{DEVICE_NAME}'...")

    devices = await BleakScanner.discover(timeout=10.0)

    for device in devices:
        if device.name == DEVICE_NAME:
            print(f"✓ Found {DEVICE_NAME} at {device.address}")
            return device.address

    print(f"✗ Could not find {DEVICE_NAME}")
    return None


async def connect_and_listen():
    """Main function to connect to ESP32 and listen for data"""

    # Find the device
    address = await find_device()
    if address is None:
        return

    # Connect to the device
    print(f"Connecting to {address}...")

    async with BleakClient(address) as client:
        print(f"✓ Connected to {DEVICE_NAME}")

        # Enable notifications
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("✓ Listening for sensor data with Complementary Filter...")
        print("=" * 80)

        # Keep the connection alive
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)
            print("✓ Disconnected")


def main():
    """Entry point"""
    print("=" * 80)
    print("ESP32 BLE to LEGO Brick Rotator (Complementary Filter)")
    print("=" * 80)
    print(f"Looking for device: {DEVICE_NAME}")
    print(f"API endpoint: {API_URL}")
    print(f"Filter alpha: {comp_filter.alpha} (98% gyro, 2% accel)")
    print("=" * 80)
    print()

    try:
        asyncio.run(connect_and_listen())
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()