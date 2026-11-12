#include <Arduino.h>
#include <HX711.h>
#include <NimBLEDevice.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <atomic>

enum class WifiMode { Off, AccessPoint, Station };

static constexpr WifiMode WIFI_MODE = WifiMode::Off;
static const char *WIFI_AP_SSID = "ForceGripper_AP";
static const char *WIFI_AP_PASSWORD = "forcegripper";
static const char *WIFI_STA_SSID = "";
static const char *WIFI_STA_PASSWORD = "";
// Leave empty to use HTTP only, or set the receiver's IPv4 address.
static const char *WIFI_UDP_TARGET = "";
static constexpr uint16_t WIFI_UDP_PORT = 5005;

WebServer http(80);
WiFiUDP udp;
IPAddress udpTarget;
bool udpEnabled = false;
bool wifiStarted = false;
bool stationWasConnected = false;
bool sampleAvailable = false;
uint32_t latestSequence = 0;
uint32_t latestTimeUs = 0;
int32_t latestRaw = 0;

// Keep the BLE name and UUIDs used by existing clients.
static const char *BLE_DEVICE_NAME = "HX711_Wake_v1";

// The FireBeetle ESP32-C6/NimBLE/iOS path has been reliable with 16-bit UUIDs.
static const char *FORCE_SERVICE_UUID = "fff0";
static const char *FORCE_TX_CHAR_UUID = "fff1";
static const char *FORCE_RX_CHAR_UUID = "fff2";

static const int HX711_DATA_PIN = 14;
static const int HX711_CLOCK_PIN = 8;
static const int LED_PIN = 15;

static const uint32_t SAMPLE_RATE_HZ = 80;
static const uint32_t SAMPLE_INTERVAL_US = 1000000UL / SAMPLE_RATE_HZ;
static const uint8_t BLE_SAMPLE_BATCH_MAGIC = 0xA6;
static const uint8_t BLE_SAMPLE_BATCH_SIZE = 3;
static const size_t BLE_SAMPLE_BATCH_HEADER_BYTES = 10;
static const size_t BLE_SAMPLE_BATCH_PACKET_BYTES =
  BLE_SAMPLE_BATCH_HEADER_BYTES + (BLE_SAMPLE_BATCH_SIZE * 3);
static const unsigned long SERIAL_BAUD = 115200;
static const uint32_t DEFAULT_WAKE_PERIOD_SECONDS = 10;
static const int32_t DEFAULT_WAKE_THRESHOLD_COUNTS = 50000;

HX711 scale;
Preferences prefs;
NimBLECharacteristic *txCharacteristic = nullptr;

std::atomic<bool> bleClientConnected{false};
std::atomic<bool> resetBleBatch{false};
QueueHandle_t bleCommands;
struct BleCommand {
  char text[128];
};
bool hx711Started = false;
bool configDirty = false;
bool configured = false;
int32_t baselineRaw = 0;
int32_t wakeThresholdCounts = DEFAULT_WAKE_THRESHOLD_COUNTS;
uint32_t wakePeriodSeconds = DEFAULT_WAKE_PERIOD_SECONDS;
int32_t lastRaw = 0;
uint32_t sampleSeq = 0;
uint32_t nextSampleAtUs = 0;
int32_t sampleRawBatch[BLE_SAMPLE_BATCH_SIZE];
uint32_t batchBaseSeq = 0;
uint32_t batchBaseTimeUs = 0;
uint8_t batchCount = 0;
String serialCommandBuffer;
unsigned long lastLedPulseAt = 0;

void ledOn(bool on) {
  digitalWrite(LED_PIN, on ? HIGH : LOW);
}

void blinkLed(int times, int onMs = 80, int offMs = 80) {
  for (int i = 0; i < times; i++) {
    ledOn(true);
    delay(onMs);
    ledOn(false);
    delay(offMs);
  }
}

void pulseLed(unsigned long now, unsigned long intervalMs, int onMs = 40) {
  if (now - lastLedPulseAt < intervalMs) return;
  lastLedPulseAt = now;
  ledOn(true);
  delay(onMs);
  ledOn(false);
}

