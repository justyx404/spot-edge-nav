#!/bin/bash
# Zenoh ROS 2 Client Startup Script (e.g. 192.168.1.150:7447).
# USAGE: source zenoh_client.sh  (do NOT run as ./zenoh_client.sh)

pkill -9 -f ros 2>/dev/null
ros2 daemon stop 2>/dev/null

# Set environment variables BEFORE starting the daemon
export RMW_IMPLEMENTATION="rmw_zenoh_cpp"
export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/192.168.80.100:7447"]'

ros2 daemon start
