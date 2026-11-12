"""Read the latest force sample over HTTP or listen for the live UDP stream."""

import argparse
import json
import socket
import time
from urllib.request import urlopen


def poll_http(host, interval):
    while True:
        with urlopen(f"http://{host}/reading", timeout=3) as response:
            reading = json.load(response)
        print(f"{reading['seq']},{reading['t_us']},{reading['raw']}", flush=True)
        time.sleep(interval)


def listen_udp(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("", port))
        while True:
            packet, _ = receiver.recvfrom(256)
            try:
                seq, t_us, raw = map(int, packet.decode("ascii").strip().split(","))
            except ValueError:
                continue
            print(f"{seq},{t_us},{raw}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    http = modes.add_parser("http", help="Poll /reading on the gripper")
    http.add_argument("host", help="Gripper IP address")
    http.add_argument("--interval", type=float, default=0.1)
    udp = modes.add_parser("udp", help="Listen for samples sent to this computer")
    udp.add_argument("--port", type=int, default=5005)
    args = parser.parse_args()
    if args.mode == "http" and args.interval <= 0:
        parser.error("--interval must be positive")
    print("seq,t_us,raw", flush=True)
    if args.mode == "http":
        poll_http(args.host, args.interval)
    else:
        listen_udp(args.port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
