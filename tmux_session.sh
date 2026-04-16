#!/bin/bash
# Tmux session for Spot robot ROS 2 workspace
# Usage: ./tmux_session.sh
#
# All panes have RMW_IMPLEMENTATION=rmw_zenoh_cpp and the workspace sourced.
# Start the zenoh router manually in the zenoh window:
#   ./zenoh_host.sh          — default config (no downsampling)
#   ./zenoh_host.sh remote   — remote config (downsampled for RVIZ over WiFi)

SESSION="spot"
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill existing session if it exists
tmux kill-session -t "$SESSION" 2>/dev/null

# Common setup commands for every pane
SETUP="cd \"$WORKSPACE_DIR\" && export RMW_IMPLEMENTATION=rmw_zenoh_cpp && source /opt/ros/humble/setup.bash && source install/setup.bash 2>/dev/null"

# ============================================================
# Window 0: Hardware
#   Pane 0: Robot driver
#   Pane 1: Sensor drivers
#   Pane 2: Spare
# ============================================================
tmux new-session -d -s "$SESSION" -n "hardware" -x 200 -y 50
tmux send-keys -t "$SESSION:hardware" "$SETUP" Enter

tmux split-window -t "$SESSION:hardware" -v
tmux send-keys -t "$SESSION:hardware.1" "$SETUP" Enter
tmux send-keys -t "$SESSION:hardware.1" "ros2 launch spot_navigation sensors.launch.py radio_baud:=57600"

tmux split-window -t "$SESSION:hardware.1" -h
tmux send-keys -t "$SESSION:hardware.2" "$SETUP" Enter

# ============================================================
# Window 1: Software
#   Pane 0: Odometry / localization
#   Pane 1: Path planning
#   Pane 2: Spare (scripts, topic echo, etc.)
# ============================================================
tmux new-window -t "$SESSION" -n "software"
tmux send-keys -t "$SESSION:software" "$SETUP" Enter
tmux send-keys -t "$SESSION:software.0" "ros2 launch spot_navigation lio_localization.launch.py"

tmux split-window -t "$SESSION:software" -v
tmux send-keys -t "$SESSION:software.1" "$SETUP" Enter
tmux send-keys -t "$SESSION:software.1" "ros2 launch spot_navigation far_planner.launch.py"

tmux split-window -t "$SESSION:software.1" -h
tmux send-keys -t "$SESSION:software.2" "$SETUP" Enter

# ============================================================
# Window 2: Topics
#   Pane 0: Zenoh router
#   Pane 1: ROS 2 topic tools
#   Pane 2: Spare
# ============================================================
tmux new-window -t "$SESSION" -n "topics"
tmux send-keys -t "$SESSION:topics" "$SETUP" Enter
tmux send-keys -t "$SESSION:topics.0" "./zenoh_host.sh"

tmux split-window -t "$SESSION:topics" -v
tmux send-keys -t "$SESSION:topics.1" "$SETUP" Enter

tmux split-window -t "$SESSION:topics.1" -h
tmux send-keys -t "$SESSION:topics.2" "$SETUP" Enter

# Focus on the hardware window
tmux select-window -t "$SESSION:hardware"
tmux select-pane -t "$SESSION:hardware.0"

# Attach
tmux attach-session -t "$SESSION"
