#!/bin/bash
# Zenoh ROS 2 Router Startup Script
# Usage:
#   ./zenoh_host.sh          — default config (local/offline testing, no downsampling)
#   ./zenoh_host.sh remote   — remote config (downsampled for low-latency RVIZ over WiFi)

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$1" == "remote" ]]; then
  # Remote config: downsampling rules for low-latency RVIZ over WiFi
  export ZENOH_ROUTER_CONFIG_URI="${SCRIPT_DIR}/zenoh_router_config.json5"
  echo "Mode: REMOTE (downsampling enabled)"
  echo "Config: ${ZENOH_ROUTER_CONFIG_URI}"
else
  # Default config: no downsampling, full rate on all topics
  unset ZENOH_ROUTER_CONFIG_URI
  echo "Mode: DEFAULT (no downsampling, full rate)"
fi

# Execute the Zenoh router. This process will run in the foreground and display output.
ros2 run rmw_zenoh_cpp rmw_zenohd

# Note: Press Ctrl+C to stop the Zenoh router and exit the script.
