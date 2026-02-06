import asyncio
import struct
import socketio
import math
import time
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

# BLE UUIDs from ESP32
SERVICE_UUID = "c10299b1-b9ba-451a-ad8c-17baeecd9480"
CHARACTERISTIC_UUID = "657b9056-09f8-4e0f-9d37-f76b6756e95e"

# Flask server WebSocket endpoint
SERVER_URL = "http://localhost:5000"

# Device name
DEVICE_NAME = "ESP32_MPU6050_BLE"

# Reconnection settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY_BASE = 2  # Base delay in seconds (will use exponential backoff)
CONNECTION_TIMEOUT = 10.0  # Connection timeout in seconds

# Rotation state
current_rotation = {"x": 0.0, "y": 0.0, "z": 0.0}

# BLE connection state
ble_connected = False
ble_device_name = None

# WebSocket client with reconnection enabled
sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=1, reconnection_delay_max=5)

# WebSocket event handlers
@sio.on('connect')
def on_connect():
    """Handle connection to WebSocket server"""
    print("✓ Connected to WebSocket server")
    # Re-send current BLE status when WebSocket reconnects
    if ble_connected:
        send_ble_status(True, ble_device_name)
    else:
        send_ble_status(False)

@sio.on('disconnect')
def on_disconnect():
    """Handle disconnection from WebSocket server"""
    print("✗ Disconnected from WebSocket server")

@sio.on('rotation_update')
def on_rotation_update(data):
    """Handle rotation updates from server (for bidirectional communication)"""
    print(f"← Received rotation update from server: {data}")

@sio.on('error')
def on_error(data):
    """Handle error messages from server"""
    print(f"✗ Server error: {data.get('message', 'Unknown error')}")

@sio.on('update_timer_interval')
def on_timer_interval_update(data):
    """Handle timer interval update request from server"""
    interval = data.get('interval', 100)
    print(f"← Received timer interval update request: {interval}ms")
    # Store for writing to BLE
    if hasattr(on_timer_interval_update, 'pending_interval'):
        on_timer_interval_update.pending_interval = interval
    else:
        on_timer_interval_update.pending_interval = interval

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

# Last timestamp for dt calculation
last_timestamp = None

class SensorData:
    """Class to parse the binary sensor data from ESP32"""
    def __init__(self, data):
        # Unpack 1 uint + 6 floats (4 bytes each = 28 bytes total) directly into named variables
        (self.timestamp,
         self.acc_x, self.acc_y, self.acc_z,
         self.gyro_x, self.gyro_y, self.gyro_z) = struct.unpack('<I6f', data)

    def __str__(self):
        return (f"[T={self.timestamp}ms] "
                f"Acc: X={self.acc_x:.2f} Y={self.acc_y:.2f} Z={self.acc_z:.2f} | "
                f"Gyro: X={self.gyro_x:.1f} Y={self.gyro_y:.1f} Z={self.gyro_z:.1f}")


def send_rotation_to_api():
    """Send current rotation to Flask server via WebSocket"""
    try:
        if sio.connected:
            sio.emit('rotation_update', current_rotation)
            print(f"→ Sent rotation: X={current_rotation['x']:.1f}° "
                  f"Y={current_rotation['y']:.1f}° Z={current_rotation['z']:.1f}°")
        else:
            print("✗ WebSocket not connected, skipping rotation update")
    except Exception as e:
        print(f"✗ Failed to send rotation: {e}")


def send_ble_status(connected, device_name=None):
    """Send BLE connection status to server via WebSocket"""
    global ble_connected, ble_device_name
    
    # Update tracked state
    ble_connected = connected
    ble_device_name = device_name if device_name else DEVICE_NAME
    
    try:
        if sio.connected:
            status = {
                'connected': connected,
                'device_name': ble_device_name
            }
            sio.emit('ble_status', status)
            print(f"→ BLE Status: {'Connected' if connected else 'Disconnected'} to {ble_device_name}")
        else:
            print("✗ WebSocket not connected, cannot send BLE status")
    except Exception as e:
        print(f"✗ Failed to send BLE status: {e}")


