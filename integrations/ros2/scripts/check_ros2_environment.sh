#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUMANOIDSIM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export PYTHONPATH="$HUMANOIDSIM_ROOT/src:${PYTHONPATH:-}"
ros2 --help > /dev/null
python3 - <<'PY'
import importlib.util
for name in ("rclpy", "humanoidsim"):
    if importlib.util.find_spec(name) is None:
        raise SystemExit(f"missing Python package: {name}")
print("ROS 2 Python environment OK")
PY
if command -v gz >/dev/null 2>&1; then
  gz sim --versions || true
else
  echo "gz command not found; install Gazebo Harmonic if full Gazebo checks are required."
fi
