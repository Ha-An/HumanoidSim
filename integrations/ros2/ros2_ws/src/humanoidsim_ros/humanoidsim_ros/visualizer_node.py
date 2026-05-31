from __future__ import annotations

import json
import math
import re
from typing import Any

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray

from humanoidsim_ros_interfaces.srv import PlayTrace


JOINT_NAMES = [
    "left_arm_joint",
    "right_arm_joint",
    "left_leg_joint",
    "right_leg_joint",
    "left_gripper_joint",
    "right_gripper_joint",
]


class HumanoidSimVisualizerNode(Node):
    def __init__(self) -> None:
        super().__init__("humanoidsim_visualizer")
        self.trace: dict[str, Any] | None = None
        self.humanoid_id = "LAB-H1"
        self.speed = 1.0
        self.started_ns: int | None = None
        self.tf_broadcaster = TransformBroadcaster(self)
        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/visualization_marker_array", 10)
        self.state_pub = self.create_publisher(String, f"/humanoid/{_topic_token(self.humanoid_id)}/state", 10)
        self.create_service(PlayTrace, "/humanoidsim/play_trace", self._play_trace)
        self.create_timer(0.05, self._tick)

    def _play_trace(self, request, response):
        try:
            trace = json.loads(request.trace_json or "{}")
            if not isinstance(trace, dict) or "events" not in trace:
                raise ValueError("trace_json must contain an events array.")
            self.trace = trace
            self.humanoid_id = request.humanoid_id or trace.get("humanoid_id") or "LAB-H1"
            self.speed = max(0.05, float(request.speed or 1.0))
            self.started_ns = self.get_clock().now().nanoseconds
            self.state_pub = self.create_publisher(String, f"/humanoid/{_topic_token(self.humanoid_id)}/state", 10)
            response.accepted = True
            response.message = "trace playback started"
        except Exception as exc:  # noqa: BLE001 - ROS service reports errors in response.
            response.accepted = False
            response.message = str(exc)
        return response

    def _tick(self) -> None:
        elapsed = 0.0
        if self.trace and self.started_ns is not None:
            elapsed = ((self.get_clock().now().nanoseconds - self.started_ns) / 1_000_000_000.0) * self.speed
        pose, event, progress = _pose_for_trace(self.trace, elapsed)
        self._publish_tf(pose)
        self._publish_joints(event, elapsed, progress)
        self._publish_markers(event, pose)
        if event:
            msg = String()
            msg.data = json.dumps(event.get("state_after", {}), ensure_ascii=False)
            self.state_pub.publish(msg)

    def _publish_tf(self, pose: dict[str, float]) -> None:
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = "world"
        transform.child_frame_id = "base_link"
        transform.transform.translation.x = float(pose["x"])
        transform.transform.translation.y = float(pose["y"])
        transform.transform.translation.z = float(pose["z"])
        q = _yaw_quaternion(float(pose["yaw"]))
        transform.transform.rotation.x = q[0]
        transform.transform.rotation.y = q[1]
        transform.transform.rotation.z = q[2]
        transform.transform.rotation.w = q[3]
        self.tf_broadcaster.sendTransform(transform)

    def _publish_joints(self, event: dict[str, Any] | None, elapsed: float, progress: float) -> None:
        primitive = str((event or {}).get("primitive_call_code") or "").upper()
        phase = math.sin(elapsed * 8.0)
        arm = 0.0
        grip = 0.0
        if primitive == "NAVIGATE_TO":
            left_leg = 0.45 * phase
            right_leg = -0.45 * phase
            arm = -0.25 * phase
        elif primitive in {"REACH_TO", "GRASP"}:
            left_leg = right_leg = 0.0
            arm = -0.9 * min(1.0, progress + 0.1)
            grip = 0.45 if primitive == "GRASP" else 0.1
        elif primitive in {"LIFT", "PLACE", "RELEASE"}:
            left_leg = right_leg = 0.0
            arm = -0.65 + 0.18 * phase
            grip = -0.2 if primitive == "RELEASE" else 0.35
        else:
            left_leg = right_leg = 0.0
            arm = 0.15 * phase if event and event.get("kind") not in {"task_completed"} else 0.0

        joint_state = JointState()
        joint_state.header.stamp = self.get_clock().now().to_msg()
        joint_state.name = JOINT_NAMES
        joint_state.position = [arm, arm, left_leg, right_leg, grip, -grip]
        self.joint_pub.publish(joint_state)

    def _publish_markers(self, event: dict[str, Any] | None, pose: dict[str, float]) -> None:
        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = "world"
        marker.ns = "humanoidsim_status"
        marker.id = 1
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        marker.pose.position.x = float(pose["x"])
        marker.pose.position.y = float(pose["y"])
        marker.pose.position.z = 1.25
        marker.scale.z = 0.18
        marker.color.a = 1.0
        marker.color.r = 1.0 if event and event.get("is_recovery") else 0.45
        marker.color.g = 0.75
        marker.color.b = 0.25 if event and event.get("is_recovery") else 1.0
        marker.text = str((event or {}).get("display_code") or "HumanoidSim")
        self.marker_pub.publish(MarkerArray(markers=[marker]))


def _pose_for_trace(trace: dict[str, Any] | None, elapsed: float) -> tuple[dict[str, float], dict[str, Any] | None, float]:
    pose = {"x": 0.0, "y": 0.0, "z": 0.25, "yaw": 0.0}
    if not trace:
        return pose, None, 0.0
    events = [row for row in trace.get("events", []) if isinstance(row, dict)]
    active: dict[str, Any] | None = events[-1] if events else None
    active_progress = 0.0
    for row in events:
        start = float(row.get("time_s") or 0.0)
        duration = max(0.0, float(row.get("duration_s") or 0.0))
        motion = row.get("motion_hint") if isinstance(row.get("motion_hint"), dict) else {}
        if duration <= 0.0:
            if start <= elapsed:
                active = row
            continue
        if elapsed >= start + duration:
            _apply_motion(pose, motion, 1.0)
            active = row
            active_progress = 1.0
        elif elapsed >= start:
            active = row
            active_progress = max(0.0, min(1.0, (elapsed - start) / duration))
            _apply_motion(pose, motion, active_progress)
            break
    return pose, active, active_progress


def _apply_motion(pose: dict[str, float], motion: dict[str, Any], progress: float) -> None:
    motion_type = str(motion.get("type") or "")
    if motion_type == "translate":
        distance = float(motion.get("distance_m") or 0.0) * progress
        pose["x"] += math.cos(pose["yaw"]) * distance
        pose["y"] += math.sin(pose["yaw"]) * distance
    elif motion_type == "rotate":
        pose["yaw"] += float(motion.get("angle_rad") or 0.0) * progress


def _yaw_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half = yaw / 2.0
    return (0.0, 0.0, math.sin(half), math.cos(half))


def _topic_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]", "_", value or "")
    return token or "humanoid"


def main() -> None:
    rclpy.init()
    node = HumanoidSimVisualizerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
