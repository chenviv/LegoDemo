# LegoDemo

A smart LEGO building system that combines Unity 3D visualization, ESP32 motion sensing, and real-time Bluetooth communication.

## Project Structure

```
LegoDemo/
├── unity/              # Unity 3D application for LEGO brick visualization
├── server/             # Web server with integrated BLE client
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
Web server that serves the Unity WebGL build and handles Bluetooth communication.

**⚠️ Note:** The BLE client is currently integrated with the web server and requires:
- Local execution on a machine with Bluetooth hardware
- Direct access to the ESP32 device via Bluetooth

**Key Features:**
- Serves Unity WebGL application
- Integrated BLE client for ESP32 communication
- Real-time data bridging between web UI and hardware

### Firmware (ESP32)
Arduino-based firmware for ESP32 with MPU6050 motion sensor integration.

**Key Features:**
- BLE server implementation
- Motion data collection (accelerometer/gyroscope)
- Real-time sensor data transmission

## Prerequisites

- **Unity**: 2021.3 LTS or later
- **Python**: 3.8+
- **Arduino IDE**: For ESP32 firmware upload
- **Bluetooth**: Hardware with BLE support (for Server)

## Quick Start

### 1. Setup ESP32
```bash
cd firmware
# Open LEGO.ino in Arduino IDE
# Install MPU6050_light library
# Upload to ESP32 board
```

### 2. Run Server (with BLE)
```bash
cd server
pip install -r requirements.txt
python app.py
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

- The server must run on a machine with Bluetooth hardware
- BLE client and web server are coupled for simplicity
- Consider separating BLE bridge for production deployments

