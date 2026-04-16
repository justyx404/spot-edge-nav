/*
 * owon_node.cpp
 * ROS 2 Wrapper for Owon Multimeter CLI
 * Features: 
 * - Geo-Location via Odometry
 * - Automatic Reconnection
 * - TF2 Transform to "map" frame
 * - Yaw Angle Calculation
 */

#include <chrono>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>
#include <vector>
#include <sstream>
#include <iostream>
#include <cstring>
#include <mutex>
#include <atomic>
#include <iomanip>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp" // Changed to PoseStamped

// --- TF2 Includes ---
#include "tf2_ros/transform_listener.h"
#include "tf2_ros/buffer.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
#include "tf2/LinearMath/Quaternion.h" // Needed for math
#include "tf2/LinearMath/Matrix3x3.h"  // Needed for Euler conversion

// --- Macros ---
#define MODE_DC_VOLTS     0b00000000
#define MODE_AC_VOLTS     0b00000001
#define MODE_AC_AMPS      0b00000011
#define MODE_DC_AMPS      0b00000010
#define MODE_NCV          0b00001101
#define MODE_OHMS         0b00000100
#define MODE_CAPACITANCE  0b00000101
#define MODE_DIODE        0b00001010
#define MODE_CONTINUITY   0b00001011
#define MODE_FREQUENCY    0b00000110
#define MODE_PERCENT      0b00000111
#define MODE_TEMP_C       0b00001000
#define MODE_TEMP_F       0b00001001
#define MODE_HFE          0b00001100

#define OWON_CM2100B_HANDLE  "0x001b"
#define OWON_CM2100B_LENGTH  18
#define OWON_OW18E_HANDLE    "0x001b"
#define OWON_OW18E_LENGTH    18
#define OWON_B35_B41_HANDLE  "0x002e"
#define OWON_B35_B41_LENGTH  18
#define INF_OPEN   (-32767)

using std::placeholders::_1;

class OwonNode : public rclcpp::Node
{
public:
    OwonNode() : Node("owon_driver_node"), keep_running_(true), has_data_(false)
    {
        // Declare Parameters
        this->declare_parameter("mac_address", "A6:C0:80:91:58:C2");
        this->declare_parameter("model", "cm2100b");
        this->declare_parameter("odom_topic", "/odometry");
        this->declare_parameter("target_frame", "map"); 

        // Get Parameters
        mac_address_ = this->get_parameter("mac_address").as_string();
        std::string model = this->get_parameter("model").as_string();
        std::string odom_topic = this->get_parameter("odom_topic").as_string();
        target_frame_ = this->get_parameter("target_frame").as_string();

        // Configure Handle
        if (model == "b35t" || model == "b41t") {
            owon_handle_ = OWON_B35_B41_HANDLE;
            owon_length_ = OWON_B35_B41_LENGTH;
        } else if (model == "cm2100b") {
            owon_handle_ = OWON_CM2100B_HANDLE;
            owon_length_ = OWON_CM2100B_LENGTH;
        } else if (model == "ow18e") {
            owon_handle_ = OWON_OW18E_HANDLE;
            owon_length_ = OWON_OW18E_LENGTH;
        } else {
            RCLCPP_ERROR(this->get_logger(), "Unknown model: %s. Defaulting to B35T", model.c_str());
            owon_handle_ = OWON_B35_B41_HANDLE;
            owon_length_ = OWON_B35_B41_LENGTH;
        }

        // Initialize TF2 Buffer and Listener
        tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

        // Publishers
        pub_val_ = this->create_publisher<std_msgs::msg::Float32>("owon/value", 10);

        RCLCPP_INFO(this->get_logger(), "Starting Owon Driver for %s at %s", model.c_str(), mac_address_.c_str());
        RCLCPP_INFO(this->get_logger(), "Syncing %s -> Transforming to '%s'", odom_topic.c_str(), target_frame_.c_str());
        
        // Subscriber
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
            odom_topic, 
            10, 
            std::bind(&OwonNode::odom_callback, this, _1)
        );

        // Start reading loop
        reader_thread_ = std::thread(&OwonNode::read_loop, this);
    }

    ~OwonNode()
    {
        keep_running_ = false;
        if (reader_thread_.joinable()) {
            reader_thread_.join();
        }
    }

