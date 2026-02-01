# Architecture Overview

## System Architecture

The LegoDemo project consists of three main components that work together to create an interactive LEGO building experience with motion sensing capabilities.

```
┌─────────────────┐          ┌─────────────────────────────┐          ┌─────────────────┐
│                 │          │  Python Server (2 processes)│          │                 │
│  Unity WebGL    │  HTTP    │  ┌────────────────────────┐ │   BLE    │   ESP32 + IMU   │
│  (Frontend)     │◄────────►│  │ Flask Server (app.py)  │ │          │   (Firmware)    │
│                 │          │  └────────────────────────┘ │◄────────►│                 │
│                 │          │  ┌────────────────────────┐ │          │                 │
│                 │          │  │ BLE Client (ble_      │ │          │                 │
│                 │          │  │   client.py)          │ │          │                 │
│                 │          │  └────────────────────────┘ │          │                 │
└─────────────────┘          └─────────────────────────────┘          └─────────────────┘
     Browser                   Flask + BLE on same machine            Physical Device
```

**Note:** Flask server and BLE client are separate processes that communicate via HTTP (BLE client posts to Flask API endpoints).

## Component Details

### 1. Unity (Frontend)
- **Technology**: Unity 3D Engine, WebGL
- **Purpose**: 3D visualization and user interaction
- **Features**:
  - Real-time LEGO brick rendering
  - Motion-based manipulation
  - Interactive building interface
- **Output**: WebGL build deployed to `server/static/webgl/`

### 2. Server (Backend + BLE Bridge)
- **Technology**: Python Flask + BLE libraries (Bleak)
- **Purpose**: Web server and Bluetooth communication bridge
- **Architecture**: Two separate processes
  - `app.py`: Flask server (serves WebGL, provides REST API, stores rotation state)
  - `ble_client.py`: BLE client (connects to ESP32, processes sensor data, posts to Flask API)
- **Responsibilities**:
  - Serve Unity WebGL application and static files
  - Provide REST API endpoints (`/api/rotation` GET/POST)
  - Connect to ESP32 via Bluetooth Low Energy
  - Process sensor data (complementary filter, axis mapping, drift compensation)
  - Bridge data between ESP32 hardware and web client
  - Real-time data synchronization via HTTP polling

### 3. Firmware (Hardware)
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

**Current Implementation** (One-way: ESP32 → Server → Unity):

1. **ESP32 Sensor Reading** → MPU6050 data read every 100ms via timer interrupt
2. **BLE Transmission** → ESP32 broadcasts sensor data via BLE notifications
3. **Python BLE Client** → Receives notifications and processes data (complementary filter, axis mapping, drift compensation)
4. **HTTP POST** → BLE client posts rotation data to Flask API (`/api/rotation`)
5. **State Storage** → Flask stores current rotation in memory
6. **Unity Polling** → Unity WebGL polls Flask API (`GET /api/rotation`) for updates
7. **Visual Update** → Unity renders LEGO brick with new rotation

**Note**: User input in Unity web interface can also POST rotation values directly to the API for manual control.

## Communication Protocols

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
- **Service UUID**: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
- **Characteristic UUID**: `beb5483e-36e1-4688-b7f5-ea07361b26a8`
- **Device Name**: `ESP32_MPU6050_BLE`

### HTTP
- **Purpose**: Browser-to-server communication
- **Usage**: Request/response for commands and rotation data
- **Current**: Polling-based updates from Unity to Flask
- **Future**: Consider WebSocket for real-time bidirectional streaming

## Technology Stack

| Component | Technologies |
|-----------|-------------|
| **Frontend** | Unity 3D, WebGL, C# |
| **Backend** | Python 3.8+, Flask, BLE libraries |
| **Firmware** | Arduino, ESP32, MPU6050_light |
| **Protocols** | HTTP, BLE, I2C |
| **Build Tools** | Unity Build Pipeline, pip |

## Current Limitations

### 1. Polling-Based Architecture
- Unity WebGL polls Flask API for rotation updates instead of real-time push
- **Impact**: Higher latency (~polling interval) and unnecessary network traffic
- **Future**: Implement WebSocket for real-time bidirectional communication

### 2. Separate Processes Required
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

### 1. WebSocket for Real-Time Communication

**Current Issue**: Unity WebGL polls Flask API repeatedly, causing latency and unnecessary requests.

**Proposed Architecture**:
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Unity     │   WS    │   Flask     │   WS    │ BLE Client  │
│   WebGL     │◄───────►│   Server    │◄───────►│   Process   │
└─────────────┘         └─────────────┘         └─────────────┘
```

**Benefits**:
- Real-time bidirectional communication
- Lower latency (push updates immediately)
- Reduced network overhead
- Better for multiple concurrent users

### 2. Separated BLE Bridge Service

**Current Issue**: BLE client and Flask server run as separate processes without coordination, limiting scalability and deployment options.

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

### 3. Multi-Device Support via Device UID

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

### 4. Scalability Considerations

**Current State**: Single-process Flask server with polling, in-memory state, single ESP32 device.

**Production Requirements**:
- Message queue (Redis/RabbitMQ) for component communication
- Session management to isolate user data
- WebSocket implementation for real-time updates per user (future)
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
- **Network Latency**: Currently using HTTP polling; WebSocket would reduce latency

## References

- [Unity WebGL Documentation](https://docs.unity3d.com/Manual/webgl.html)
- [ESP32 BLE Arduino](https://github.com/nkolban/ESP32_BLE_Arduino)
- [MPU6050 Library](https://github.com/rfetick/MPU6050_light)
- [Flask Documentation](https://flask.palletsprojects.com/)
