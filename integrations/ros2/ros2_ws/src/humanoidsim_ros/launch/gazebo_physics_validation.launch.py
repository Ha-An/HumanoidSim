from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gz_args = LaunchConfiguration("gz_args")
    model_path = PathJoinSubstitution([FindPackageShare("humanoidsim_ros"), "models", "minimal_humanoid.urdf"])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])]
        ),
        launch_arguments={"gz_args": gz_args}.items(),
    )

    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        name="humanoidsim_spawn_minimal_humanoid",
        output="screen",
        arguments=[
            "-file",
            model_path,
            "-name",
            "humanoidsim_minimal_humanoid",
            "-x",
            "0.0",
            "-y",
            "0.0",
            "-z",
            "0.6",
            "-allow_renaming",
            "true",
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gz_args",
                default_value="-r empty.sdf",
                description="Gazebo Harmonic arguments for HumanoidSim physics validation.",
            ),
            gazebo,
            spawn,
        ]
    )
