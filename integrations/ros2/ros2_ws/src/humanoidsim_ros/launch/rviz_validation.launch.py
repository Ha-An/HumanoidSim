from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory("humanoidsim_ros"))
    model_path = share / "models" / "minimal_humanoid.urdf"
    rviz_config = share / "config" / "validation.rviz"
    robot_description = model_path.read_text(encoding="utf-8")
    return LaunchDescription(
        [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="humanoidsim_robot_state_publisher",
                output="screen",
                parameters=[{"robot_description": robot_description}],
            ),
            Node(
                package="humanoidsim_ros",
                executable="humanoidsim_visualizer_node",
                name="humanoidsim_visualizer",
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="humanoidsim_rviz",
                arguments=["-d", str(rviz_config)],
                output="screen",
            ),
        ]
    )