private:
    std::string mac_address_;
    std::string owon_handle_;
    int owon_length_;
    std::string target_frame_;

    std::thread reader_thread_;
    std::atomic<bool> keep_running_;

    std::mutex data_mutex_;
    bool has_data_;
    float latest_val_float_;
    std::string latest_val_str_;

    // ROS pointers
    rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr pub_val_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    
    // TF2 pointers
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;

    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg)
    {
        // 1. Prepare input Pose (Position + Orientation)
        // PointStamped doesn't have orientation, so we use PoseStamped
        geometry_msgs::msg::PoseStamped pose_in;
        pose_in.header = msg->header;
        pose_in.pose = msg->pose.pose; 

        geometry_msgs::msg::PoseStamped pose_out;

        // 2. Try to transform to Map frame
        try {
            pose_out = tf_buffer_->transform(pose_in, target_frame_);
        } 
        catch (const tf2::TransformException & ex) {
            RCLCPP_DEBUG(this->get_logger(), "Skipping publish: Could not transform to %s: %s", 
                         target_frame_.c_str(), ex.what());
            return; 
        }

        // 3. Calculate Yaw from Quaternion
        tf2::Quaternion q(
            pose_out.pose.orientation.x,
            pose_out.pose.orientation.y,
            pose_out.pose.orientation.z,
            pose_out.pose.orientation.w);
        
        tf2::Matrix3x3 m(q);
        double roll, pitch, yaw;
        m.getRPY(roll, pitch, yaw); // Yaw is in radians

        (void)yaw;
        (void)pose_out;
    }

    void read_loop()
    {
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "gatttool -b %s --char-read --handle %s --listen 2>/dev/null",
                 mac_address_.c_str(), owon_handle_.c_str());

        char buffer[1024];
        char target_str[64];
        snprintf(target_str, sizeof(target_str), "%s value: ", owon_handle_.c_str());

        while (keep_running_) {
            
            RCLCPP_INFO_ONCE(this->get_logger(), "Attempting to connect to Multimeter...");

            FILE *fp = popen(cmd, "r");
            if (fp == NULL) {
                RCLCPP_ERROR(this->get_logger(), "Failed to run gatttool. Retrying...");
                std::this_thread::sleep_for(std::chrono::seconds(3));
                continue;
            }

            bool connected_at_least_once = false;

            while (keep_running_ && fgets(buffer, sizeof(buffer), fp) != NULL) {
                
                if (!connected_at_least_once) {
                    RCLCPP_INFO(this->get_logger(), "Multimeter Connected!");
                    connected_at_least_once = true;
                }

                char *p = strstr(buffer, target_str);
                if (!p) continue;
                
                p += strlen(target_str);
                size_t len = strlen(p);
                if (len > 0 && p[len-1] == '\n') p[len-1] = '\0';

                uint8_t d[14];
                int i = 0;
                char *ptr = p;
                char *endptr;
                
                while (*ptr != '\0' && i < 6) {
                    d[i] = (uint8_t)strtol(ptr, &endptr, 16);
                    if (ptr == endptr) break; 
                    ptr = endptr;
                    i++;
                }

                uint16_t reading[3];
                reading[0] = d[1] << 8 | d[0];
                reading[1] = d[3] << 8 | d[2];
                reading[2] = d[5] << 8 | d[4];

                unsigned int function = (reading[0] >> 6) & 0x0f;
                unsigned int scale = (reading[0] >> 3) & 0x07;
                unsigned int decimal = reading[0] & 0x07;
                int measurement;

                if (reading[2] < 0x7fff) {
                    measurement = reading[2];
                } else {
                    measurement = -1 * (reading[2] & 0x7fff);
                }

                update_measurement_storage(function, scale, decimal, measurement);
            }

            pclose(fp);
            
            if (keep_running_) {
                RCLCPP_WARN(this->get_logger(), "Connection lost. Retrying in 3s...");
                std::this_thread::sleep_for(std::chrono::seconds(3));
            }
        }
    }

    void update_measurement_storage(int function, int scale, int decimal, int measurement)
    {
        char tmp_val_buf[16];
        char fixed_val_buf[32];
        sprintf(tmp_val_buf, "%04d", measurement);

        int tv = 0;
        int fv = 0;
        int len = strlen(tmp_val_buf);
        
        memset(fixed_val_buf, 0, 32);

        for (tv = 0; tv < len; tv++) {
            if (tv == (len - decimal)) {
                fixed_val_buf[fv++] = '.';
            }
            fixed_val_buf[fv++] = tmp_val_buf[tv];
        }

        std::string unit = get_unit_string(function, scale, measurement);
        
        std::lock_guard<std::mutex> lock(data_mutex_);
        
        try {
            latest_val_float_ = std::stof(fixed_val_buf);
        } catch (...) {
            latest_val_float_ = 0.0; 
        }
        
        latest_val_str_ = std::string(fixed_val_buf) + " " + unit;
        has_data_ = true;

        auto msg_float = std_msgs::msg::Float32();
        msg_float.data = latest_val_float_;
        pub_val_->publish(msg_float);
    }

    std::string get_unit_string(int function, int scale, int measurement) {
        if (function == MODE_DC_VOLTS) return (scale == 3) ? "mV DC" : "V DC";
        if (function == MODE_AC_VOLTS) return (scale == 3) ? "mV AC" : "V AC";
        if (function == MODE_DC_AMPS) return (scale == 2) ? "uA DC" : (scale == 3 ? "mA DC" : "A DC");
        if (function == MODE_AC_AMPS) return (scale == 2) ? "uA AC" : (scale == 3 ? "mA AC" : "A AC");
        if (function == MODE_OHMS) return (measurement == INF_OPEN) ? "Open" : (scale == 5 ? "kOhm" : (scale == 6 ? "MOhm" : "Ohm"));
        if (function == MODE_CONTINUITY) return (measurement == INF_OPEN) ? "Open" : "Closed";
        if (function == MODE_CAPACITANCE) return (scale == 1) ? "nF" : "uF";
        if (function == MODE_FREQUENCY) return "Hz";
        if (function == MODE_TEMP_C) return "C";
        return "";
    }
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<OwonNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
