# Architecture Overview

## System Architecture

The LegoDemo project consists of three main components that work together to create an interactive LEGO building experience with motion sensing capabilities.

```
┌─────────────────┐          ┌─────────────────────────────┐          ┌─────────────────┐
│                 │          │  Python Server (2 processes)│          │                 │
│  Unity WebGL    │ WebSocket│  ┌────────────────────────┐ │   BLE    │   ESP32 + IMU   │
│  (Frontend)     │◄────────►│  │ Flask Server (app.py)  │ │          │   (Firmware)    │
│                 │          │  │  + Socket.IO           │ │          │                 │
│                 │          │  └────────────────────────┘ │◄────────►│                 │
│                 │          │  ┌────────────────────────┐ │          │                 │
│                 │          │  │ BLE Client (ble_       │ │          │                 │
│                 │          │  │   client.py)           │ │          │                 │
│                 │          │  └────────────────────────┘ │          │                 │
└─────────────────┘          └─────────────────────────────┘          └─────────────────┘
     Browser                   Server + BLE Client (separate)         Physical Device
```

**Note:** Flask server (`server/`) and BLE client (`ble_client/`) are in separate folders and can run on different machines. They communicate via WebSocket (Socket.IO) for real-time bidirectional updates.

## Component Details

### 1. Unity (Frontend)
- **Technology**: Unity 3D Engine, WebGL
- **Purpose**: 3D visualization and user interaction
- **Features**:
  - Real-time LEGO brick rendering
  - Motion-based manipulation
  - Interactive building interface
- **Output**: WebGL build deployed to `server/static/webgl/`

### 2. Server (Backend)
- **Technology**: Python Flask + Socket.IO
- **Purpose**: Web server, REST API, and WebSocket server
- **Location**: `server/` folder
- **Responsibilities**:
  - Serve Unity WebGL application and static files
  - Provide REST API for rotation data (compatibility)
  - Real-time WebSocket (Socket.IO) communication for rotation updates
  - Store current rotation state in memory
  - Track and broadcast BLE connection status
  - Can be containerized with Docker

### 3. BLE Client (Hardware Bridge)
- **Technology**: Python + Bleak (BLE library) + Socket.IO
- **Purpose**: Bluetooth communication bridge
- **Location**: `ble_client/` folder (separate from server)
- **Responsibilities**:
  - Connect to ESP32 via Bluetooth Low Energy
  - Process sensor data with complementary filter
  - Apply axis mapping and drift compensation
  - Bridge data between ESP32 hardware and Flask server
  - Real-time WebSocket connection to Flask server for bidirectional updates
  - Report BLE connection status to server
  - Automatic reconnection with exponential backoff

### 4. Firmware (Hardware)
- **Technology**: Arduino/ESP32, MPU6050 sensor
- **Purpose**: Motion sensing and data transmission
- **Features**:
  - 6-axis motion sensing (accelerometer + gyroscope)
  - BLE server broadcasting as "ESP32_MPU6050_BLE"
  - Hardware timer interrupt for precise 100ms sampling (10 Hz)
  - 28-byte binary packets (timestamp + 6 sensor values)
  - Automatic calibration on startup (requires flat surface)

## Data Flow

### Motion Data Pipeline

```
1. MPU6050 Sensor
   ↓ (I2C)
2. ESP32 Firmware
   ↓ (BLE - Bluetooth Low Energy)
3. Server BLE Client
   ↓ (HTTP)
4. Unity WebGL Application
   ↓
5. Visual Feedback (3D Rotation/Movement)
```

### Request Flow

**Current Implementation** (Real-time via WebSocket):

1. **ESP32 Sensor Reading** → MPU6050 data read every 100ms via timer interrupt
2. **BLE Transmission** → ESP32 broadcasts sensor data via BLE notifications
3. **Python BLE Client** → Receives notifications and processes data (complementary filter, axis mapping, drift compensation)
4. **WebSocket Emit** → BLE client emits rotation data to Flask server via Socket.IO (`rotation_update` event)
5. **State Storage** → Flask stores current rotation in memory
6. **WebSocket Broadcast** → Flask broadcasts rotation updates to all connected WebSocket clients
7. **Unity Real-time Update** → Unity WebGL receives rotation data via WebSocket (no polling)
8. **Visual Update** → Unity renders LEGO brick with new rotation

