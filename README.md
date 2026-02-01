# LegoDemo

A smart LEGO building system that combines Unity 3D visualization, ESP32 motion sensing, and real-time Bluetooth communication.

## Project Structure

```
LegoDemo/
├── unity/              # Unity 3D application for LEGO brick visualization
├── server/             # Web server and BLE client (separate processes)
│   └── static/webgl/   # Unity WebGL build artifacts
├── firmware/           # ESP32 firmware with MPU6050 motion sensor
└── docs/               # Documentation
```

## Components

### Unity
Interactive 3D LEGO brick builder with WebGL export support.

**Key Features:**
- Real-time brick placement and manipulation
- WebGL build for browser-based interaction
- Motion data visualization

### Server (Flask + BLE Client)
Flask web server and BLE client that serve the Unity WebGL build and handle Bluetooth communication.

**⚠️ Note:** The Flask server and BLE client run as **two separate processes**:
- **Flask Server**: Must run to serve web UI and provide REST API
- **BLE Client**: Must run on a machine with Bluetooth hardware to connect to ESP32

**Key Features:**
- Serves Unity WebGL application via Flask
- BLE client connects to ESP32 and processes sensor data
- Complementary filter for sensor fusion (accelerometer + gyroscope)
- Axis mapping and drift compensation
- Real-time data forwarding between ESP32 hardware and web interface

### Firmware (ESP32)
Arduino-based firmware for ESP32 with MPU6050 motion sensor integration.

**Key Features:**
- BLE server broadcasting as \"ESP32_MPU6050_BLE\"
- Motion data collection (accelerometer/gyroscope)
- Hardware timer interrupt for 100ms sampling (10 Hz)
- 28-byte binary packets (timestamp + 6 sensor floats)
- Automatic calibration on startup (requires flat surface)
- Compatible with Python BLE client for sensor fusion and rotation tracking

## Prerequisites

- **Unity**: 2022.3 LTS or later (project created with 2022.3.62f3)
- **Python**: 3.8+
- **Arduino IDE**: For ESP32 firmware upload
- **Bluetooth**: Hardware with BLE support (for Server)

## Quick Start

### 1. Setup ESP32
```bash
cd firmware
# Open ESP32_LEGO_BLE/ESP32_LEGO_BLE.ino in Arduino IDE
# Install MPU6050_light library
# Upload to ESP32 board
# Important: Place on flat, level surface for calibration
```

### 2. Run Server (with BLE)
```bash
cd server
pip install -r requirements.txt

# Terminal 1 - Flask Server
python app.py

# Terminal 2 - BLE Client (separate process)
python ble_client.py
```

### 3. Build Unity WebGL (Optional)
```bash
cd unity
# Open in Unity Editor
# Build WebGL target: File > Build Settings > WebGL > Build
# Output to: ../server/static/webgl
```

**Note:** The WebGL build must be placed in `server/static/webgl/` for the Flask server to serve it correctly.

## Documentation

- [BLE Integration Guide](docs/BLE_INTEGRATION.md)
- [Architecture Overview](docs/architecture.md)

## Development Notes

- The Flask server and BLE client run as separate processes for flexibility
- BLE client must run on a machine with Bluetooth hardware
- Flask server can run anywhere (locally or in cloud if BLE bridge is separate)
- Consider separating BLE bridge for production deployments
- Unity WebGL polls Flask API for rotation updates (consider WebSocket for lower latency)