void loadConfig() {
  prefs.begin("gripper", false);
  configured = prefs.getBool("configured", false);
  baselineRaw = prefs.getInt("baseline", 0);
  wakeThresholdCounts = prefs.getInt(
    "threshold",
    DEFAULT_WAKE_THRESHOLD_COUNTS
  );
  wakePeriodSeconds = prefs.getUInt(
    "wake_sec",
    DEFAULT_WAKE_PERIOD_SECONDS
  );
  if (wakePeriodSeconds < 1) wakePeriodSeconds = DEFAULT_WAKE_PERIOD_SECONDS;
  if (wakeThresholdCounts < 1) {
    wakeThresholdCounts = DEFAULT_WAKE_THRESHOLD_COUNTS;
  }
}

void saveConfig() {
  prefs.putBool("configured", configured);
  prefs.putInt("baseline", baselineRaw);
  prefs.putInt("threshold", wakeThresholdCounts);
  prefs.putUInt("wake_sec", wakePeriodSeconds);
  configDirty = false;
}

void clearConfig() {
  prefs.clear();
  configured = false;
  baselineRaw = 0;
  wakeThresholdCounts = DEFAULT_WAKE_THRESHOLD_COUNTS;
  wakePeriodSeconds = DEFAULT_WAKE_PERIOD_SECONDS;
  configDirty = false;
}

void startHx711() {
  if (hx711Started) return;
  scale.begin(HX711_DATA_PIN, HX711_CLOCK_PIN);
  hx711Started = true;
  delay(25);
}

bool readRawWithTimeout(int32_t &raw, unsigned long timeoutMs = 300) {
  startHx711();
  const unsigned long start = millis();
  while (!scale.is_ready()) {
    if (millis() - start > timeoutMs) return false;
    delayMicroseconds(250);
  }
  raw = static_cast<int32_t>(scale.read());
  lastRaw = raw;
  return true;
}

bool readMedianRaw(int32_t &raw, int count = 9) {
  if (count < 1) count = 1;
  if (count > 15) count = 15;
  int32_t values[15];
  int got = 0;

  for (int i = 0; i < 2; i++) {
    int32_t ignored;
    readRawWithTimeout(ignored, 500);
  }

  while (got < count) {
    int32_t sample;
    if (readRawWithTimeout(sample, 700)) {
      values[got++] = sample;
    } else if (got == 0) {
      return false;
    } else {
      break;
    }
  }

  for (int i = 1; i < got; i++) {
    const int32_t value = values[i];
    int j = i - 1;
    while (j >= 0 && values[j] > value) {
      values[j + 1] = values[j];
      j--;
    }
    values[j + 1] = value;
  }
  raw = values[got / 2];
  lastRaw = raw;
  return true;
}

void sendLine(const String &line) {
  Serial.println(line);
  if (bleClientConnected && txCharacteristic != nullptr) {
    const String payload = line + "\n";
    txCharacteristic->setValue(payload.c_str());
    txCharacteristic->notify(
      reinterpret_cast<const uint8_t *>(payload.c_str()),
      payload.length()
    );
  }
}