**Alternative REST API** (Available for compatibility):
- `GET /api/rotation` - Retrieve current rotation state
- `POST /api/rotation` - Update rotation manually

**BLE Connection Status**:
- BLE client reports connection status via WebSocket (`ble_status` event)
- Server broadcasts status to all connected clients
- Unity WebGL displays connection indicator

## Communication Protocols

### WebSocket (Socket.IO)
- **Purpose**: Real-time bidirectional communication
- **Usage**:
  - BLE client → Server: rotation updates, BLE connection status
  - Server → Unity WebGL: rotation updates, BLE status broadcasts
  - Server → BLE client: timer interval updates
- **Advantages**:
  - Low latency push-based updates
  - Efficient bidirectional messaging
  - Automatic reconnection support
  - Event-based architecture
- **Events**:
  - `rotation_update` - Send/receive rotation data
  - `ble_status` - BLE connection status updates
  - `update_timer_interval` - ESP32 sampling rate control (10-1000ms)
  - `connect`/`disconnect` - Connection lifecycle

### BLE (Bluetooth Low Energy)
- **Purpose**: Hardware-to-software communication
- **Advantages**:
  - Low power consumption
  - Suitable for continuous data streaming
  - Good range (10-100m depending on environment)
- **Data Format**: 28-byte binary packets (little-endian)
  - 1 × uint32_t timestamp (4 bytes) - milliseconds since boot
  - 6 × float sensor values (24 bytes) - accX, accY, accZ, gyroX, gyroY, gyroZ
  - Update rate: 10 Hz (every 100ms via hardware timer)
- **Service UUID**: `c10299b1-b9ba-451a-ad8c-17baeecd9480`
- **Characteristic UUID**: `657b9056-09f8-4e0f-9d37-f76b6756e95e`
- **Device Name**: `ESP32_MPU6050_BLE`

### HTTP (REST API)
- **Purpose**: Browser-to-server communication (legacy/compatibility)
- **Usage**: Fallback REST endpoints for rotation data
- **Endpoints**:
  - `GET /api/rotation` - Retrieve current rotation
  - `POST /api/rotation` - Update rotation manually
  - `GET /health` - Health check
- **Note**: Primary communication now uses WebSocket for better performance

## Technology Stack

| Component | Technologies |
|-----------|-------------|
| **Frontend** | Unity 3D, WebGL, C#, Socket.IO Client |
| **Backend** | Python 3.8+, Flask, Flask-SocketIO, Socket.IO |
| **BLE Bridge** | Python, Bleak, Socket.IO Client |
| **Firmware** | Arduino, ESP32, MPU6050_light |
| **Protocols** | WebSocket (Socket.IO), HTTP, BLE, I2C |
| **Build Tools** | Unity Build Pipeline, pip |

## Current Limitations

### 1. Separate Processes Required
- Flask server and BLE client run as separate processes (requires manual coordination)
- **Impact**: Two terminals needed, manual startup sequence, no integrated logging
- **Future**: Consider process manager (systemd, supervisord) or integrate into single service

### 3. Single Device Support
- Currently supports one ESP32 device at a time
- No device identifier or multi-device management
- **Future**: Multi-device support for collaborative building

