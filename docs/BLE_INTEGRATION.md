# ESP32 BLE Integration Guide

This guide explains how to connect your ESP32 with MPU6050 sensor to control the LEGO brick rotation.

## Overview

The ESP32 sends sensor data via BLE → Python script receives it → Updates Flask API → Unity updates LEGO brick rotation

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `bleak` - Bluetooth Low Energy library for Python
- `requests` - For sending data to Flask API

### 2. ESP32 Setup

Your ESP32 is already configured! It:
- Reads MPU6050 accelerometer and gyroscope data
- Broadcasts as "ESP32_MPU6050_BLE"
- Sends 28-byte binary packets every 100ms containing:
  - Timestamp (milliseconds since boot)
  - Acceleration (X, Y, Z) in g
  - Gyroscope (X, Y, Z) in °/s

### 3. Running the System

**Terminal 1 - Start Flask Server:**
```bash
python app.py
```

**Terminal 2 - Start BLE Client:**
```bash
python ble_client.py
```

**Terminal 3 - Open Web Interface (optional):**
```bash
# Or just open http://localhost:5000 in browser
```

## How It Works

### Data Processing Flow

The system processes sensor data through multiple stages:

1. **ESP32** reads MPU6050 sensor → sends raw data (acc + gyro) via BLE (28 bytes)
2. **Python BLE Client** receives data → applies complementary filter for sensor fusion
3. **Angle Calculation** → combines accelerometer (absolute) + gyroscope (rate) for stable angles
4. **Drift Compensation** → detects stationary state and resets gyro drift
5. **Axis Mapping** → converts ESP32 coordinate system to Unity's coordinate system
6. **Flask API** → receives mapped rotation → stores current state
7. **Unity WebGL** → polls API → updates 3D brick rotation

### Axis Mapping

The BLE client converts ESP32 coordinate system to Unity's coordinate system:
```python
AXIS_MAPPING = {
    'unity_x': ('x', False),  # Pitch (front/back tilt)
    'unity_y': ('z', False),  # Yaw (rotation)
    'unity_z': ('y', True),   # Roll (left/right tilt, inverted)
}
```

## Troubleshooting

### "Could not find ESP32_MPU6050_BLE"
- Make sure ESP32 is powered on
- Check Serial Monitor shows "Waiting for client (28-byte binary packets with timestamp)..."
- ESP32 should be within Bluetooth range (~10m)
- Verify device completed calibration (should show offset values)
- Try running the scan again

### "Permission denied" or Bluetooth errors
- **Linux**: You may need to run with sudo or configure bluetooth permissions
  ```bash
  sudo python ble_client.py
  ```
- **Windows**: Make sure Bluetooth is enabled in settings
- **Mac**: Grant Bluetooth permissions when prompted

### Connection keeps dropping
- Move ESP32 closer to computer
- Check power is stable for ESP32
- Reduce interference from other Bluetooth devices

### Rotation is too sensitive/not sensitive enough
- The Python client applies a complementary filter with configurable parameters
- Adjust `alpha` (gyro vs accel weight) or `gyro_deadband` in the `ComplementaryFilter` class
- Modify axis mapping or implement custom scaling in `ble_client.py`
- See "Advanced Usage" section for customizing the sensor fusion filter

### Flask API not receiving data
- Make sure `app.py` is running in another terminal
- Check the API_URL in `ble_client.py` matches your Flask server
- Look for "Sent rotation" messages in the BLE client output

## Data Format

### ESP32 Firmware Output (28 bytes)

The ESP32 sends this struct:
```cpp
struct SensorData {
  uint32_t timestamp; // 0-3:   Timestamp (ms)
  float accX;         // 4-7:   Accel X (g)
  float accY;         // 8-11:  Accel Y (g)
  float accZ;         // 12-15: Accel Z (g)
  float gyroX;        // 16-19: Gyro X (°/s)
  float gyroY;        // 20-23: Gyro Y (°/s)
  float gyroZ;        // 24-27: Gyro Z (°/s)
} __attribute__((packed));
```

### Python BLE Client Parsing

The Python client correctly unpacks this data:
```python
struct.unpack('<I6f', data)  # 1 uint32 + 6 floats, little-endian (28 bytes)
# Returns: (timestamp, accX, accY, accZ, gyroX, gyroY, gyroZ)
```

The client then applies a **complementary filter** to fuse accelerometer and gyroscope data into stable rotation angles, with drift compensation for when the device is stationary.

## Advanced Usage

### Understanding the Complementary Filter

The BLE client implements sensor fusion using a complementary filter that combines:
- **Accelerometer**: Provides absolute orientation (stable long-term, noisy short-term)
- **Gyroscope**: Provides rotation rate (accurate short-term, drifts long-term)

The filter formula:
```python
alpha = 0.98  # Weight factor (98% gyro, 2% accelerometer)
angle = alpha * (previous_angle + gyro_rate * dt) + (1 - alpha) * accel_angle
```

### Drift Compensation

When the device is stationary (low gyro values for extended time), the filter automatically:
1. Detects stationary state (gyro magnitude < threshold for multiple readings)
2. Gradually resets angles toward accelerometer values
3. Prevents long-term drift accumulation

### Customizing Filter Parameters

In `ble_client.py`, adjust these parameters:
```python
class ComplementaryFilter:
    def __init__(self, alpha=0.98, gyro_deadband=2.0):
        self.alpha = alpha              # Higher = trust gyro more (0.95-0.99)
        self.gyro_deadband = gyro_deadband  # Degrees/sec below which gyro is ignored
        # Other internal state: angle_x, angle_y, angle_z, stationary_counter
```

The ESP32 uses a hardware timer interrupt for precise timing. Current interval: **100ms** (10 Hz).

To change it, modify this line in the firmware:
```cpp
unsigned long measurementInterval = 100; // milliseconds
```

Faster updates = smoother rotation, but more power consumption and BLE bandwidth usage.

## Testing Without ESP32

To test the system without an ESP32, you can manually send rotation data:

```bash
curl -X POST http://localhost:5000/api/rotation \
  -H "Content-Type: application/json" \
  -d '{"x": 45, "y": 30, "z": 15}'
```

Or use the web interface input fields.

## BLE UUIDs Reference

```
Service UUID:        4fafc201-1fb5-459e-8fcc-c5c9c331914b
Characteristic UUID: beb5483e-36e1-4688-b7f5-ea07361b26a8
```

## Example Output

When running successfully, you should see:
```
================================================================================
ESP32 BLE to LEGO Brick Rotator
================================================================================
Looking for device: ESP32_MPU6050_BLE
API endpoint: http://localhost:5000/api/rotation
Filter alpha: 0.98 (98% gyro, 2% accel)
Max reconnection attempts: 5
Connection timeout: 10.0s
================================================================================

Scanning for 'ESP32_MPU6050_BLE'...
Found ESP32_MPU6050_BLE at XX:XX:XX:XX:XX:XX
Connecting to XX:XX:XX:XX:XX:XX...
✓ Connected to ESP32_MPU6050_BLE

RAW: [T=12345ms] Acc: X=0.01 Y=-0.02 Z=1.00 | Gyro: X=0.5 Y=-0.3 Z=0.0 | dt=100.0ms
ESP32: Angles: X=2.9° Y=-2.9° Z=0.0°
Unity: X=2.9° Y=0.0° Z=2.9°
✓ Sent rotation: X=2.9° Y=0.0° Z=2.9°
```
