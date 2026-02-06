# LegoDemo

A smart LEGO building system that combines Unity 3D visualization, ESP32 motion sensing, and real-time Bluetooth communication.

![Demo](demo.gif)

## Project Structure

```
LegoDemo/
├── unity/              # Unity 3D application for LEGO brick visualization
├── server/             # Flask web server (serves WebGL + REST API)
│   └── static/webgl/   # Unity WebGL build artifacts
├── ble_client/         # BLE client for ESP32 communication
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

### Server (Flask)
Flask web server that serves the Unity WebGL build and provides REST API and WebSocket for rotation data.

**Key Features:**
- Serves Unity WebGL application
- WebSocket (Socket.IO) for real-time bidirectional communication
- REST API for rotation state management
- Can be containerized with Docker
- CORS enabled for WebGL cross-origin requests

### BLE Client
Python BLE client that connects to ESP32 and forwards sensor data to the Flask server.

**Key Features:**
- Connects to ESP32 via Bluetooth Low Energy
- Processes sensor data with complementary filter
- Sensor fusion (accelerometer + gyroscope)
- Axis mapping and drift compensation
- WebSocket (Socket.IO) connection to Flask server for real-time updates
- Automatic reconnection with exponential backoff
- BLE connection status reporting

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
- **Bluetooth**: Hardware with BLE support (for BLE Client)

## Quick Start

### 1. Setup ESP32
```bash
cd firmware
# Open ESP32_LEGO_BLE/ESP32_LEGO_BLE.ino in Arduino IDE
# Install MPU6050_light library
# Upload to ESP32 board
# Important: Place on flat, level surface for calibration
```

### 2. Run Server and BLE Client
```bash
# Terminal 1 - Flask Server (start this first)
cd server
pip install -r requirements.txt
python app.py

# Terminal 2 - BLE Client (start after server is running)
cd ble_client
pip install -r requirements.txt
python ble_client.py

# Access web interface at http://localhost:5000
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

- Flask server (`server/`) can be containerized with Docker
- BLE client (`ble_client/`) must run on host machine with Bluetooth hardware
- Flask server can run anywhere (locally or in Docker)
- **WebSocket Implementation**: Real-time bidirectional communication via Socket.IO
  - Unity WebGL receives rotation updates via WebSocket (no polling)
  - BLE client sends rotation data and connection status via WebSocket
  - Server broadcasts updates to all connected clients
  - Fallback REST API still available for compatibility
- **Data Flow**: ESP32 → BLE → BLE Client → WebSocket → Flask Server → WebSocket → Unity WebGL

