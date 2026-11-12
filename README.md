# ForceGripper

## 3D model

[Open or download the full v3 STEP assembly](model/forcegripper_v3.step). It includes the enclosure, two load cells, two contact discs, the HX711 breakout, the FireBeetle 2 ESP32-C6, and the battery.

![Lowrails v3 sensor chamber with a callout for its 38 by 10 mm lengthwise opening](model/images/sensor-chamber.png)

- **Printable parts:** [Sensor chamber](model/sensor_chamber.stl), [top cover](model/top_cover.stl), and [11 mm counterplate](model/counterplate.stl).
- **Component reference models:** [34 × 34 mm load cell](model/components/load_cell.stl), [two-hole HX711 breakout](model/components/hx711.stl), [FireBeetle 2 ESP32-C6](model/components/firebeetle.stl), and [46 × 24 × 8.4 mm battery](model/components/battery.stl).

The electronics, load cell details, and battery are simplified clearance models. The HX711 reference uses the v3 mounting pattern with two holes spaced 15.5 mm apart. Check your breakout and battery dimensions, including connectors and wires, before assembly. The FireBeetle board outline is 60 × 25.4 mm. [DFRobot specifications](https://wiki.dfrobot.com/dfr1075)

Regenerate all models in millimeters with Python 3.12:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r model/requirements.txt
.venv/bin/python model/assembly.py
```

Pass an output directory to export elsewhere. Run [sensor_chamber.py](model/sensor_chamber.py) to regenerate just the chamber.

## Assembly

![Exploded v3 assembly showing the top cover, three electronics components, chamber, two load cells, contact discs, and counterplate](model/images/exploded-assembly.png)

1. Feed each load cell edge-first through the **38 × 10 mm** slot, with its 34 mm edge parallel to the long side of the chamber. Rotate it flat into the channel, orient its load tip down and toward the center, then slide it along the rails toward its end stop. Route the leads back up through the center slot.
2. Mount the HX711 on the two M3 bosses and the FireBeetle on the four M2 bosses. Place the battery between them, keeping the exposed end of the center slot clear for the sensor leads. Face the FireBeetle USB-C port toward the opening in the cover.
3. Seat two one-cent euro coins as contact discs in the counterplate pockets and face the pockets toward the load tips. Place the top cover over the electronics and align the counterplate below the chamber. Fit the four M3 heat-set inserts in the chamber. The corner screws pass through the cover, thread through the inserts, and reach the nuts in the counterplate. Verify the load tips move freely and the wires stay clear before closing.

![Underside view showing both load cell tips facing inward and arrows toward the two rail stops](model/images/load-cell-placement.png)

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

## Python examples

Install the reader dependencies in the same virtual environment. Each example writes `seq,t_us,raw` CSV to standard output. Append `> samples.csv` to record a session and press Ctrl+C to stop.

```sh
.venv/bin/python -m pip install -r examples/requirements.txt

# USB serial. List ports with python -m serial.tools.list_ports.
.venv/bin/python examples/read_serial.py /dev/cu.usbmodem101

# BLE. Uses HX711_Wake_v1 by default.
.venv/bin/python examples/read_ble.py

# Wi-Fi HTTP. Use the board's IP for station mode.
.venv/bin/python examples/read_wifi.py http 192.168.4.1

# Wi-Fi UDP. Set WIFI_UDP_TARGET to this computer's IPv4 address before flashing.
.venv/bin/python examples/read_wifi.py udp
```

Use UDP for the Wi-Fi sample stream. HTTP polls the latest reading, so it can repeat or skip sample numbers. The BLE reader estimates the timestamps after the first sample of each batch.