void writeInt24Le(uint8_t *target, int32_t value) {
  target[0] = static_cast<uint8_t>(value & 0xFF);
  target[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  target[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
}

void resetSampleBatch() {
  batchBaseSeq = 0;
  batchBaseTimeUs = 0;
  batchCount = 0;
}

void notifySampleBatch() {
  if (
    !bleClientConnected ||
    txCharacteristic == nullptr ||
    batchCount == 0
  ) {
    return;
  }

  uint8_t packet[BLE_SAMPLE_BATCH_PACKET_BYTES];
  packet[0] = BLE_SAMPLE_BATCH_MAGIC;
  packet[1] = batchCount;
  memcpy(packet + 2, &batchBaseSeq, sizeof(batchBaseSeq));
  memcpy(packet + 6, &batchBaseTimeUs, sizeof(batchBaseTimeUs));
  for (uint8_t i = 0; i < batchCount; i++) {
    writeInt24Le(packet + BLE_SAMPLE_BATCH_HEADER_BYTES + (i * 3), sampleRawBatch[i]);
  }

  const size_t packetBytes = BLE_SAMPLE_BATCH_HEADER_BYTES + (batchCount * 3);
  txCharacteristic->setValue(packet, packetBytes);
  txCharacteristic->notify(packet, packetBytes);
  resetSampleBatch();
}

bool usbPowerPresent() {
#if ARDUINO_USB_CDC_ON_BOOT && ARDUINO_USB_MODE
  return HWCDC::isPlugged();
#elif ARDUINO_USB_CDC_ON_BOOT
  return static_cast<bool>(Serial);
#else
  return false;
#endif
}

bool shouldStayAwake() {
  return usbPowerPresent();
}

bool transportClientConnected() {
  return bleClientConnected || usbPowerPresent() || wifiStarted;
}

void handleCommand(String command);

void processSerialCommands() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == '\n' || incoming == '\r') {
      if (serialCommandBuffer.length() > 0) {
        handleCommand(serialCommandBuffer);
        serialCommandBuffer = "";
      }
      continue;
    }
    if (serialCommandBuffer.length() < 127) {
      serialCommandBuffer += incoming;
    } else {
      serialCommandBuffer = "";
      sendLine("ERR,usb_command_too_long=1");
    }
  }
}

void sendConfigStatus(const char *prefix = "CFG") {
  String line(prefix);
  line += ",default_active=1";
  line += ",configured=";
  line += configured ? "1" : "0";
  line += ",baseline=";
  line += baselineRaw;
  line += ",threshold=";
  line += wakeThresholdCounts;
  line += ",wake_sec=";
  line += wakePeriodSeconds;
  line += ",last_raw=";
  line += lastRaw;
  line += ",usb_power=";
  line += usbPowerPresent() ? "1" : "0";
  line += ",keep_awake=";
  line += shouldStayAwake() ? "1" : "0";
  sendLine(line);
}

void handleCommand(String command) {
  command.trim();
  if (command.length() == 0) return;
  const String original = command;
  command.toUpperCase();

  if (command == "STATUS?") {
    sendConfigStatus();
    return;
  }

  if (command == "BASELINE:CAPTURE") {
    sendLine("CFG,capturing_baseline=1");
    ledOn(true);
    int32_t raw;
    if (!readMedianRaw(raw, 11)) {
      ledOn(false);
      sendLine("ERR,hx711_not_ready=1");
      blinkLed(6, 40, 40);
      return;
    }
    baselineRaw = raw;
    configured = true;
    if (wakeThresholdCounts < 1) {
      wakeThresholdCounts = DEFAULT_WAKE_THRESHOLD_COUNTS;
    }
    saveConfig();
    ledOn(false);
    blinkLed(3);
    sendConfigStatus("CFG,baseline_saved=1");
    return;
  }

  if (command.startsWith("BASELINE:")) {
    baselineRaw = original.substring(String("BASELINE:").length()).toInt();
    configured = true;
    saveConfig();
    blinkLed(3);
    sendConfigStatus("CFG,baseline_saved=1");
    return;
  }

  if (command.startsWith("WAKE_THRESHOLD:")) {
    const int32_t threshold = original
      .substring(String("WAKE_THRESHOLD:").length())
      .toInt();
    if (threshold < 1) {
      sendLine("ERR,bad_threshold=1");
      return;
    }
    wakeThresholdCounts = threshold;
    if (configured) saveConfig();
    blinkLed(2);
    sendConfigStatus("CFG,threshold_saved=1");
    return;
  }

  if (command.startsWith("WAKE_SEC:")) {
    const int seconds = original.substring(String("WAKE_SEC:").length()).toInt();
    if (seconds < 1 || seconds > 3600) {
      sendLine("ERR,bad_wake_sec=1");
      return;
    }
    wakePeriodSeconds = static_cast<uint32_t>(seconds);
    if (configured) saveConfig();
    blinkLed(2);
    sendConfigStatus("CFG,wake_sec_saved=1");
    return;
  }

  if (command == "CLEAR_CONFIG") {
    clearConfig();
    blinkLed(5, 50, 50);
    sendConfigStatus("CFG,cleared=1");
    return;
  }

  if (command == "SLEEP" || command == "FORCE_SLEEP") {
    sendLine("CFG,sleep_disabled=1");
    return;
  }

  if (command == "LED:ON") {
    ledOn(true);
    sendLine("CFG,led=on");
    return;
  }

  if (command == "LED:OFF") {
    ledOn(false);
    sendLine("CFG,led=off");
    return;
  }

  sendLine("ERR,unknown_command=1");
}

class RxCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *characteristic, NimBLEConnInfo &connInfo)
      override {
    const auto value = characteristic->getValue();
    BleCommand command{};
    if (value.size() >= sizeof(command.text)) return;
    memcpy(command.text, value.data(), value.size());
    xQueueSend(bleCommands, &command, 0);
  }
} rxCallbacks;

class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer *server, NimBLEConnInfo &connInfo) override {
    bleClientConnected = true;
    resetBleBatch = true;
    Serial.println("BLE connected");
    Serial.printf(
      "BLE conn interval=%.2fms mtu=%u\n",
      connInfo.getConnInterval() * 1.25f,
      connInfo.getMTU()
    );
  }

  void onDisconnect(
    NimBLEServer *server,
    NimBLEConnInfo &connInfo,
    int reason
  ) override {
    bleClientConnected = false;
    resetBleBatch = true;
    Serial.println("BLE disconnected; advertising");
    NimBLEDevice::startAdvertising();
  }
} serverCallbacks;

void setupBle() {
  bleCommands = xQueueCreate(4, sizeof(BleCommand));
  if (bleCommands == nullptr) {
    Serial.println("BLE initialization failed");
    return;
  }
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);

  NimBLEServer *server = NimBLEDevice::createServer();
  server->setCallbacks(&serverCallbacks);

  NimBLEService *forceService = server->createService(FORCE_SERVICE_UUID);

  txCharacteristic = forceService->createCharacteristic(
    FORCE_TX_CHAR_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
  );
  txCharacteristic->setValue("0\n");

  NimBLECharacteristic *rxCharacteristic = forceService->createCharacteristic(
    FORCE_RX_CHAR_UUID,
    NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR
  );
  rxCharacteristic->setCallbacks(&rxCallbacks);

  forceService->start();

  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->setName(BLE_DEVICE_NAME);
  advertising->addServiceUUID(forceService->getUUID());
  advertising->enableScanResponse(true);
  advertising->setMinInterval(160);
  advertising->setMaxInterval(240);
  advertising->start();
  Serial.printf("BLE advertising as %s\n", BLE_DEVICE_NAME);
}

void handleReading() {
  if (!sampleAvailable) {
    http.send(503, "application/json", "{\"error\":\"no_sample\"}");
    return;
  }
  char json[96];
  snprintf(json, sizeof(json), "{\"seq\":%lu,\"t_us\":%lu,\"raw\":%ld}",
           static_cast<unsigned long>(latestSequence),
           static_cast<unsigned long>(latestTimeUs),
           static_cast<long>(latestRaw));
  http.send(200, "application/json", json);
}

void setupWifi() {
  switch (WIFI_MODE) {
    case WifiMode::Off:
      return;
    case WifiMode::AccessPoint:
      WiFi.mode(WIFI_AP);
      if (!WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASSWORD)) {
        Serial.println("Wi-Fi access point failed to start");
        return;
      }
      Serial.print("Wi-Fi access point IP: ");
      Serial.println(WiFi.softAPIP());
      break;
    case WifiMode::Station:
      if (WIFI_STA_SSID[0] == '\0') {
        Serial.println("Wi-Fi station needs an SSID");
        return;
      }
      WiFi.mode(WIFI_STA);
      WiFi.setAutoReconnect(true);
      WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);
      break;
  }

  udpEnabled = udpTarget.fromString(WIFI_UDP_TARGET);
  if (WIFI_UDP_TARGET[0] != '\0' && !udpEnabled) {
    Serial.println("Invalid Wi-Fi UDP destination");
  }
  http.on("/reading", HTTP_GET, handleReading);
  http.begin();
  wifiStarted = true;
}

