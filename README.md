# ForceGripper

## 3D model

The [Lowrails HX711 M3 v3 sensor chamber](model/sensor_chamber.stl) is the current design. Its 38 × 10 mm lengthwise opening lets the 34 mm sensor pass through edge-first. The STL uses millimeters.

Regenerate it from [the CAD source](model/sensor_chamber.py) with Python 3.12:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r model/requirements.txt
.venv/bin/python model/sensor_chamber.py
```

Pass an output path to write a separate STL.

## Firmware

Flash [ForceGripper.ino](firmware/ForceGripper/ForceGripper.ino) to a DFRobot FireBeetle 2 ESP32-C6. Connect HX711 DOUT to GPIO 14, SCK to GPIO 8, and GND to the board's GND. Set the HX711 module to 80 samples/s if it has a RATE selector.

In Arduino IDE, install the **esp32** board package, **HX711** by Rob Tillaart, and **NimBLE-Arduino**. Select **DFRobot FireBeetle 2 ESP32-C6** then set **Tools → USB CDC On Boot → Enabled** and **Tools → Partition Scheme → Minimal SPIFFS**. The build was checked with ESP32 core 3.3.8, HX711 0.6.3, and NimBLE-Arduino 2.5.0.

```sh
arduino-cli compile --fqbn esp32:esp32:dfrobot_firebeetle2_esp32c6:CDCOnBoot=cdc,PartitionScheme=min_spiffs firmware/ForceGripper
arduino-cli compile --upload -p YOUR_PORT --fqbn esp32:esp32:dfrobot_firebeetle2_esp32c6:CDCOnBoot=cdc,PartitionScheme=min_spiffs firmware/ForceGripper
```

## Connections

USB serial and BLE are enabled by default. Enable Wi-Fi at the top of the sketch before flashing to use it alongside them. All transports report signed raw HX711 counts.

| Connection | How to read samples |
| --- | --- |
| USB serial | Open the board's USB port at **115200 baud**. Each sample is one CSV line, `seq,t_us,raw`. The port can also show startup messages and command responses. |
| BLE | Connect to **HX711_Wake_v1** and subscribe to characteristic **FFF1** under service **FFF0**. Send control commands to **FFF2**. |
| Wi-Fi access point | Set `WIFI_MODE` to `WifiMode::AccessPoint`. Set an AP password of at least eight characters and join the network named by `WIFI_AP_SSID`. Read the latest sample at `http://192.168.4.1/reading`. |
| Wi-Fi on an existing network | Set `WIFI_MODE` to `WifiMode::Station` and fill in the SSID and password locally. The board prints its IP over USB after joining. Read the latest sample at `http://BOARD_IP/reading`. |

Wi-Fi `GET /reading` returns JSON with `seq`, `t_us`, and `raw`. For a live UDP stream, set `WIFI_UDP_TARGET` to the receiver's IPv4 address. The board then sends one CSV line per sample to UDP port **5005**.

Each BLE sample notification contains `0xA6`, a one-byte sample count (normally 3), the first sample's sequence and timestamp as unsigned 32-bit values, and one signed 24-bit raw value per sample. All multi-byte values are little-endian. The batch stores the first timestamp only. Clients can estimate the following times at 12,500 µs intervals. Sequence numbers and microsecond timestamps wrap at 32 bits. USB and BLE accept commands such as `STATUS?` and `BASELINE:CAPTURE`. Command responses over BLE are text on the same notification characteristic.
