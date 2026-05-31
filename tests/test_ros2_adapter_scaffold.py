from __future__ import annotations

import ast
import unittest
from pathlib import Path


class Ros2AdapterScaffoldTests(unittest.TestCase):
    def test_ros2_workspace_scaffold_exists(self) -> None:
        root = Path(__file__).resolve().parents[1] / "integrations" / "ros2"
        expected = [
            root / "README.md",
            root / "scripts" / "install_ros2_jazzy_gazebo_harmonic.sh",
            root / "ros2_ws" / "src" / "humanoidsim_ros_interfaces" / "action" / "ExecuteTask.action",
            root / "ros2_ws" / "src" / "humanoidsim_ros_interfaces" / "srv" / "InjectIncident.srv",
            root / "ros2_ws" / "src" / "humanoidsim_ros_interfaces" / "srv" / "PlayTrace.srv",
            root / "ros2_ws" / "src" / "humanoidsim_ros" / "models" / "minimal_humanoid.urdf",
            root / "ros2_ws" / "src" / "humanoidsim_ros" / "launch" / "rviz_validation.launch.py",
            root / "ros2_ws" / "src" / "humanoidsim_ros" / "launch" / "gazebo_physics_validation.launch.py",
            root / "ros2_ws" / "src" / "humanoidsim_ros" / "config" / "validation.rviz",
        ]
        for path in expected:
            self.assertTrue(path.exists(), str(path))

    def test_ros_python_files_parse_without_ros_imports(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "ros2"
            / "ros2_ws"
            / "src"
            / "humanoidsim_ros"
            / "humanoidsim_ros"
        )
        for name in ("bridge_node.py", "visualizer_node.py", "play_trace_file.py"):
            ast.parse((root / name).read_text(encoding="utf-8"))

    def test_ros_launch_files_parse(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "ros2"
            / "ros2_ws"
            / "src"
            / "humanoidsim_ros"
            / "launch"
        )
        for name in ("rviz_validation.launch.py", "gazebo_physics_validation.launch.py"):
            ast.parse((root / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
