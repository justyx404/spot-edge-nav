#!/bin/bash
# Zenoh ROS 2 Router Startup Script
if ! command -v ros2 &>/dev/null; then
  echo "ERROR: ROS 2 command not found."
  echo "Please ensure you have sourced your ROS 2 environment (e.g., source ~/spot_ws/install/setup.bash) before running this script."
  exit 1
fi

echo "--- (1/2) Cleaning up existing ROS processes and daemon ---"

# Use pkill to forcibly terminate all processes related to ROS, matching the user's original command.
# We redirect standard error (2) to /dev/null to hide "No process found" warnings.
pkill -9 -f ros 2>/dev/null
echo "Existing ROS-related processes terminated (if running)."

# Stop the ROS 2 daemon.
ros2 daemon stop 2>/dev/null
echo "ROS 2 daemon stopped (if running)."

echo "--- (2/2) Starting Zenoh Router (rmw_zenohd) ---"

# Point the router to our custom config with downsampling rules for remote RVIZ.
# This reduces bandwidth over WiFi by throttling heavy topics (pointclouds, cameras, debug).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ZENOH_ROUTER_CONFIG_URI="${SCRIPT_DIR}/zenoh_router_config.json5"
echo "Using Zenoh router config: ${ZENOH_ROUTER_CONFIG_URI}"

# Execute the Zenoh router. This process will run in the foreground and display output.
ros2 run rmw_zenoh_cpp rmw_zenohd

# Note: Press Ctrl+C to stop the Zenoh router and exit the script. And open a new terminal:
# export RMW_IMPLEMENTATION=rmw_zenoh_cpp
