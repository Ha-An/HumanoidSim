#!/usr/bin/env bash
set -euo pipefail

if ! grep -qi "Ubuntu 24.04" /etc/os-release; then
  echo "This script targets Ubuntu 24.04 for ROS 2 Jazzy." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y software-properties-common curl gnupg lsb-release python3-pip
sudo add-apt-repository universe -y

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt-get update
sudo apt-get install -y ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-robot-state-publisher ros-jazzy-xacro

if ! sudo apt-get install -y python3-colcon-common-extensions; then
  python3 -m pip install --break-system-packages colcon-common-extensions
fi

if ! grep -q "source /opt/ros/jazzy/setup.bash" "$HOME/.bashrc"; then
  echo "source /opt/ros/jazzy/setup.bash" >> "$HOME/.bashrc"
fi

echo "ROS 2 Jazzy and Gazebo Harmonic ROS integration packages are installed."
