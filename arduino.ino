#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

// Analog data collection settings
const int ANALOG_PIN = 34;              // GPIO34 - Analog input pin (use 32, 33, 34, 35, 36, or 39)
const int SAMPLES_PER_PACKET = 250;     // 250 samples × 2 bytes = 500 bytes per packet (max BLE payload)
const int SAMPLE_INTERVAL_US = 1000;    // 1000 µs = 1 ms between samples (1 kHz sampling rate)

// Speed testing variables
unsigned long lastTime = 0;
unsigned long bytesSent = 0;
unsigned long packetsSent = 0;
unsigned long sampleCount = 0;

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Device connected");
      
      // Request optimal connection parameters for speed
      // (interval min, interval max, latency, timeout)
      // Shorter intervals = faster updates but more power consumption
      // Note: updateConnParams may not be available in all ESP32 BLE library versions
      // If this still causes issues, you can comment out or remove this line
      // pServer->updateConnParams(6, 6, 0, 500); 
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Device disconnected");
      BLEDevice::startAdvertising();
    }
};

void setup() {
  Serial.begin(115200);
  Serial.println("Starting HIGH SPEED BLE with Analog Data!");

  // Configure analog pin
  pinMode(ANALOG_PIN, INPUT);
  
  // Set ADC resolution (ESP32 specific)
  analogReadResolution(12); // 12-bit ADC (0-4095)
  analogSetAttenuation(ADC_11db); // Full range 0-3.3V

  // Initialize BLE
  BLEDevice::init("ESP32_ADC_BLE");
  
  // Set MTU size (Maximum Transmission Unit)
  BLEDevice::setMTU(512); // Max MTU, gives us ~500 bytes per packet

  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x06); // Faster connection interval
  BLEDevice::startAdvertising();
  
  Serial.println("Waiting for connection...");
  Serial.printf("Sampling at %d Hz, sending %d samples per packet\n", 
                1000000/SAMPLE_INTERVAL_US, SAMPLES_PER_PACKET);
  lastTime = millis();
}

void loop() {
  // Read and plot analog values to Serial (works with or without BLE connection)
  int analogValue = analogRead(ANALOG_PIN); // Read 12-bit value (0-4095)
  
  // Print to Serial for Arduino Serial Plotter
  Serial.println(analogValue);
  
  // If BLE is connected, also send via BLE
  if (deviceConnected) {
    // Buffer to hold analog samples (250 samples × 2 bytes = 500 bytes)
    static uint8_t data[500];
    static uint16_t* samples = (uint16_t*)data;
    static int sampleIndex = 0;
    
    // Store the sample
    samples[sampleIndex] = analogValue;
    sampleIndex++;
    sampleCount++;
    
    // When we have enough samples, send the packet
    if (sampleIndex >= SAMPLES_PER_PACKET) {
      pCharacteristic->setValue(data, sizeof(data));
      pCharacteristic->notify();
      
      bytesSent += sizeof(data);
      packetsSent++;
      sampleIndex = 0; // Reset for next packet
    }
    
    // Print throughput and sample stats every second
    if (millis() - lastTime >= 1000) {
      float kbps = (bytesSent * 8.0) / 1024.0;
      float kBps = bytesSent / 1024.0;
      float samplesPerSec = sampleCount;
      
      Serial.printf("BLE Stats - Throughput: %.2f KB/s | Packets: %lu | Samples: %.0f/sec\n", 
                    kBps, packetsSent, samplesPerSec);
      
      bytesSent = 0;
      packetsSent = 0;
      sampleCount = 0;
      lastTime = millis();
    }
  }
  
  // Control sample rate
  delayMicroseconds(SAMPLE_INTERVAL_US);
}