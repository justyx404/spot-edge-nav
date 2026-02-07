# Quadruped Workspace

ROS 2 Humble workspace for Spot robot navigation, localization, and planning.

## Setup

```bash
# Clone with all submodules
git clone --recursive <repo-url>

# Build the Docker container
docker compose up -d

# Inside the container
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

## Remote RVIZ (Zenoh)

```bash
# Robot PC: start the Zenoh router with downsampling config
./zenoh_host.sh

# Client PC: connect to the robot's router
source zenoh_client.sh
```

## TODO

- [ ] Add `elevation_mapping_cupy` as a tracked submodule
- [ ] Add `ocs2` and `ocs2_robotic_assets` as tracked submodules
- [ ] Add `legged_control` as a tracked submodule
- [ ] Add `spot_gazebo_ros2` as a tracked submodule
- [ ] Replace the swing leg controller in `spot_gazebo_ros2` with `legged_control` MPC controller
- [ ] Integrate `elevation_mapping_cupy` with the navigation stack
