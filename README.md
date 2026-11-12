# ForceGripper

Lowrails HX711 M3 v3. [Full STEP assembly](model/forcegripper_v3.step) · [Chamber view](model/images/sensor-chamber.png) · [CAD source](model/assembly.py) · [Firmware](firmware/ForceGripper/ForceGripper.ino) · [Python readers](#read-samples)

## Parts per gripper

| Qty | Part |
| ---: | --- |
| 1 each | Printed [sensor chamber](model/sensor_chamber.stl), [top cover](model/top_cover.stl), and [11 mm counterplate](model/counterplate.stl) |
| 2 | 34 × 34 mm three-wire half-bridge load cells |
| 1 | [Soldered Electronics HX711 breakout, 333005](https://solde.red/333005) |
| 1 | [DFRobot FireBeetle 2 ESP32-C6, DFR1075](https://www.dfrobot.com/product-2771.html) |
| 1 | LiPo battery. We used the pack measured at **46 × 24 × 8.4 mm**. The brand and capacity aren’t recorded. |
| 4 each | M3 socket-head screws, M3 heat-set inserts, and **M3 nylon nuts** |
| 2 + 4 | Short M3 screws for the HX711 and short M2 screws for the FireBeetle |
| 2 | One-cent euro coins for the counterplate contact pockets |
| As needed | Hookup wire and heat-shrink tubing for the two sensor splices |

| Three-wire half-bridge load cells | Soldered HX711 333005 | FireBeetle 2 ESP32-C6 |
| :---: | :---: | :---: |
| <img src="https://sensor-con.com/products/SC134-HB-1024-iso.png" alt="Representative square three-wire half-bridge load cells" width="180"> | <img src="https://mm.digikey.com/Volume0/opasdata/d220001/derivates/1/002/203/396/MFG_333005_secondary_sml%28200x200%29.jpg" alt="Soldered Electronics HX711 breakout 333005" width="180"> | <img src="https://dfimg.dfrobot.com/enshop/DFR1075/DFR1075_Main_01.jpg" alt="DFRobot FireBeetle 2 ESP32-C6 DFR1075" width="180"> |

The load-cell photo shows a representative half-bridge model. The part number of the cells used in the gripper is unconfirmed. [Sensor and Control](https://sensor-con.com/product/sc134/) · [DigiKey](https://www.digikey.com/en/products/detail/soldered-electronics/333005/21720457) · [DFRobot](https://www.dfrobot.com/product-2771.html)

## 1. Fit the load cells

Pass each cell edge-first through the **38 × 10 mm** slot. Turn it flat with the tip down and toward the center, then slide it along the rails to its end stop. Route both sets of leads back through the slot.

![Load cells on the chamber rails with their tips facing inward](model/images/load-cell-placement.png)

## 2. Wire the bridge and boards

![Wiring diagram with both white-to-black splices, separate red leads, and the four HX711-to-FireBeetle connections](model/images/wiring.svg)

This wiring forms one Wheatstone bridge from two three-wire half-bridges. With power disconnected and the cells separated, check each with a multimeter. **White–black should read approximately the sum of red–white and red–black**, with the two red-to-end readings roughly equal at rest. This identifies red as the center tap. [SparkFun sensor lead reference](https://docs.sparkfun.com/SparkFun_OpenScale_IoT/single_page/#load-sensor-combinator)

| HX711 | Connect to |
| --- | --- |
| **E+** | Cell A white **joined to** cell B black |
| **E−** | Cell A black **joined to** cell B white |
| **A+** | Cell A red |
| **A−** | Cell B red |
| VCC / GND | FireBeetle 3V3 / GND |
| DAT / DT / DOUT | FireBeetle D3 / GPIO14 |
| SCK / CLK | FireBeetle D2 / GPIO8 |

Insulate the two splices separately. With the bridge powered, press each load tip in its installed direction and check that both move the reading the same way. If both move the reading in the wrong direction, swap the two red leads at A+ and A−. [HX711 terminal labels](https://docs.soldered.com/hx711/hardware/) · [FireBeetle pinout](https://wiki.dfrobot.com/dfr1075/#pinout)

## 3. Mount the electronics and close the grip

Fasten the boards to their bosses with USB-C facing the cover opening. Place the battery between the boards and connect it to **BAT** after checking plug polarity. Keep the sensor wires clear of the slot edges, screw paths, and cover seam. [Electronics placement](model/images/electronics-routing.png)

Fit the M3 heat-set inserts and seat both coins in the counterplate pockets. Face the pockets toward the load tips. Fit the cover and counterplate, then use the four M3 corner screws and **M3 nylon nuts**. The CAD uses about 23 mm below each screw head as a fit reference. Check the screw engagement and free movement of the tips on your print.

![Exploded fastener stack with the four nylon nuts below the counterplate](model/images/exploded-assembly.png)

## Firmware

In Arduino IDE, install the **esp32** board package, **HX711** by Rob Tillaart, and **NimBLE-Arduino**. Select **DFRobot FireBeetle 2 ESP32-C6**, enable **USB CDC On Boot**, and select **Minimal SPIFFS** as the partition scheme. Upload [ForceGripper.ino](firmware/ForceGripper/ForceGripper.ino).

The sketch targets an 80 SPS HX711 setup. Soldered lists the stock 333005 at a fixed 10 SPS, so use the recorded USB or UDP timestamps for timing on that board. The BLE reader estimates times within each batch at 80 SPS. [333005 specifications](https://solde.red/333005)

## Read samples

USB serial (115200 baud) and BLE (`HX711_Wake_v1`) are enabled by default. For Wi-Fi, set `WIFI_MODE` in the sketch to `WifiMode::AccessPoint` or `WifiMode::Station`. AP mode serves `/reading` at `192.168.4.1`. In station mode, enter your network details locally and read the board IP from USB serial. Set `WIFI_UDP_TARGET` to your computer’s IPv4 address for the UDP stream on port 5005.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r examples/requirements.txt
.venv/bin/python examples/read_serial.py /dev/cu.usbmodem101
.venv/bin/python examples/read_ble.py
.venv/bin/python examples/read_wifi.py http 192.168.4.1
.venv/bin/python examples/read_wifi.py udp
```

Each reader prints `seq,t_us,raw` CSV. Append `> samples.csv` to save it.

## Regenerate the CAD

```sh
.venv/bin/python -m pip install -r model/requirements.txt
.venv/bin/python model/assembly.py
```

The generator writes the STEP, printable STLs, and [component clearance models](model/components) in millimeters.
