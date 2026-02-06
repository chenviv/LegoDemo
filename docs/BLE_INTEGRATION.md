# ESP32 BLE Integration Guide

This guide explains how to connect your ESP32 with MPU6050 sensor to control the LEGO brick rotation.

## Overview

The ESP32 sends sensor data via BLE → Python BLE client receives it → Sends via WebSocket to Flask server → Flask broadcasts to Unity WebGL → Unity updates LEGO brick rotation

## Setup

### 1. Install Python Dependencies

```bash
# Flask server
cd server
pip install -r requirements.txt

# BLE client
cd ../ble_client
pip install -r requirements.txt
```

This installs:
- **Server**: Flask, flask-cors, flask-socketio, python-socketio
- **BLE Client**: bleak, python-socketio, websocket-client

### 2. ESP32 Setup

Your ESP32 is already configured! It:
- Reads MPU6050 accelerometer and gyroscope data
- Broadcasts as "ESP32_MPU6050_BLE"
- Sends 28-byte binary packets every 100ms containing:
  - Timestamp (milliseconds since boot)
  - Acceleration (X, Y, Z) in g
  - Gyroscope (X, Y, Z) in °/s

### 3. Running the System

**Important:** Start the Flask server first, then the BLE client.

**Terminal 1 - Start Flask Server:**
```bash
cd server
python app.py
# Wait for "Running on http://0.0.0.0:5000" message
```

**Terminal 2 - Start BLE Client:**
```bash
cd ble_client
python ble_client.py
# Will connect to Flask WebSocket, then scan for ESP32
```

**Terminal 3 - Open Web Interface:**
```bash
# Open http://localhost:5000 in browser
# WebSocket connection will be established automatically
```

## How It Works

### Data Processing Flow

The system processes sensor data through multiple stages:

1. **ESP32** reads MPU6050 sensor → sends raw data (acc + gyro) via BLE (28 bytes)
2. **Python BLE Client** receives data → applies complementary filter for sensor fusion
3. **Angle Calculation** → combines accelerometer (absolute) + gyroscope (rate) for stable angles
4. **Drift Compensation** → detects stationary state and resets gyro drift
5. **Axis Mapping** → converts ESP32 coordinate system to Unity's coordinate system
6. **WebSocket Emit** → BLE client emits rotation data via Socket.IO to Flask server
7. **Flask Broadcast** → Flask broadcasts rotation updates to all connected WebSocket clients
8. **Unity WebGL** → receives real-time updates via WebSocket → updates 3D brick rotation

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

### "Failed to connect to WebSocket server" or WebSocket errors
- Make sure Flask server is running first (before BLE client)
- Check Flask server shows "Running on http://0.0.0.0:5000"
- Verify no firewall blocking port 5000
- Try restarting both Flask server and BLE client

### BLE client connects but Unity doesn't update
- Check browser console (F12) for WebSocket connection status
- Verify Unity WebGL is loaded and connected to WebSocket
- Look for rotation update events in browser console
- Restart Flask server to reset WebSocket connections

### MPU6050 sensor not detected or initialization fails
- Verify I2C wiring (SDA to GPIO 21, SCL to GPIO 22)
- Check MPU6050 power supply is stable at 3.3V
- If AD0 pin is wired to GND, ensure ESP32 code uses I2C address 0x68 (default is 0x69)
- Try running an I2C scanner sketch to confirm the sensor's address

### Rotation is too sensitive/not sensitive enough
- The Python client applies a complementary filter with configurable parameters
- Adjust `alpha` (gyro vs accel weight) or `gyro_deadband` in the `ComplementaryFilter` class
- Modify axis mapping or implement custom scaling in `ble_client.py`
- See "Advanced Usage" section for customizing the sensor fusion filter

### Data not reaching Unity WebGL
- Make sure `app.py` is running in another terminal
- Check the SERVER_URL in `ble_client.py` matches your Flask server (default: `http://localhost:5000`)
- Look for "Sent rotation" messages in the BLE client output
- Verify WebSocket connection is established in browser console

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

The ESP32 uses a hardware timer interrupt for precise timing. Default interval: **100ms** (10 Hz).

**Dynamic Timer Interval Control:**

You can change the sampling rate in real-time from the web UI (when BLE is connected):
- Range: 10ms to 1000ms
- Default: 100ms (10 Hz)
- The BLE client sends the update via WebSocket to the server, which forwards it to the BLE client
- The BLE client writes the new interval to a writable BLE characteristic
- ESP32 immediately updates its hardware timer

Faster updates = smoother rotation, but more power consumption and BLE bandwidth usage.

You can also set the default interval in the firmware:
```cpp
unsigned long measurementInterval = 100; // milliseconds
```

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
Service UUID:        c10299b1-b9ba-451a-ad8c-17baeecd9480
Characteristic UUID: 657b9056-09f8-4e0f-9d37-f76b6756e95e
```

## Example Output

When running successfully, you should see:
```
================================================================================
ESP32 BLE to LEGO Brick Rotator with WebSocket
================================================================================
Looking for device: ESP32_MPU6050_BLE
WebSocket server: http://localhost:5000
Filter alpha: 0.98 (98% gyro, 2% accel)
Max reconnection attempts: 5
Connection timeout: 10.0s
================================================================================

Connecting to WebSocket server at http://localhost:5000...
✓ Connected to WebSocket server
→ BLE Status: Disconnected to ESP32_MPU6050_BLE
Scanning for 'ESP32_MPU6050_BLE'...
Found ESP32_MPU6050_BLE at XX:XX:XX:XX:XX:XX
Connecting to XX:XX:XX:XX:XX:XX...
✓ Connected to ESP32_MPU6050_BLE
→ BLE Status: Connected to ESP32_MPU6050_BLE
Listening for sensor data...
================================================================================

RAW: [T=12345ms] Acc: X=0.01 Y=-0.02 Z=1.00 | Gyro: X=0.5 Y=-0.3 Z=0.0 | dt=100.0ms
FILTERED: X=2.9° Y=-2.9° Z=0.0°
→ Sent rotation: X=2.9° Y=0.0° Z=2.9°
```
