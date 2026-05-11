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

# Common mission commands. The software panes seed both prior-map and no-prior
# SLAM commands into shell history, then prefill the prior-map workflow.
LIO_PRIOR_CMD="ros2 launch spot_navigation lio_localization.launch.py map_path:=$WORKSPACE_DIR/src/spot_navigation/map/microgrid_transformed.pcd"
LIO_OFFICE_PRIOR_CMD="ros2 launch spot_navigation lio_localization.launch.py map_path:=$WORKSPACE_DIR/src/spot_navigation/map/office_2026_05_07_113224.pcd"
LIO_SLAM_CMD="ros2 launch spot_navigation lio_slam.launch.py"
FAR_PRIOR_CMD="ros2 launch spot_navigation far_planner.launch.py use_sim_time:=false load_prior_map:=true prior_map_path:=$WORKSPACE_DIR/src/spot_navigation/map/microgrid_transformed.vgh"
FAR_OFFICE_PRIOR_CMD="ros2 launch spot_navigation far_planner.launch.py use_sim_time:=false load_prior_map:=true prior_map_path:=$WORKSPACE_DIR/src/spot_navigation/map/office_2026_05_07_113224.vgh"
FAR_SLAM_CMD="ros2 launch spot_navigation far_planner.launch.py use_sim_time:=false load_prior_map:=false"

add_history() {
    local pane="$1"
    local command="$2"
    tmux send-keys -t "$pane" "history -s $(printf '%q' "$command")" Enter
}

# ============================================================
# Window 0: Hardware
#   Pane 0: Robot driver command prefilled
#   Pane 1: Sensor drivers
#   Pane 2: Spare
# ============================================================
tmux new-session -d -s "$SESSION" -n "hardware" -x 200 -y 50
tmux send-keys -t "$SESSION:hardware" "$SETUP" Enter
tmux send-keys -t "$SESSION:hardware.0" 'ros2 launch spot_driver spot_driver.launch.py password:=${BOSDYN_CLIENT_PASSWORD:?set BOSDYN_CLIENT_PASSWORD} cmd_vel_command_duration:=1.0'

tmux split-window -t "$SESSION:hardware" -v
tmux send-keys -t "$SESSION:hardware.1" "$SETUP" Enter
tmux send-keys -t "$SESSION:hardware.1" "ros2 launch spot_navigation sensors.launch.py radio_baud:=57600"

tmux split-window -t "$SESSION:hardware.1" -h
tmux send-keys -t "$SESSION:hardware.2" "$SETUP" Enter

# ============================================================
# Window 1: Software
#   Pane 0: Odometry / localization
#   Pane 1: Path planning
#   Pane 2: Route manager command prefilled
# ============================================================
tmux new-window -t "$SESSION" -n "software"
tmux send-keys -t "$SESSION:software" "$SETUP" Enter
add_history "$SESSION:software.0" "$LIO_PRIOR_CMD"
add_history "$SESSION:software.0" "$LIO_OFFICE_PRIOR_CMD"
add_history "$SESSION:software.0" "$LIO_SLAM_CMD"
tmux send-keys -t "$SESSION:software.0" "$LIO_PRIOR_CMD"

tmux split-window -t "$SESSION:software" -v
tmux send-keys -t "$SESSION:software.1" "$SETUP" Enter
add_history "$SESSION:software.1" "$FAR_PRIOR_CMD"
add_history "$SESSION:software.1" "$FAR_OFFICE_PRIOR_CMD"
add_history "$SESSION:software.1" "$FAR_SLAM_CMD"
tmux send-keys -t "$SESSION:software.1" "$FAR_PRIOR_CMD"

tmux split-window -t "$SESSION:software.1" -h
tmux send-keys -t "$SESSION:software.2" "$SETUP" Enter
tmux send-keys -t "$SESSION:software.2" "ros2 run spot_navigation route_manager --ros-args -p route_name:=midpoint"

# ============================================================
# Window 2: Topics
#   Pane 0: Zenoh router
#   Pane 1: Bag recorder command prefilled
#   Pane 2: Spare
# ============================================================
tmux new-window -t "$SESSION" -n "topics"
tmux send-keys -t "$SESSION:topics" "$SETUP" Enter
tmux send-keys -t "$SESSION:topics.0" "./zenoh_host.sh"

tmux split-window -t "$SESSION:topics" -v
tmux send-keys -t "$SESSION:topics.1" "$SETUP" Enter
tmux send-keys -t "$SESSION:topics.1" "ros2 bag record -a --max-bag-size 1073741824"

tmux split-window -t "$SESSION:topics.1" -h
tmux send-keys -t "$SESSION:topics.2" "$SETUP" Enter

# Focus on the hardware window
tmux select-window -t "$SESSION:hardware"
tmux select-pane -t "$SESSION:hardware.0"

# Attach
tmux attach-session -t "$SESSION"
