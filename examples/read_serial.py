"""Stream raw force samples from the gripper over USB serial."""

import argparse

import serial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="USB serial device, e.g. /dev/cu.usbmodem101 or COM3")
    args = parser.parse_args()
    print("seq,t_us,raw", flush=True)
    with serial.Serial(args.port, 115200, timeout=1) as connection:
        while True:
            fields = connection.readline().decode("ascii", errors="replace").strip().split(",")
            if len(fields) != 3:
                continue
            try:
                seq, t_us, raw = map(int, fields)
            except ValueError:
                continue
            print(f"{seq},{t_us},{raw}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
