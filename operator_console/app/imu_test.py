from __future__ import annotations

import argparse
import time
from collections import Counter

import serial


PACKET_NAMES = {
    0x51: "acceleration",
    0x52: "angular_velocity",
    0x53: "euler_angles",
    0x59: "quaternion",
}


def checksum_ok(packet: bytes) -> bool:
    return len(packet) == 11 and (sum(packet[:10]) & 0xFF) == packet[10]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WIT IMU serial output for the ROS driver.")
    parser.add_argument("--port", default="/dev/imu_usb")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--min-valid-packets", type=int, default=20)
    args = parser.parse_args()

    print(f"Opening IMU serial port {args.port} at {args.baud} baud")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
    except Exception as exc:
        print(f"FAIL: could not open IMU serial port: {exc}")
        return 1

    packet_counts: Counter[int] = Counter()
    invalid_packets = 0
    read_buf = bytearray()
    deadline = time.monotonic() + args.duration

    with ser:
        while time.monotonic() < deadline:
            waiting = ser.in_waiting
            chunk = ser.read(waiting if waiting > 0 else 1)
            if chunk:
                read_buf.extend(chunk)

            while len(read_buf) >= 11:
                if read_buf[0] != 0x55:
                    del read_buf[0]
                    continue

                packet = bytes(read_buf[:11])
                if checksum_ok(packet):
                    packet_counts[packet[1]] += 1
                    del read_buf[:11]
                else:
                    invalid_packets += 1
                    del read_buf[0]

    valid_packets = sum(packet_counts.values())
    rate_hz = valid_packets / args.duration if args.duration > 0 else 0.0
    known_counts = {PACKET_NAMES.get(packet_type, hex(packet_type)): count for packet_type, count in packet_counts.items()}

    print(f"Valid WIT packets: {valid_packets}")
    print(f"Approx packet rate: {rate_hz:.1f} packets/s")
    print(f"Invalid checksum/frame attempts: {invalid_packets}")
    print(f"Packet types: {known_counts}")

    required_types = {0x51, 0x52}
    if valid_packets < args.min_valid_packets:
        print(f"FAIL: expected at least {args.min_valid_packets} valid packets")
        return 1
    if not required_types.issubset(packet_counts):
        missing = [PACKET_NAMES[item] for item in sorted(required_types - set(packet_counts))]
        print(f"FAIL: missing required packet types for ROS IMU driver: {missing}")
        return 1

    print("PASS: IMU is streaming valid packets at the ROS driver baud rate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
