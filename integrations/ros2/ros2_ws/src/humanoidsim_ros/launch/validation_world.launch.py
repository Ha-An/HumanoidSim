from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="humanoidsim_ros",
                executable="humanoidsim_bridge_node",
                name="humanoidsim_bridge_node",
                output="screen",
            )
        ]
    )
