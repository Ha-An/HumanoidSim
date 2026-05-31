#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUMANOIDSIM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ROS_WS="$HUMANOIDSIM_ROOT/integrations/ros2/ros2_ws"

source /opt/ros/jazzy/setup.bash
source "$ROS_WS/install/setup.bash"

export PYTHONPATH="$HUMANOIDSIM_ROOT/src:$ROS_WS/install/humanoidsim_ros/lib/python3.12/site-packages:$ROS_WS/install/humanoidsim_ros_interfaces/lib/python3.12/site-packages:/opt/ros/jazzy/lib/python3.12/site-packages:${PYTHONPATH:-}"

LOG_FILE="${1:-/tmp/humanoidsim_bridge.log}"
rm -f "$LOG_FILE"

ros2 run humanoidsim_ros humanoidsim_bridge_node > "$LOG_FILE" 2>&1 &
NODE_PID=$!

cleanup() {
  if kill -0 "$NODE_PID" >/dev/null 2>&1; then
    kill "$NODE_PID" >/dev/null 2>&1 || true
    wait "$NODE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

sleep 3
ros2 node list | grep -q "/humanoidsim_bridge"
ros2 service list | grep -q "/humanoidsim/expand_task"
ros2 service list | grep -q "/humanoidsim/validate_transition"
ros2 service list | grep -q "/humanoidsim/inject_incident"
ros2 service list | grep -q "/humanoidsim/get_incident_protocol"
ros2 action list | grep -q "/humanoidsim/execute_task"
ros2 action list | grep -q "/humanoidsim/execute_primitive"
ros2 action list | grep -q "/humanoidsim/recover_incident"

cleanup
cat "$LOG_FILE"
echo "HumanoidSim ROS bridge node smoke check passed."
