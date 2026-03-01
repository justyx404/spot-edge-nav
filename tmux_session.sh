#!/bin/bash
# Tmux session for Spot robot ROS 2 workspace
# Usage: ./tmux_session.sh
#
# All panes have RMW_IMPLEMENTATION=rmw_zenoh_cpp and the workspace sourced.
# Start the zenoh router manually in the zenoh window:
#   ./zenoh_host.sh          — default config (no downsampling)
#   ./zenoh_host.sh remote   — remote config (downsampled for RVIZ over WiFi)

SESSION="spot"

# Kill existing session if it exists
tmux kill-session -t "$SESSION" 2>/dev/null

# Common setup commands for every pane
SETUP="export RMW_IMPLEMENTATION=rmw_zenoh_cpp && source /opt/ros/humble/setup.bash && source install/setup.bash 2>/dev/null"

# ============================================================
# Window 0: Zenoh + Bags
#   Pane 0: Zenoh router
#   Pane 1: Spare (bag record/play)
#   Pane 2: Spare
# ============================================================
tmux new-session -d -s "$SESSION" -n "zenoh" -x 200 -y 50
tmux send-keys -t "$SESSION:zenoh" "$SETUP" Enter

tmux split-window -t "$SESSION:zenoh" -v
tmux send-keys -t "$SESSION:zenoh.1" "$SETUP" Enter

tmux split-window -t "$SESSION:zenoh.1" -h
tmux send-keys -t "$SESSION:zenoh.2" "$SETUP" Enter

# ============================================================
# Window 1: Navigation (localization + planner)
#   Pane 0: Localization launch
#   Pane 1: Planner launch
#   Pane 2: Spare (scripts, topic echo, etc.)
# ============================================================
tmux new-window -t "$SESSION" -n "nav"
tmux send-keys -t "$SESSION:nav" "$SETUP" Enter

tmux split-window -t "$SESSION:nav" -v
tmux send-keys -t "$SESSION:nav.1" "$SETUP" Enter

tmux split-window -t "$SESSION:nav.1" -h
tmux send-keys -t "$SESSION:nav.2" "$SETUP" Enter

# ============================================================
# Window 2: Hardware (robot drivers, sensors)
#   Pane 0: Robot driver
#   Pane 1: Sensor drivers
#   Pane 2: Spare
# ============================================================
tmux new-window -t "$SESSION" -n "hw"
tmux send-keys -t "$SESSION:hw" "$SETUP" Enter

tmux split-window -t "$SESSION:hw" -v
tmux send-keys -t "$SESSION:hw.1" "$SETUP" Enter

tmux split-window -t "$SESSION:hw.1" -h
tmux send-keys -t "$SESSION:hw.2" "$SETUP" Enter

# Focus on the nav window
tmux select-window -t "$SESSION:zenoh"
tmux select-pane -t "$SESSION:zenoh.0"

# Attach
tmux attach-session -t "$SESSION"
