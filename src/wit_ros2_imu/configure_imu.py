import serial
import time

# Configure your serial port settings
port = "/dev/ttyUSB0"  # Change to /dev/ttyUSB0 on Linux
baud = 9600    # Default baud rate before change (check your manual)

try:
    ser = serial.Serial(port, baud, timeout=1)
    
    def send_cmd(cmd_list):
        cmd_bytes = bytes(cmd_list)
        ser.write(cmd_bytes)
        time.sleep(0.1) # Small delay for processing

    print("Step 1: Unlocking registers...")
    # KEY Register (0x69), Unlock Code: 0xB588
    # Format: FF AA ADDR DATAL DATAH
    send_cmd([0xFF, 0xAA, 0x69, 0x88, 0xB5])

    print("Step 2: Setting Output Rate to 100Hz...")
    # RRATE Register (0x03), 100Hz Value: 0x09
    send_cmd([0xFF, 0xAA, 0x03, 0x09, 0x00])

    print("Step 3: Setting Baud Rate to 115200...")
    # BAUD Register (0x04), 115200 Value: 0x06
    send_cmd([0xFF, 0xAA, 0x04, 0x06, 0x00])

    print("Step 4: Saving configuration...")
    # SAVE Register (0x00), Save Code: 0x0000
    send_cmd([0xFF, 0xAA, 0x00, 0x00, 0x00])

    print("Configuration complete. Please restart the device and update your Python script baud rate.")
    ser.close()

except Exception as e:
    print(f"Error: {e}")
