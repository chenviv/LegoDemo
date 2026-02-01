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
- Sends 28-byte binary packets every second containing:
  - Temperature
  - Acceleration (X, Y, Z)
  - Gyroscope (X, Y, Z)

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

### Two Rotation Modes

The script supports two ways to calculate rotation:

#### Mode 1: Accelerometer (Default - ENABLED)
- Uses tilt angles from accelerometer
- Provides **absolute orientation** relative to gravity
- Best for: Showing the physical tilt of the ESP32
- Calculates pitch (X) and roll (Y) directly

#### Mode 2: Gyroscope (Commented out)
- Integrates angular velocity over time
- Provides **relative rotation** from starting position
- Best for: Tracking rotation changes
- Can drift over time

To switch modes, edit `ble_client.py` and comment/uncomment the appropriate section in `notification_handler()`.

### Adjusting Sensitivity

In `ble_client.py`, change this line:
```python
SENSITIVITY = 0.5  # Increase for more rotation, decrease for less
```

## Troubleshooting

### "Could not find ESP32_MPU6050_BLE"
- Make sure ESP32 is powered on
- Check Serial Monitor shows "Waiting for client..."
- ESP32 should be within Bluetooth range (~10m)
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
- Check USB power is stable for ESP32
- Reduce interference from other Bluetooth devices

### Rotation is too sensitive/not sensitive enough
- Adjust `SENSITIVITY` in `ble_client.py`
- Try switching between accelerometer and gyroscope modes

### Flask API not receiving data
- Make sure `app.py` is running in another terminal
- Check the API_URL in `ble_client.py` matches your Flask server
- Look for "✓ Sent rotation" messages in the BLE client output

## Data Format

The ESP32 sends this struct (28 bytes):
```cpp
struct SensorData {
  float temp;   // 0-3:   Temperature (°C)
  float accX;   // 4-7:   Accel X (g)
  float accY;   // 8-11:  Accel Y (g)
  float accZ;   // 12-15: Accel Z (g)
  float gyroX;  // 16-19: Gyro X (°/s)
  float gyroY;  // 20-23: Gyro Y (°/s)
  float gyroZ;  // 24-27: Gyro Z (°/s)
}
```

Python unpacks it as:
```python
struct.unpack('<7f', data)  # 7 floats (temp, accX, accY, accZ, gyroX, gyroY, gyroZ), little-endian
```

## Advanced Usage

### Using Gyroscope Instead of Accelerometer

Edit `ble_client.py` in the `notification_handler()` function:

```python
# Comment out accelerometer:
# update_rotation_from_accelerometer(...)

# Uncomment gyroscope:
update_rotation_from_gyro(
    sensor_data.gyro_x,
    sensor_data.gyro_y,
    sensor_data.gyro_z,
    dt=1.0
)
```

### Combining Both Sensors

For best results, you could use a complementary filter:
- Accelerometer for long-term stability
- Gyroscope for short-term accuracy

This would require implementing sensor fusion (like a Kalman filter).

### Changing Update Rate

In the ESP32 code, change this line:
```cpp
if (deviceConnected && (millis() - timer > 1000)) {  // Change 1000 to desired ms
```

Faster updates = smoother rotation, but more CPU usage.

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
Sensitivity: 0.5
================================================================================

Scanning for 'ESP32_MPU6050_BLE'...
✓ Found ESP32_MPU6050_BLE at XX:XX:XX:XX:XX:XX
Connecting to XX:XX:XX:XX:XX:XX...
✓ Connected to ESP32_MPU6050_BLE
✓ Listening for sensor data...
================================================================================
Temp: 28.5°C | Acc: X=0.05 Y=-0.02 Z=0.98 | Gyro: X=0.3 Y=-0.1 Z=0.0
✓ Sent rotation: X=2.9° Y=-2.9° Z=0.0°
```
