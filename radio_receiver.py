#!/usr/bin/env python3

import argparse
import json
import sys

import serial


def main():
    parser = argparse.ArgumentParser(description="Read radio bridge JSON frames from a serial port.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port connected to the radio receiver")
    parser.add_argument("--baud", type=int, default=576000, help="Serial baud rate")
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
    except Exception as exc:
        print(f"Failed to open {args.port}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Listening on {args.port} at {args.baud} baud")

    try:
        while True:
            line = ser.readline()
            if not line:
                continue

            text = line.decode("utf-8", errors="ignore").strip()
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end < start:
                print(f"Ignoring non-JSON frame: {line!r}", file=sys.stderr)
                continue

            try:
                payload = json.loads(text[start:end + 1])
            except Exception as exc:
                print(f"Invalid frame: {line!r} ({exc})", file=sys.stderr)
                continue

            pos = payload.get("position") or {}
            orient = payload.get("orientation") or {}
            voltage = payload.get("voltage")
            stamp = payload.get("stamp") or {}

            print(
                f"t={stamp.get('sec', 0)}.{stamp.get('nanosec', 0):09d} "
                f"pos=({pos.get('x')}, {pos.get('y')}, {pos.get('z')}) "
                f"quat=({orient.get('x')}, {orient.get('y')}, {orient.get('z')}, {orient.get('w')}) "
                f"voltage={voltage}"
            )
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