bool wifiConnected() {
  if (!wifiStarted) return false;
  if (WIFI_MODE == WifiMode::AccessPoint) return true;
  return WiFi.status() == WL_CONNECTED;
}

void pollWifi() {
  const bool connected = wifiConnected();
  if (WIFI_MODE == WifiMode::Station && connected && !stationWasConnected) {
    Serial.print("Wi-Fi station IP: ");
    Serial.println(WiFi.localIP());
  }
  stationWasConnected = connected;
  if (connected) http.handleClient();
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  ledOn(false);
  Serial.begin(SERIAL_BAUD);
  delay(500);
  Serial.println();
  Serial.println("ForceGripper HX711");
  Serial.printf("HX711 data pin=%d clock pin=%d\n", HX711_DATA_PIN, HX711_CLOCK_PIN);
  Serial.printf("LED pin=%d\n", LED_PIN);

  loadConfig();
  sendConfigStatus();

  setupBle();
  setupWifi();
  if (!configured) {
    blinkLed(2, 60, 60);
  }
}

void publishSample(uint32_t seq, uint32_t sampleTimeUs, long raw) {
  char line[48];
  const int bytes = snprintf(line, sizeof(line), "%lu,%lu,%ld\n",
                            static_cast<unsigned long>(seq),
                            static_cast<unsigned long>(sampleTimeUs),
                            raw);
  if (usbPowerPresent()) Serial.print(line);

  latestSequence = seq;
  latestTimeUs = sampleTimeUs;
  latestRaw = static_cast<int32_t>(raw);
  sampleAvailable = true;
  if (udpEnabled && wifiConnected() && udp.beginPacket(udpTarget, WIFI_UDP_PORT)) {
    udp.write(reinterpret_cast<const uint8_t *>(line), bytes);
    udp.endPacket();
  }

  if (bleClientConnected && txCharacteristic != nullptr) {
    const int32_t raw32 = static_cast<int32_t>(raw);
    if (batchCount == 0) {
      batchBaseSeq = seq;
      batchBaseTimeUs = sampleTimeUs;
    }
    sampleRawBatch[batchCount++] = raw32;
    if (batchCount >= BLE_SAMPLE_BATCH_SIZE) {
      notifySampleBatch();
    }
  }
}

void loop() {
  const unsigned long now = millis();
  processSerialCommands();
  BleCommand command;
  if (bleCommands != nullptr && xQueueReceive(bleCommands, &command, 0) == pdTRUE) {
    handleCommand(command.text);
  }
  if (resetBleBatch.exchange(false)) resetSampleBatch();
  pollWifi();

  if (!transportClientConnected()) {
    pulseLed(now, configured ? 2000 : 900, configured ? 35 : 55);
    delay(50);
    return;
  }

  if (!hx711Started) {
    Serial.println("Starting HX711 transport stream");
    startHx711();
    sampleSeq = 0;
    resetSampleBatch();
    nextSampleAtUs = micros();
    return;
  }

  const uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - nextSampleAtUs) < 0) {
    delay(1);
    return;
  }

  int32_t raw;
  if (!readRawWithTimeout(raw, 14)) {
    if (Serial) {
      Serial.println("HX711 not ready");
    }
    nextSampleAtUs = micros() + SAMPLE_INTERVAL_US;
    return;
  }

  const uint32_t sampleTimeUs = micros();
  publishSample(sampleSeq++, sampleTimeUs, raw);
  nextSampleAtUs += SAMPLE_INTERVAL_US;
  if (static_cast<int32_t>(sampleTimeUs - nextSampleAtUs) > static_cast<int32_t>(SAMPLE_INTERVAL_US)) {
    nextSampleAtUs = sampleTimeUs + SAMPLE_INTERVAL_US;
  }
}
