# HumanoidSim ROS 2 / RViz / Gazebo Adapter

이 adapter는 ROS dependency를 HumanoidSim Python core 밖에 둡니다. 목적은 HumanoidSim의 task, primitive, incident, recovery, state-transition 정의를 ROS 2 action, service, topic, RViz visualization, Gazebo spawn으로 검증하는 것입니다.

## 대상 환경

- WSL2 Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- HumanoidSim repo 경로: `/mnt/c/Github/HumanoidSim`

## 설치와 빌드

WSL2 Ubuntu 24.04에서 실행합니다.

```bash
cd /mnt/c/Github/HumanoidSim
bash integrations/ros2/scripts/install_ros2_jazzy_gazebo_harmonic.sh
cd integrations/ros2/ros2_ws
source /opt/ros/jazzy/setup.bash
export PYTHONPATH=/mnt/c/Github/HumanoidSim/src:$PYTHONPATH
colcon build
source install/setup.bash
```

## Interactive UI와 함께 사용

Windows PowerShell에서 실행합니다.

```powershell
cd C:\Github\HumanoidSim
.\.venv\Scripts\python.exe -m humanoidsim lab-ui --ros --gazebo --wsl-distro Ubuntu-24.04
```

브라우저에서는 다음 순서로 사용합니다.

1. Task 또는 Incident를 선택합니다.
2. `Run`을 눌러 HumanoidSim trace를 생성합니다.
3. 내장 Browser 3D Viewer에서 즉시 동작을 확인합니다.
4. `Launch RViz`를 눌러 RViz validation stack을 실행합니다.
5. `Play in RViz`를 눌러 같은 trace를 ROS `PlayTrace` service로 전달합니다.
6. `Launch Gazebo`를 눌러 별도 physics validation scene을 실행합니다.

Browser 3D Viewer는 ROS 없이 가장 빠르게 trace를 확인하는 경로입니다. RViz는 ROS topic과 URDF joint animation을 검증합니다. Gazebo는 bundled minimal humanoid model이 physics scene에 spawn되는지 확인합니다. v1에서는 실제 휴머노이드 보행 제어까지 검증하지 않습니다.

세 화면은 같은 역할을 하지 않습니다. Browser viewer는 trace 의미와 step 순서를 확인하고, RViz는 ROS interface와 joint/TF publication을 확인하며, Gazebo는 model spawn과 physics scene 연결을 확인합니다. 실제 보행 안정성, 접촉 역학, controller tuning 결과를 검증한 것으로 해석하면 안 됩니다.

## ROS Interfaces

Actions:

- `/humanoidsim/execute_task`
- `/humanoidsim/execute_primitive`
- `/humanoidsim/recover_incident`

Services:

- `/humanoidsim/expand_task`
- `/humanoidsim/validate_transition`
- `/humanoidsim/inject_incident`
- `/humanoidsim/get_incident_protocol`
- `/humanoidsim/play_trace`

Topics:

- `/humanoid/{id}/state`
- `/humanoidsim/events`
- `/tf`
- `/joint_states`
- `/visualization_marker_array`

## 직접 실행 명령

Bridge action/service node를 실행합니다.

```bash
ros2 run humanoidsim_ros humanoidsim_bridge_node
```

RViz visualization stack을 실행합니다.

```bash
ros2 launch humanoidsim_ros rviz_validation.launch.py
```

Gazebo physics validation stack을 실행합니다.

```bash
ros2 launch humanoidsim_ros gazebo_physics_validation.launch.py
```

저장된 interactive trace를 RViz로 보냅니다.

```bash
ros2 run humanoidsim_ros play_trace_file --file /mnt/c/Github/HumanoidSim/outputs/interactive_lab/<run>/<session>/trace.json --speed 1.0
```

## Humanoid 모델

Adapter는 minimal block humanoid URDF를 포함합니다.

```text
ros2_ws/src/humanoidsim_ros/models/minimal_humanoid.urdf
```

이 모델은 팔, 다리, 그리퍼 joint를 가진 validation asset입니다. 실제 물리 로봇 제어기나 보행 controller가 아닙니다. 공개 휴머노이드 모델은 이후 custom launch/config에서 model path와 joint mapping을 교체해 연결할 수 있습니다.

## Smoke Check

```bash
cd /mnt/c/Github/HumanoidSim
bash integrations/ros2/scripts/check_ros2_environment.sh
bash integrations/ros2/scripts/smoke_bridge_node.sh
bash integrations/ros2/scripts/smoke_visualizer_node.sh
```
