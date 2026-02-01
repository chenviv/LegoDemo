# Architecture Overview

## System Architecture

The LegoDemo project consists of three main components that work together to create an interactive LEGO building experience with motion sensing capabilities.

```
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│                 │          │                 │          │                 │
│  Unity WebGL    │  HTTP    │  Flask Server   │   BLE    │   ESP32 + IMU   │
│  (Frontend)     │◄────────►│  + BLE Client   │◄────────►│   (Firmware)    │
│                 │          │                 │          │                 │
└─────────────────┘          └─────────────────┘          └─────────────────┘
     Browser                   Python Server              Physical Device
```

## Component Details

### 1. Unity (Frontend)
- **Technology**: Unity 3D Engine, WebGL
- **Purpose**: 3D visualization and user interaction
- **Features**:
  - Real-time LEGO brick rendering
  - Motion-based manipulation
  - Interactive building interface
- **Output**: WebGL build deployed to `/build/webgl`

### 2. Server (Backend + BLE Bridge)
- **Technology**: Python Flask + BLE libraries
- **Purpose**: Web server and Bluetooth communication bridge
- **Components**:
  - `app.py`: Flask application serving WebGL and API endpoints
  - `ble_client.py`: Bluetooth Low Energy client for ESP32 communication
- **Responsibilities**:
  - Serve Unity WebGL application
  - Manage BLE connection to ESP32
  - Bridge data between web client and hardware
  - Real-time data synchronization

### 3. Firmware (Hardware)
- **Technology**: Arduino/ESP32, MPU6050 sensor
- **Purpose**: Motion sensing and data transmission
- **Features**:
  - 6-axis motion sensing (accelerometer + gyroscope)
  - BLE server implementation
  - Continuous data streaming
  - Low-latency sensor readings

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

1. **User Interaction** → Unity WebGL captures user input
2. **HTTP Request** → Sent to Flask server
3. **BLE Command** → Server forwards to ESP32 via BLE
4. **Sensor Response** → ESP32 sends motion data back
5. **Data Update** → Server pushes to Unity WebGL
6. **Visual Update** → Unity renders changes

## Communication Protocols

### BLE (Bluetooth Low Energy)
- **Purpose**: Hardware-to-software communication
- **Advantages**:
  - Low power consumption
  - Suitable for continuous data streaming
  - Good range (10-100m depending on environment)
- **Data Format**: Binary/JSON encoded sensor readings

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

### 1. Coupled Architecture
- BLE client and web server run in the same process
- **Impact**: Server must be on machine with Bluetooth hardware
- **Future**: Consider separating into microservices

### 2. Single Device Support
- Currently supports one ESP32 device at a time
- **Future**: Multi-device support for collaborative building

### 3. Local Deployment Only
- Bluetooth requirement limits deployment options
- **Future**: BLE bridge as separate service for cloud deployment

## Future Architecture Improvements

### 1. Separated BLE Bridge

**Current Issue**: BLE client and web server are coupled in one process, limiting deployment flexibility.

**Proposed Architecture**:
```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Unity     │  HTTP   │   Flask     │  WS/MQ  │ BLE Bridge  │   BLE   │   ESP32     │
│   WebGL     │◄───────►│   Server    │◄───────►│   Service   │◄───────►│   Device    │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
   Browser                Cloud/Any             Local Machine           Physical Device
```

**Benefits**:
- Deploy web server anywhere (cloud)
- Scale web server independently
- Multiple BLE bridges for multiple devices
- Better security isolation

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

**Multi-User Support**:
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
3. **Frontend Development**: Edit Unity → Build WebGL → Deploy to `/build/webgl`
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