async def notification_handler(sender, data):
    """Handle BLE notifications from ESP32"""
    global last_timestamp

    try:
        # Parse the binary data
        sensor_data = SensorData(data)

        # Calculate dt from timestamp
        if last_timestamp is None:
            dt = 0.1  # Default for first reading
        else:
            dt = (sensor_data.timestamp - last_timestamp) / 1000.0  # Convert ms to seconds
        last_timestamp = sensor_data.timestamp

        # Print raw sensor data and dt
        print(f"RAW: {sensor_data} | dt={dt*1000:.1f}ms")

        # Apply complementary filter (returns filtered angles directly)
        angle_x, angle_y, angle_z = comp_filter.update(
            sensor_data.acc_x,
            sensor_data.acc_y,
            sensor_data.acc_z,
            sensor_data.gyro_x,
            sensor_data.gyro_y,
            sensor_data.gyro_z,
            dt=dt
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
            print(f"Found {DEVICE_NAME} at {device.address}")
            return device.address

    print(f"✗ Could not find {DEVICE_NAME}")
    return None


async def connect_and_listen():
    """Main function to connect to ESP32 and listen for data with reconnection support"""
    reconnect_count = 0

    # Connect to WebSocket server first
    try:
        print(f"Connecting to WebSocket server at {SERVER_URL}...")
        sio.connect(SERVER_URL)
        # Send initial BLE status (disconnected) upon WebSocket connection
        send_ble_status(False)
    except Exception as e:
        print(f"✗ Failed to connect to WebSocket server: {e}")
        print("Continuing anyway, will attempt to connect later...")

    while reconnect_count < MAX_RECONNECT_ATTEMPTS:
        try:
            # Find the device
            address = await find_device()
            if address is None:
                reconnect_count += 1
                if reconnect_count < MAX_RECONNECT_ATTEMPTS:
                    delay = RECONNECT_DELAY_BASE * (2 ** reconnect_count)
                    print(f"Retrying in {delay} seconds... (Attempt {reconnect_count + 1}/{MAX_RECONNECT_ATTEMPTS})")
                    await asyncio.sleep(delay)
                continue

            # Reset reconnect counter on successful device discovery
            reconnect_count = 0

            # Connect to the device with timeout
            print(f"Connecting to {address}...")

            async with BleakClient(address, timeout=CONNECTION_TIMEOUT) as client:
                print(f"Connected to {DEVICE_NAME}")

                # Send BLE connected status
                send_ble_status(True, DEVICE_NAME)

                # Find writable characteristic for timer interval
                TIMER_INTERVAL_WRITE_UUID = "a7b3e6c8-4d2f-11ed-b878-0242ac120002"

                # Enable notifications
                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                print("Listening for sensor data...")
                print("=" * 80)

                # Track last status update time
                last_status_update = time.time()
                STATUS_UPDATE_INTERVAL = 2.0  # Send status every 2 seconds

                # Keep the connection alive
                try:
                    while True:
                        # Check if still connected
                        if not client.is_connected:
                            print("\n⚠ Connection lost! Attempting to reconnect...")
                            send_ble_status(False)
                            break

                        # Check WebSocket connection and reconnect if needed
                        if not sio.connected:
                            print("\n⚠ WebSocket disconnected! Attempting to reconnect...")
                            try:
                                sio.connect(SERVER_URL)
                                # Re-send BLE status after reconnection
                                if ble_connected:
                                    send_ble_status(True, ble_device_name)
                            except Exception as ws_error:
                                print(f"✗ WebSocket reconnection failed: {ws_error}")

                        # Periodically send BLE status (every 2 seconds)
                        current_time = time.time()
                        if current_time - last_status_update >= STATUS_UPDATE_INTERVAL:
                            send_ble_status(True, DEVICE_NAME)
                            last_status_update = current_time

                        # Check for pending timer interval update
                        if hasattr(on_timer_interval_update, 'pending_interval'):
                            interval = on_timer_interval_update.pending_interval
                            delattr(on_timer_interval_update, 'pending_interval')
                            try:
                                # Write interval as 4-byte unsigned integer (little-endian)
                                interval_bytes = struct.pack('<I', interval)
                                await client.write_gatt_char(TIMER_INTERVAL_WRITE_UUID, interval_bytes)
                                print(f"✓ Updated timer interval to {interval}ms")
                            except Exception as e:
                                print(f"✗ Failed to write timer interval: {e}")

                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nStopping...")
                    await client.stop_notify(CHARACTERISTIC_UUID)
                    print("Disconnected")
                    # Send BLE disconnected status
                    send_ble_status(False)
                    # Disconnect from WebSocket
                    if sio.connected:
                        sio.disconnect()
                    return  # Exit completely on user interrupt
                finally:
                    if client.is_connected:
                        await client.stop_notify(CHARACTERISTIC_UUID)
                    # Send BLE disconnected status
                    send_ble_status(False)

        except asyncio.TimeoutError:
            reconnect_count += 1
            print(f"\n✗ Connection timeout!")
            send_ble_status(False)
            if reconnect_count < MAX_RECONNECT_ATTEMPTS:
                delay = RECONNECT_DELAY_BASE * (2 ** reconnect_count)
                print(f"Retrying in {delay} seconds... (Attempt {reconnect_count + 1}/{MAX_RECONNECT_ATTEMPTS})")
                await asyncio.sleep(delay)

        except BleakError as e:
            reconnect_count += 1
            print(f"\n✗ BLE Error: {e}")
            send_ble_status(False)
            if reconnect_count < MAX_RECONNECT_ATTEMPTS:
                delay = RECONNECT_DELAY_BASE * (2 ** reconnect_count)
                print(f"Retrying in {delay} seconds... (Attempt {reconnect_count + 1}/{MAX_RECONNECT_ATTEMPTS})")
                await asyncio.sleep(delay)

        except Exception as e:
            reconnect_count += 1
            print(f"\n✗ Unexpected error: {e}")
            if reconnect_count < MAX_RECONNECT_ATTEMPTS:
                delay = RECONNECT_DELAY_BASE * (2 ** reconnect_count)
                print(f"Retrying in {delay} seconds... (Attempt {reconnect_count + 1}/{MAX_RECONNECT_ATTEMPTS})")
                await asyncio.sleep(delay)

    print(f"\n✗ Failed to connect after {MAX_RECONNECT_ATTEMPTS} attempts. Exiting.")

    # Disconnect from WebSocket on exit
    if sio.connected:
        sio.disconnect()


def main():
    """Entry point"""
    print("=" * 80)
    print("ESP32 BLE to LEGO Brick Rotator with WebSocket")
    print("=" * 80)
    print(f"Looking for device: {DEVICE_NAME}")
    print(f"WebSocket server: {SERVER_URL}")
    print(f"Filter alpha: {comp_filter.alpha} (98% gyro, 2% accel)")
    print(f"Max reconnection attempts: {MAX_RECONNECT_ATTEMPTS}")
    print(f"Connection timeout: {CONNECTION_TIMEOUT}s")
    print("=" * 80)
    print()

    try:
        asyncio.run(connect_and_listen())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        if sio.connected:
            sio.disconnect()
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
