# Server

Flask web server for the LegoDemo project.

## Features

- Serves Unity WebGL build from `static/webgl/`
- WebSocket (Socket.IO) server for real-time bidirectional communication
- REST API for rotation data storage and retrieval (compatibility)
- BLE connection status tracking and broadcasting
- CORS enabled for Unity WebGL cross-origin requests
- Health check endpoint
- Can be containerized with Docker

## Requirements

- Python 3.8+

## Dependencies

All Python dependencies are listed in `requirements.txt`:
- **Flask** (3.0.0) - Web framework for serving WebGL and REST API
- **flask-cors** (4.0.0) - Enable CORS for Unity WebGL cross-origin requests
- **flask-socketio** (5.3.6) - WebSocket support for real-time communication
- **python-socketio** (5.11.1) - Socket.IO implementation for Python


## Installation

```bash
pip install -r requirements.txt
```

## Configuration

The Flask server with Socket.IO runs on port 5000 by default. To change this, edit `app.py`:
```python
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

## Usage

**Start Flask Server:**
```bash
python app.py
```
Server will start on `http://localhost:5000`

**Or use Docker:**
```bash
docker build -t lego-server .
docker run -p 5000:5000 lego-server
```

**Access Web Interface:**
- Open `http://localhost:5000` in your browser
- The Unity WebGL visualization will load
- WebSocket connection will be established automatically
- Rotation data comes from the BLE client via WebSocket (see `../ble_client/README.md`)
- BLE connection status is displayed in real-time

## Files

- `app.py` - Flask application with Socket.IO server
- `Dockerfile` - Docker containerization
- `static/index.html` - Web UI
- `static/webgl/` - Unity WebGL build artifacts
- `requirements.txt` - Python dependencies (Flask, flask-cors, flask-socketio, python-socketio)

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

## API Endpoints

### REST API (HTTP)
- `GET /` - Serves the main HTML page
- `GET /api/rotation` - Get current rotation angles
- `POST /api/rotation` - Update rotation angles
- `GET /health` - Health check endpoint
- `GET /webgl/<path>` - Serve WebGL build files

### WebSocket Events (Socket.IO)
- **Client → Server:**
  - `rotation_update` - Send rotation data (from BLE client)
  - `ble_status` - Send BLE connection status (from BLE client)
  - `update_timer_interval` - Request ESP32 timer interval change (10-1000ms)

- **Server → Client:**
  - `rotation_update` - Broadcast rotation data to all clients
  - `ble_status` - Broadcast BLE connection status to all clients
  - `update_timer_interval` - Forward timer interval request to BLE client
  - `error` - Error message
  - `connect`/`disconnect` - Connection lifecycle events

## Docker

The server can be containerized:
```bash
docker build -t lego-server .
docker run -p 5000:5000 lego-server
```

## Notes

- Rotation state is stored in memory (resets on restart)
- The BLE client runs separately in `../ble_client/`
- For production, consider:
  - Using a database for persistent state
  - WebSocket for real-time updates
  - Load balancing for scalability



