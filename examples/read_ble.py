"""Stream raw force samples from BLE notifications."""

import argparse
import asyncio
import struct

from bleak import BleakClient, BleakScanner

DATA_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
SAMPLE_INTERVAL_US = 12_500
UINT32_MASK = 0xFFFFFFFF


def decode_batch(packet):
    if len(packet) < 10 or packet[0] != 0xA6:
        return
    count = packet[1]
    if not 1 <= count <= 3 or len(packet) != 10 + count * 3:
        return
    seq, t_us = struct.unpack_from("<II", packet, 2)
    for index in range(count):
        start = 10 + index * 3
        raw = int.from_bytes(packet[start:start + 3], "little", signed=True)
        yield (seq + index) & UINT32_MASK, (t_us + index * SAMPLE_INTERVAL_US) & UINT32_MASK, raw


async def stream(name):
    device = await BleakScanner.find_device_by_name(name, timeout=15)
    if device is None:
        raise SystemExit(f"BLE device not found: {name}")

    disconnected = asyncio.Event()

    def print_batch(_characteristic, packet):
        for seq, t_us, raw in decode_batch(packet):
            print(f"{seq},{t_us},{raw}", flush=True)

    async with BleakClient(device, disconnected_callback=lambda _: disconnected.set()) as client:
        print("seq,t_us,raw", flush=True)
        await client.start_notify(DATA_UUID, print_batch)
        await disconnected.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="HX711_Wake_v1")
    asyncio.run(stream(parser.parse_args().name))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
