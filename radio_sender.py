#!/usr/bin/env python3

import argparse
import json
import time

import serial


def main():
    parser = argparse.ArgumentParser(description="Send sample JSON frames over a serial radio link.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port connected to the radio transmitter")
    parser.add_argument("--baud", type=int, default=57600, help="Serial baud rate")
    parser.add_argument("--rate", type=float, default=2.0, help="Send rate in Hz")
    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=1.0)
    print(f"Sending test frames on {args.port} at {args.baud} baud")

    counter = 0
    period = 1.0 / max(args.rate, 0.1)

    try:
        while True:
            now = time.time()
            sec = int(now)
            nanosec = int((now - sec) * 1e9)
            frame = {
                "stamp": {"sec": sec, "nanosec": nanosec},
                "frame_id": "map",
                "child_frame_id": "base_link",
                "position": {
                    "x": float(counter),
                    "y": float(counter) * 0.1,
                    "z": 0.0,
                },
                "orientation": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0,
                    "w": 1.0,
                },
                "voltage": 12.0 + 0.01 * counter,
            }
            payload = json.dumps(frame, separators=(",", ":")) + "\n"
            ser.write(payload.encode("utf-8"))
            ser.flush()
            print(payload.strip())
            counter += 1
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
