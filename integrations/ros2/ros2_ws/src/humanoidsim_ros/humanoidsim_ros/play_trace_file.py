from __future__ import annotations

import argparse
from pathlib import Path

import rclpy
from rclpy.node import Node

from humanoidsim_ros_interfaces.srv import PlayTrace


class PlayTraceClient(Node):
    def __init__(self) -> None:
        super().__init__("humanoidsim_play_trace_file")
        self.client = self.create_client(PlayTrace, "/humanoidsim/play_trace")

    def send(self, *, humanoid_id: str, trace_json: str, speed: float) -> tuple[bool, str]:
        if not self.client.wait_for_service(timeout_sec=5.0):
            return False, "PlayTrace service is not available."
        request = PlayTrace.Request()
        request.humanoid_id = humanoid_id
        request.trace_json = trace_json
        request.speed = float(speed)
        request.reset_scene = True
        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
        if future.result() is None:
            return False, "PlayTrace request timed out."
        response = future.result()
        return bool(response.accepted), str(response.message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--humanoid-id", default="")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    trace_json = Path(args.file).read_text(encoding="utf-8")
    rclpy.init()
    node = PlayTraceClient()
    try:
        ok, message = node.send(humanoid_id=args.humanoid_id, trace_json=trace_json, speed=args.speed)
        print(message)
        raise SystemExit(0 if ok else 1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
