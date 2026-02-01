# Firmware

ESP32 firmware for the LegoDemo project with MPU6050 motion sensor integration.

## Hardware Requirements

- ESP32 development board
- MPU6050 IMU sensor (accelerometer + gyroscope)
- Connection wires

## Wiring

Connect MPU6050 to ESP32:
- VCC → 3.3V
- GND → GND
- SCL → GPIO 22 (default I2C clock)
- SDA → GPIO 21 (default I2C data)

## Software Requirements

- Arduino IDE 1.8.x or later
- ESP32 board support installed
- MPU6050_light library

## Installation

### 1. Install Arduino IDE

Download from [arduino.cc](https://www.arduino.cc/en/software)

### 2. Add ESP32 Board Support

1. Open Arduino IDE
2. Go to File → Preferences
3. Add to "Additional Board Manager URLs":
   ```
   https://dl.espressif.com/dl/package_esp32_index.json
   ```
4. Go to Tools → Board → Board Manager
5. Search "esp32" and install "ESP32 by Espressif Systems"

### 3. Install MPU6050_light Library

1. Go to Sketch → Include Library → Manage Libraries
2. Search "MPU6050_light"
3. Install the library by rfetick

### 4. Configure and Upload

1. Open `LEGO.ino` in Arduino IDE
2. Select your ESP32 board: Tools → Board → ESP32 Arduino → (your board)
3. Select the correct port: Tools → Port → (your COM/USB port)
4. Click Upload (→) button

## BLE Configuration

The firmware implements a BLE server with the following characteristics:
- Device name: "LEGO_ESP32" (configurable in code)
- Service UUID: (check LEGO.ino for current UUIDs)
- Characteristic UUID: (check LEGO.ino for current UUIDs)

## Features

- Real-time motion data collection from MPU6050
- BLE server for wireless communication
- Sensor calibration on startup
- Continuous data streaming

## Troubleshooting

### Upload fails:
- Check USB cable connection
- Press and hold BOOT button during upload
- Verify correct COM port selected

### Sensor not responding:
- Check I2C wiring
- Verify MPU6050 power supply (3.3V)
- Try sensor calibration

### BLE not visible:
- Ensure Bluetooth is enabled on client device
- Check if device name appears in BLE scanner
- Verify ESP32 is not already connected to another device

## Configuration

Edit `LEGO.ino` to customize:
- BLE device name
- Service/Characteristic UUIDs
- Sensor sampling rate
- Data format

## License

MIT
