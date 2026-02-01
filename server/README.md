# Server

Flask web server and BLE client for the LegoDemo project.

## Features

- **Flask Server (`app.py`)**: Serves Unity WebGL build and provides REST API for rotation data
- **BLE Client (`ble_client.py`)**: Connects to ESP32 via Bluetooth and forwards sensor data to Flask API
- Real-time data bridging between ESP32 hardware and web interface

**Note:** The Flask server and BLE client run as separate processes.

## Requirements

- Python 3.8+
- Bluetooth hardware (BLE capable) for the BLE client
- ESP32 device running the LegoDemo firmware

## Dependencies

All Python dependencies are listed in `requirements.txt`:
- **Flask** (3.0.0) - Web framework for serving WebGL and REST API
- **flask-cors** (4.0.0) - Enable CORS for Unity WebGL cross-origin requests
- **bleak** (0.21.1) - Bluetooth Low Energy library for ESP32 communication
- **requests** (2.31.0) - HTTP library for BLE client to post data to Flask API


## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `ble_client.py` to configure your ESP32 device settings:
- BLE device name (default: `"ESP32_MPU6050_BLE"`)
- Service and characteristic UUIDs (if you modified the firmware)
- Complementary filter parameters (`alpha`, `gyro_deadband`)
- Axis mapping for Unity coordinate system

## Usage

The system requires running **two separate processes**:

**Terminal 1 - Start Flask Server:**
```bash
python app.py
```
Server will start on `http://localhost:5000`

**Terminal 2 - Start BLE Client:**
```bash
python ble_client.py
```
BLE client will scan for, connect to, and stream data from the ESP32 device.

**Terminal 3 - Access Web Interface:**
- Open `http://localhost:5000` in your browser
- The Unity WebGL visualization will load and display real-time rotation from the ESP32

## Files

- `app.py` - Flask application
- `ble_client.py` - Bluetooth Low Energy client
- `static/index.html` - Web UI
- `static/webgl/` - Unity WebGL build artifacts
- `requirements.txt` - Python dependencies

## Unity WebGL Build Setup

The server expects Unity WebGL build files to be placed in `static/webgl/`:

```
server/
  static/
    webgl/
      Build/
        webgl.data.gz
        webgl.framework.js.gz
        webgl.loader.js
        webgl.wasm.gz
      TemplateData/
      index.html
    index.html
```

**To create the build:**
1. Open the Unity project from the `unity/` directory
2. Go to **File → Build Settings**
3. Select **WebGL** platform
4. Click **Build** (not Build And Run)
5. Choose output directory: `../server/static/webgl`

## Notes

**Architecture:** The Flask server (`app.py`) and BLE client (`ble_client.py`) run as separate processes:
- **Flask Server**: Serves web UI, provides REST API, stores current rotation state in memory
- **BLE Client**: Connects to ESP32 via Bluetooth, processes sensor data (complementary filter, axis mapping), posts to Flask API

This separation allows the Flask server to run anywhere while the BLE client must run on a machine with Bluetooth hardware.

For production deployment, consider:
- Separating the BLE client into a standalone bridge service
- Using WebSocket instead of polling for real-time updates
- Adding a database for persistent state storage