### 4. Local BLE Requirement
- BLE client must run on machine with Bluetooth hardware near ESP32
- **Impact**: Limits deployment flexibility (can't easily deploy Flask server to cloud)
- **Future**: BLE bridge as separate microservice communicating with Flask via WebSocket/MQTT

### 5. In-Memory State Storage
- Current rotation state stored in Flask server memory (lost on restart)
- **Impact**: No persistence, no historical data
- **Future**: Database for persistent state and analytics

## Future Architecture Improvements

### 1. Separated BLE Bridge Service

**Current Status**: ✅ **WebSocket communication implemented** - Flask server and BLE client now use Socket.IO for real-time bidirectional communication. ✅ **Dynamic timer interval control implemented** - UI allows adjusting ESP32 sample rate (10-1000ms) via WebSocket.

**Remaining Issue**: BLE client and Flask server run as separate processes without process management, limiting scalability and deployment options.

**Proposed Architecture**:
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Unity     │  WS/HTTP│   Flask     │  WS/MQTT│ BLE Bridge  │   BLE   │   ESP32     │
│   WebGL     │◄───────►│   Server    │◄───────►│   Service   │◄───────►│   Device    │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
   Browser                Cloud/Any             Local Machine           Physical Device
```

**Benefits**:
- Deploy Flask server anywhere (cloud, containers)
- Scale Flask server independently of BLE hardware
- Multiple BLE bridges for multiple physical locations
- Better security isolation between components
- Centralized management and monitoring

### 2. Multi-Device Support via Device UID

**Current Limitation**: The `ble_client.py` connects to a single hardcoded device name and doesn't differentiate between multiple BLE servers.

**Proposed Implementation**:

1. **Device Identification**: Use MAC address or custom UID to track each ESP32 device
2. **Concurrent Connections**: Maintain multiple active BLE connections simultaneously
3. **Data Tagging**: Include device identifier in all sensor data sent to Flask API
4. **Device Registry**: Map device UIDs to user sessions or specific LEGO brick instances

**Code Structure**:
```python
# Multi-device connection management
devices = {
    "AA:BB:CC:DD:EE:FF": {"name": "ESP32_Brick_1", "connection": client1},
    "11:22:33:44:55:66": {"name": "ESP32_Brick_2", "connection": client2}
}

# Data format with device identifier
{
    "device_uid": "AA:BB:CC:DD:EE:FF",
    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    "timestamp": "2026-02-01T12:00:00Z"
}
```

**API Changes Required**:
- `/api/rotation/<device_uid>` - Accept rotation data for specific device
- `/api/devices/scan` - Discover available BLE devices
- `/api/devices/connect/<device_uid>` - Connect to specific device
- `/api/devices/disconnect/<device_uid>` - Disconnect specific device

**Benefits**:
- Support multiple LEGO bricks with individual motion tracking
- Enable collaborative building with multiple users
- Scale to sensor networks with multiple ESP32 devices
- Better device management and monitoring

### 3. Scalability Considerations

**Current State**: Single-process Flask server with WebSocket (Socket.IO), in-memory state, single ESP32 device. ✅ Dynamic timer interval control implemented.

**Production Requirements**:
- Message queue (Redis/RabbitMQ) for component communication
- Session management to isolate user data
- Device pool management and assignment

**Load Distribution**:
- Horizontal scaling of Flask server instances
- Load balancing for BLE bridge services
- Database for persistent device and session state
- Caching layer for frequently accessed data

## Security Considerations

### Current State
- BLE connection typically requires pairing
- No authentication on HTTP endpoints (development)
- CORS enabled for local development

### Production Recommendations
- Add authentication/authorization to web API
- Restrict CORS to specific domains
- Encrypt BLE communication
- Use HTTPS for web server
- Implement rate limiting

## Development Workflow

1. **Hardware Development**: Edit firmware → Upload to ESP32
2. **Backend Development**: Modify server code → Restart Flask
3. **Frontend Development**: Edit Unity → Build WebGL → Deploy to `server/static/webgl/`
4. **Testing**: Run server → Connect ESP32 → Open browser → Test interaction

## Monitoring and Debugging

- **Unity**: Console logs in browser developer tools
- **Server**: Flask console output, logging to file
- **Firmware**: Serial monitor in Arduino IDE
- **BLE**: Use BLE scanner apps to verify device advertising

## Performance Considerations

- **Sensor Sampling Rate**: Configurable in firmware (trade-off: latency vs. power)
- **Data Transmission**: Optimize payload size for BLE (28 bytes binary struct)
- **WebGL Rendering**: Unity performance depends on browser/hardware
- **Network Latency**: ✅ **WebSocket implemented** - Real-time push updates with low latency (no polling overhead)

## References

- [Unity WebGL Documentation](https://docs.unity3d.com/Manual/webgl.html)
- [ESP32 BLE Arduino](https://github.com/nkolban/ESP32_BLE_Arduino)
- [MPU6050 Library](https://github.com/rfetick/MPU6050_light)
- [Flask Documentation](https://flask.palletsprojects.com/)
