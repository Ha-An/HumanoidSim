#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUMANOIDSIM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ROS_WS="$HUMANOIDSIM_ROOT/integrations/ros2/ros2_ws"

source /opt/ros/jazzy/setup.bash
source "$ROS_WS/install/setup.bash"
export PYTHONPATH="$HUMANOIDSIM_ROOT/src:$ROS_WS/install/humanoidsim_ros/lib/python3.12/site-packages:$ROS_WS/install/humanoidsim_ros_interfaces/lib/python3.12/site-packages:/opt/ros/jazzy/lib/python3.12/site-packages:${PYTHONPATH:-}"

TRACE_FILE="${1:-/tmp/humanoidsim_trace_smoke.json}"
cat > "$TRACE_FILE" <<'JSON'
{
  "ok": true,
  "trace_type": "task",
  "humanoid_id": "LAB-H1",
  "session_id": "SMOKE-TRACE",
  "summary": {"task_code": "TRANSFER", "duration_s": 2.0},
  "events": [
    {
      "kind": "primitive_started",
      "time_s": 0.0,
      "duration_s": 2.0,
      "task_code": "TRANSFER",
      "primitive_call_code": "NAVIGATE_TO",
      "display_code": "NAVIGATE_TO",
      "is_recovery": false,
      "state_after": {"availability": "EXECUTING", "mobility": "NAVIGATING", "power": "POWER_NORMAL", "manipulation": "FREE"},
      "motion_hint": {"type": "translate", "distance_m": 0.8, "heading_rad": 0.0},
      "manipulation_hint": {"type": "work"}
    }
  ]
}
JSON

ros2 run humanoidsim_ros humanoidsim_visualizer_node > /tmp/humanoidsim_visualizer.log 2>&1 &
NODE_PID=$!

cleanup() {
  if kill -0 "$NODE_PID" >/dev/null 2>&1; then
    kill "$NODE_PID" >/dev/null 2>&1 || true
    wait "$NODE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

sleep 3
ros2 service list | grep -q "/humanoidsim/play_trace"
ros2 run humanoidsim_ros play_trace_file --file "$TRACE_FILE" --speed 2.0
cleanup
cat /tmp/humanoidsim_visualizer.log
echo "HumanoidSim ROS visualizer smoke check passed."
