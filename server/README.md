# Server

Flask web server for the LegoDemo project.

## Features

- Serves Unity WebGL build from `static/webgl/`
- REST API for rotation data storage and retrieval
- CORS enabled for Unity WebGL cross-origin requests
- Health check endpoint
- Can be containerized with Docker

## Requirements

- Python 3.8+

## Dependencies

All Python dependencies are listed in `requirements.txt`:
- **Flask** (3.0.0) - Web framework for serving WebGL and REST API
- **flask-cors** (4.0.0) - Enable CORS for Unity WebGL cross-origin requests


## Installation

```bash
pip install -r requirements.txt
```

## Configuration

The Flask server runs on port 5000 by default. To change this, edit `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
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
- Rotation data comes from the BLE client (see `../ble_client/README.md`)

## Files

- `app.py` - Flask application
- `Dockerfile` - Docker containerization
- `static/index.html` - Web UI
- `static/webgl/` - Unity WebGL build artifacts
- `requirements.txt` - Python dependencies (Flask + flask-cors)

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

- `GET /` - Serves the main HTML page
- `GET /api/rotation` - Get current rotation angles
- `POST /api/rotation` - Update rotation angles
- `GET /health` - Health check endpoint
- `GET /webgl/<path>` - Serve WebGL build files

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



