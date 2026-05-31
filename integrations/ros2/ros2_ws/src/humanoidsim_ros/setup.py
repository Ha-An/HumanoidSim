from setuptools import setup

package_name = "humanoidsim_ros"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/models", ["models/minimal_humanoid.urdf"]),
        (f"share/{package_name}/launch", ["launch/validation_world.launch.py"]),
        (f"share/{package_name}/launch", ["launch/rviz_validation.launch.py"]),
        (f"share/{package_name}/launch", ["launch/gazebo_physics_validation.launch.py"]),
        (f"share/{package_name}/config", ["config/validation.rviz"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="HumanoidSim",
    maintainer_email="dev@example.com",
    description="ROS 2 bridge node for standalone HumanoidSim validation.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "humanoidsim_bridge_node = humanoidsim_ros.bridge_node:main",
            "humanoidsim_visualizer_node = humanoidsim_ros.visualizer_node:main",
            "play_trace_file = humanoidsim_ros.play_trace_file:main",
        ],
    },
)
