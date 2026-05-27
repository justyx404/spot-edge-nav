from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROS_SETUP = "/opt/ros/humble/setup.bash"
WORKSPACE_SETUP = "install/setup.bash"
RMW_IMPLEMENTATION = "rmw_zenoh_cpp"


@dataclass(frozen=True)
class ManagedCommand:
    name: str
    command: str
    description: str


def shell_setup() -> str:
    return (
        f'cd "{REPO_ROOT}" && '
        f"export RMW_IMPLEMENTATION={RMW_IMPLEMENTATION} && "
        f"source {ROS_SETUP} && "
        f"if [ -f {WORKSPACE_SETUP} ]; then source {WORKSPACE_SETUP}; fi"
    )


def with_ros_setup(command: str) -> str:
    return f"{shell_setup()} && exec {command}"


def without_ros_setup(command: str) -> str:
    return f'cd "{REPO_ROOT}" && exec {command}'


MAP_DIR = REPO_ROOT / "src" / "spot_navigation" / "map"

LIO_COMMANDS = {
    "microgrid": (
        "ros2 launch spot_navigation lio_localization.launch.py "
        f"map_path:={MAP_DIR / 'microgrid_transformed.pcd'}"
    ),
    "office": (
        "ros2 launch spot_navigation lio_localization.launch.py "
        f"map_path:={MAP_DIR / 'office_2026_05_07_113224.pcd'}"
    ),
    "slam": "ros2 launch spot_navigation lio_slam.launch.py",
}

PLANNER_COMMANDS = {
    "microgrid": (
        "ros2 launch spot_navigation far_planner.launch.py "
        "use_sim_time:=false load_prior_map:=true "
        f"prior_map_path:={MAP_DIR / 'microgrid_transformed.vgh'}"
    ),
    "office": (
        "ros2 launch spot_navigation far_planner.launch.py "
        "use_sim_time:=false load_prior_map:=true "
        f"prior_map_path:={MAP_DIR / 'office_2026_05_07_113224.vgh'}"
    ),
    "slam": (
        "ros2 launch spot_navigation far_planner.launch.py "
        "use_sim_time:=false load_prior_map:=false"
    ),
}

ZENOH_COMMAND = "ros2 run rmw_zenoh_cpp rmw_zenohd"

MANAGED_COMMANDS = {
    "zenoh": ManagedCommand(
        name="zenoh",
        command=ZENOH_COMMAND,
        description="Zenoh router for ROS 2 middleware transport.",
    ),
    "sensors": ManagedCommand(
        name="sensors",
        command="ros2 launch spot_navigation sensors.launch.py radio_baud:=57600",
        description="Sensor drivers, IMU, radio bridge, and related hardware inputs.",
    ),
    "localization": ManagedCommand(
        name="localization",
        command=LIO_COMMANDS["microgrid"],
        description="LIO localization or SLAM.",
    ),
    "planner": ManagedCommand(
        name="planner",
        command=PLANNER_COMMANDS["microgrid"],
        description="FAR planner with prior-map or SLAM mode.",
    ),
    "route_manager": ManagedCommand(
        name="route_manager",
        command="ros2 run spot_navigation route_manager --ros-args -p route_name:=midpoint",
        description="Route manager for target route execution.",
    ),
}


def command_for(name: str, profile: str | None = None, mode: str | None = None) -> str:
    if name == "zenoh":
        return ZENOH_COMMAND
    if name == "localization":
        return LIO_COMMANDS[profile or "microgrid"]
    if name == "planner":
        return PLANNER_COMMANDS[profile or "microgrid"]
    return MANAGED_COMMANDS[name].command
