import time
import math
import serial
import struct
import numpy as np
import threading
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

class IMUDriverNode(Node):
    def __init__(self):
        super().__init__('imu_driver_node')

        # Parameters
        self.declare_parameter('port', '/dev/imu_usb')
        self.declare_parameter('baud', 115200)
        
        self.port_name = self.get_parameter('port').get_parameter_value().string_value
        self.baud_rate = self.get_parameter('baud').get_parameter_value().integer_value

        # Internal State
        self.acceleration = [0.0, 0.0, 0.0]
        self.angular_velocity = [0.0, 0.0, 0.0]
        self.angle_degree = [0.0, 0.0, 0.0]
        self.quaternion = [0.0, 0.0, 0.0, 1.0] # [x, y, z, w]
        
        # ROS 2 Publisher
        self.imu_pub = self.create_publisher(Imu, 'imu/data_raw', 10)
        self.imu_msg = Imu()
        self.imu_msg.header.frame_id = 'imu_link'

        # Serial Connection Reference
        self.serial_port = None
        self.running = True

        # Start Driver Thread
        self.driver_thread = threading.Thread(target=self.driver_loop)
        self.driver_thread.daemon = True
        self.driver_thread.start()
        
        self.get_logger().info(f"IMU Node started on {self.port_name} at {self.baud_rate} baud.")

    def check_sum(self, data):
        return sum(data[:10]) & 0xFF == data[10]

    def hex_to_short(self, data_bytes):
        return struct.unpack("<hhhh", data_bytes)

    def handle_packet(self, packet_type, data_bytes):
        shorts = self.hex_to_short(data_bytes)

        if packet_type == 0x51:  # Acceleration
            self.acceleration = [s / 32768.0 * 16.0 * 9.80665 for s in shorts[:3]]
            
        elif packet_type == 0x52:  # Angular Velocity
            self.angular_velocity = [s / 32768.0 * 2000.0 * (math.pi / 180.0) for s in shorts[:3]]
            
        elif packet_type == 0x53:  # Euler Angles
            self.get_logger().debug("Using Euler Angle Conversion (0x53)")
            self.angle_degree = [s / 32768.0 * 180.0 for s in shorts[:3]]
            roll, pitch, yaw = map(math.radians, self.angle_degree)
            self.quaternion = self.get_quaternion_from_euler(roll, pitch, yaw)
            self.publish_imu()

        elif packet_type == 0x59: # Native Quaternion
            self.get_logger().debug("Using Native Hardware Quaternion (0x59)")
            q_raw = [s / 32768.0 for s in shorts]
            self.quaternion = [q_raw[1], q_raw[2], q_raw[3], q_raw[0]]
            self.publish_imu()

    def publish_imu(self):
        now = self.get_clock().now().to_msg()
        self.imu_msg.header.stamp = now
        
        self.imu_msg.linear_acceleration.x = self.acceleration[0]
        self.imu_msg.linear_acceleration.y = self.acceleration[1]
        self.imu_msg.linear_acceleration.z = self.acceleration[2]
        
        self.imu_msg.angular_velocity.x = self.angular_velocity[0]
        self.imu_msg.angular_velocity.y = self.angular_velocity[1]
        self.imu_msg.angular_velocity.z = self.angular_velocity[2]
        
        self.imu_msg.orientation.x = self.quaternion[0]
        self.imu_msg.orientation.y = self.quaternion[1]
        self.imu_msg.orientation.z = self.quaternion[2]
        self.imu_msg.orientation.w = self.quaternion[3]
        
        self.imu_pub.publish(self.imu_msg)

    def get_quaternion_from_euler(self, roll, pitch, yaw):
        qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
        qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
        qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        return [qx, qy, qz, qw]

    def driver_loop(self):
        try:
            self.serial_port = serial.Serial(port=self.port_name, baudrate=self.baud_rate, timeout=0.1)
            if not self.serial_port.is_open:
                self.serial_port.open()
            self.get_logger().info(f"Connected to IMU at {self.baud_rate}")
        except Exception as e:
            self.get_logger().error(f"Failed to open serial port: {e}")
            return

        read_buf = bytearray()
        while rclpy.ok() and self.running:
            try:
                if self.serial_port.in_waiting > 0:
                    read_buf.extend(self.serial_port.read(self.serial_port.in_waiting))
                    while len(read_buf) >= 11:
                        if read_buf[0] == 0x55:
                            packet = read_buf[:11]
                            if self.check_sum(packet):
                                self.handle_packet(packet[1], packet[2:10])
                                del read_buf[:11]
                            else:
                                del read_buf[0]
                        else:
                            del read_buf[0]
                else:
                    time.sleep(0.001)
            except Exception as e:
                if self.running:
                    self.get_logger().error(f"Error in driver loop: {e}")
                break
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def destroy_node(self):
        self.running = False
        if self.driver_thread.is_alive():
            self.driver_thread.join(timeout=1.0)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = IMUDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Check if context is already shut down to avoid RCLError
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()