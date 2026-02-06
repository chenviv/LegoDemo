# BLE Client for ESP32 MPU6050

This client connects to the ESP32 via Bluetooth Low Energy (BLE) and sends rotation data to the Flask server via WebSocket (Socket.IO) for real-time bidirectional communication.

## Requirements

- Python 3.8+
- Bluetooth adapter on your machine
- ESP32 device running the firmware

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. Make sure the Flask server is running (either in Docker or locally):
   ```bash
   # If using Docker
   docker run -p 5000:5000 lego-server

   # Or locally
   cd ../server
   python app.py
   ```

2. Run the BLE client:
   ```bash
   python ble_client.py
   ```

The client will:
- Connect to Flask server WebSocket (Socket.IO) first
- Scan for the ESP32 device
- Connect via BLE
- Receive sensor data (accelerometer + gyroscope)
- Apply complementary filter for rotation calculation
- Send rotation data and BLE status to Flask server via WebSocket
- Automatic reconnection with exponential backoff for both BLE and WebSocket

## Configuration

You can modify these settings in `ble_client.py`:

- `SERVER_URL`: Flask server WebSocket endpoint (default: `http://localhost:5000`)
- `DEVICE_NAME`: ESP32 device name (default: `ESP32_MPU6050_BLE`)
- `MAX_RECONNECT_ATTEMPTS`: Number of reconnection attempts (default: 5)
- `RECONNECT_DELAY_BASE`: Base delay for exponential backoff (default: 2 seconds)
- `CONNECTION_TIMEOUT`: Connection timeout in seconds (default: 10)
- Complementary filter parameters: `alpha`, `gyro_deadband` in `ComplementaryFilter` class

## Troubleshooting

- **Cannot find device**: Make sure the ESP32 is powered on and advertising
- **Connection fails**: Check Bluetooth is enabled on your computer
- **WebSocket connection fails**: Verify the Flask server is running first at http://localhost:5000
- **"Connection refused" errors**: Ensure Flask server started successfully before running BLE client
- **Disconnections**: Client will automatically reconnect with exponential backoff for both BLE and WebSocket
