#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <MPU6050_light.h>
#include <Wire.h>

MPU6050 mpu(Wire);

BLEServer *pServer = NULL;
BLECharacteristic *pCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;

hw_timer_t *timer = NULL;
volatile bool readSensor = false;
unsigned long measurementInterval = 100; // milliseconds

// Compact binary struct - each field on own line
struct SensorData {
  uint32_t timestamp; // Timestamp (ms) - 4 bytes
  float accX;         // Accel X (g) - 4 bytes
  float accY;         // Accel Y (g) - 4 bytes
  float accZ;         // Accel Z (g) - 4 bytes
  float gyroX;        // Gyro X (°/s) - 4 bytes
  float gyroY;        // Gyro Y (°/s) - 4 bytes
  float gyroZ;        // Gyro Z (°/s) - 4 bytes
} __attribute__((packed));

#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

void IRAM_ATTR onTimer() { readSensor = true; }

class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *pServer) { deviceConnected = true; };

  void onDisconnect(BLEServer *pServer) { deviceConnected = false; }
};

void setup() {
  Serial.begin(115200);
  Wire.begin();

  byte status = mpu.begin();
  Serial.print(F("MPU6050 status: "));
  Serial.println(status);
  while (status != 0) {
  }

  Serial.println(F("Calculating offsets, do not move MPU6050"));
  Serial.println(F("Place device on FLAT, LEVEL surface!"));
  delay(3000); // Give yourself time to place it properly

  mpu.calcOffsets(true, true);

  Serial.println("Done!\n");

  // Print the calculated offsets to verify
  Serial.print("Accel offsets - X: ");
  Serial.print(mpu.getAccXoffset());
  Serial.print(" Y: ");
  Serial.print(mpu.getAccYoffset());
  Serial.print(" Z: ");
  Serial.println(mpu.getAccZoffset());

  Serial.print("Gyro offsets - X: ");
  Serial.print(mpu.getGyroXoffset());
  Serial.print(" Y: ");
  Serial.print(mpu.getGyroYoffset());
  Serial.print(" Z: ");
  Serial.println(mpu.getGyroZoffset());

  // BLE setup
  BLEDevice::init("ESP32_MPU6050_BLE");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);

  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);
  BLEDevice::startAdvertising();
  Serial.println(
      "Waiting for client (28-byte binary packets with timestamp)...");

  // Setup hardware timer interrupt (ESP32 v3.x API)
  timer = timerBegin(1000000);           // 1MHz timer frequency
  timerAttachInterrupt(timer, &onTimer); // Attach ISR
  timerAlarm(timer, measurementInterval * 1000, true,
             0); // microseconds, autoreload

  Serial.printf("Timer interrupt enabled: %lums interval\n",
                measurementInterval);
}

void loop() {
  // Only read sensor when timer interrupt fires
  if (deviceConnected && readSensor) {
    readSensor = false; // Clear flag

    mpu.update();

    SensorData data;

    // Assign each field explicitly on own line
    data.timestamp = millis();
    data.accX = mpu.getAccX();
    data.accY = mpu.getAccY();
    data.accZ = mpu.getAccZ();
    data.gyroX = mpu.getGyroX();
    data.gyroY = mpu.getGyroY();
    data.gyroZ = mpu.getGyroZ();

    pCharacteristic->setValue((uint8_t *)&data, sizeof(SensorData));
    pCharacteristic->notify();

    // Debug: Print values
    Serial.printf(
        "\n--- Timestamp: %ums (device should be FLAT and STILL) ---\n",
        data.timestamp);
    Serial.printf(
        "Accel: X=%.3f Y=%.3f Z=%.3f (mag=%.3f)\n", mpu.getAccX(),
        mpu.getAccY(), mpu.getAccZ(),
        sqrt(sq(mpu.getAccX()) + sq(mpu.getAccY()) + sq(mpu.getAccZ())));
    Serial.printf("Gyro:  X=%.3f Y=%.3f Z=%.3f\n", mpu.getGyroX(),
                  mpu.getGyroY(), mpu.getGyroZ());
    Serial.println("Expected: Accel mag ≈ 1.0, Gyro all ≈ 0");
  }

  // Yield to RTOS and reduce power consumption
  delay(1); // Allows task switching and reduces busy-waiting

  // Connection handling
  if (!deviceConnected && oldDeviceConnected) {
    delay(100);
    pServer->startAdvertising();
    Serial.println("Restart advertising");
    oldDeviceConnected = deviceConnected;
  }
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
  }
}
