# Spot Edge Operator Console

Small FastAPI control surface for the Spot navigation stack.

## Run

```bash
cd /home/spotbot/Workspace/spot-edge-nav
source /home/spotbot/ros_app/bin/activate
uvicorn operator_console.app.main:app --host 0.0.0.0 --port 8080
```

Open the tablet browser to:

```text
http://<nuc-ip>:8080
```

FastAPI's generated API page is also available at:

```text
http://<nuc-ip>:8080/docs
```

## Current Capabilities

- Report managed process status.
- Configure the IMU with `src/wit_ros2_imu/configure_imu.py`.
- Test that the IMU is streaming valid WIT packets on `/dev/imu_usb` at
  `115200`, which is what `spot_navigation sensors.launch.py` passes to the
  ROS IMU node.
- Start and stop the Zenoh router directly with `ros2 run rmw_zenoh_cpp rmw_zenohd`.
- Start and stop sensors.
- Start and stop localization, planner, and route manager as a navigation group.
- Stream managed process logs to the browser over WebSocket.

## Notes

The console is intentionally a thin supervisor over the existing launch commands.
ROS command definitions live in `app/stack_config.py`; long-running processes are
owned by `app/process_manager.py`.
