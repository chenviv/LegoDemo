# Server

Flask web server with integrated BLE client for the LegoDemo project.

## Features

- Serves Unity WebGL build from `static/webgl/`
- Integrated BLE client for ESP32 communication
- Real-time data bridging

## Requirements

- Python 3.8+
- Bluetooth hardware (BLE capable)
- ESP32 device running the LegoDemo firmware


## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `ble_client.py` to configure your ESP32 device settings:
- BLE device name/address
- Service and characteristic UUIDs

## Usage

```bash
python app.py
```

The server will start on `http://localhost:5000` (or configured port).

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
        WebGLBuild.data.gz
        WebGLBuild.framework.js.gz
        WebGLBuild.loader.js
        WebGLBuild.wasm.gz
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

This server requires local execution on a machine with Bluetooth hardware. For production deployment, consider separating the BLE client into a standalone bridge service.



