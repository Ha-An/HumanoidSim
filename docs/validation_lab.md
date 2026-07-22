# HumanoidSim Validation Lab

이 문서는 ManSim과 분리된 HumanoidSim 독립 검증 도구를 설명합니다. 목적은 HumanoidSim이 소유한 `State`, `Task`, `Primitive`, `Incident`, `Recovery protocol` 정의가 실제 실행 trace로 자연스럽게 전개되는지 확인하는 것입니다.

현재 검증 기준은 package `0.1.0`, catalog `0.2.0-core`, task 87개, primitive 61개, incident 35개입니다. Catalog가 변경되면 생성된 reference와 이 숫자도 함께 갱신해야 합니다.

## 실행 명령

전체 validation lab을 실행합니다.

```powershell
cd C:\Github\HumanoidSim
.\.venv\Scripts\python.exe -m humanoidsim validate-lab --all --out outputs\validation\latest
```

브라우저에서 Task 또는 Incident를 직접 선택하고 실행 과정을 관찰하려면 interactive UI를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim lab-ui --host 127.0.0.1 --port 8765
```

RViz와 Gazebo 버튼까지 표시하려면 ROS 2 workspace를 먼저 build한 뒤 다음처럼 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim lab-ui --ros --gazebo --wsl-distro Ubuntu-24.04
```

Gazebo physics validation만 직접 띄울 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim physics-validation --wsl-distro Ubuntu-24.04
```

## 검증 범위

| 영역 | 검증 내용 |
| --- | --- |
| Catalog | 모든 task, primitive, composite hierarchy, nested child task reference를 검증합니다. |
| State Schema | 네 state 축, primitive state profile, transition graph를 검증합니다. |
| Task Execution | 모든 task를 mock input으로 실행하고 primitive start/end마다 `transition_humanoid_state()`를 호출합니다. |
| Incident Recovery | 모든 incident를 주입하고 recovery protocol을 task/primitive execution trace로 전개합니다. |
| Transition Coverage | state transition graph 중 task/recovery/fuzz trace에서 실제 관찰된 edge를 집계합니다. |
| Fuzz | random task와 incident 조합을 실행해 invalid transition, unknown reference, invariant 위반을 찾습니다. |

Task Execution trace에는 HumanoidSim primitive difficulty weight 기반의 task complexity가 포함됩니다. 계산식은 `C_task(t)=sum_k a_tk*d_k`이며, `a_tk`는 task를 primitive leaf step까지 전개했을 때 primitive `p_k`가 등장한 횟수, `d_k`는 해당 primitive의 difficulty weight입니다. Validation dashboard는 task별 complexity와 primitive leaf count를 표에 표시합니다.

Validation Lab의 task complexity는 정적 catalog 구조를 검증하는 값입니다. ManSim의 OTC는 이 값에 실제 simulation에서 완료된 top-level task instance 수를 곱해 기간별 운영 부담으로 집계합니다.

## 결과물

| Artifact | 설명 |
| --- | --- |
| `validation_summary.json` | 전체 pass/fail, catalog count, issue count, coverage summary입니다. |
| `task_execution_traces.jsonl` | task별 mock execution trace입니다. |
| `incident_recovery_traces.jsonl` | incident별 recovery protocol execution trace입니다. |
| `state_transition_coverage.json` | axis별 transition coverage입니다. |
| `fuzz_report.json` | fuzz case, failure, negative check 결과입니다. |
| `validation_dashboard.html` | 브라우저에서 볼 수 있는 standalone validation dashboard입니다. |

## Interactive UI

Interactive UI는 HumanoidSim 전용 local web server입니다. ManSim hub, ManSim dashboard, ManSim artifact와 연결하지 않습니다.

### 화면 구성

| 화면 | 역할 |
| --- | --- |
| Input | Task category, Task, Incident, humanoid id, speed, args/context JSON을 입력합니다. |
| Browser 3D Viewer | WebGL 기반 3D viewer입니다. ROS 없이 Task/Incident trace의 `motion_hint`, `manipulation_hint`를 재생합니다. |
| Step Timeline | 사용자 관찰용 step timeline입니다. 내부 검증용 `primitive_finished` 이벤트는 숨기고 실행 step 단위로 표시합니다. |
| State Cards | 현재 step의 Availability, Mobility, Power, Manipulation state를 표시합니다. |
| Issues | trace 생성 중 발견된 validation issue를 JSON으로 표시합니다. |

### Browser 3D Viewer

Browser 3D Viewer는 빠른 검증용 scripted motion viewer입니다.

- WebGL renderer를 사용합니다.
- perspective camera, depth test, 조명, grid, reference object를 표시합니다.
- 좌클릭 drag로 yaw/pitch를 회전합니다.
- 마우스 wheel로 확대/축소합니다.
- Shift drag 또는 우클릭 drag로 pan합니다.
- Reset View로 기본 카메라로 돌아갑니다.
- `NAVIGATE_TO` 중에는 다리 움직임과 path 진행을 표시합니다.
- manipulation primitive 중에는 팔/그리퍼 움직임을 표시합니다.
- recovery step은 `CODE (RECOVERY)`로 표시하고 색상으로 구분합니다.

이 viewer는 RViz를 대체하는 물리/ROS 검증 도구가 아니라, HumanoidSim trace를 브라우저에서 즉시 확인하기 위한 검증 UI입니다.

### Step Timeline 표시 규칙

Trace 내부에는 state transition 검증을 위해 `primitive_started`와 `primitive_finished`가 모두 포함됩니다. 하지만 사용자 화면에서는 동일 primitive가 두 번 보이지 않도록 다음 규칙을 적용합니다.

- `primitive_started`는 표시합니다.
- `recovery_primitive_started`는 표시합니다.
- `primitive_finished`와 `recovery_primitive_finished`는 숨깁니다.
- `task_boundary`와 `recovery_task_boundary`는 child task 또는 recovery task boundary로 표시합니다.
- timeline active row는 viewer time과 동기화됩니다.

## API

| API | 역할 |
| --- | --- |
| `GET /api/catalog` | Task와 Incident catalog를 반환합니다. |
| `POST /api/run-task` | 선택한 task를 `run_task_trace()`로 실행하고 trace를 저장합니다. |
| `POST /api/run-incident` | 선택한 incident를 `run_incident_trace()`로 실행하고 recovery trace를 저장합니다. |
| `GET /api/session/<id>` | 저장된 trace session을 반환합니다. |
| `POST /api/ros/launch-rviz` | `--ros` 모드에서 RViz validation launch를 실행합니다. |
| `POST /api/ros/play-trace` | 현재 trace를 ROS `PlayTrace` service로 전달합니다. |
| `POST /api/ros/launch-gazebo` | `--gazebo` 모드에서 Gazebo physics validation launch를 실행합니다. |

각 trace는 `outputs/interactive_lab/<timestamp>/<session_id>/trace.json`에 저장됩니다. Trace event에는 `time_s`, `duration_s`, `task_code`, `primitive_call_code`, `is_recovery`, `state_before`, `state_after`, `motion_hint`, `manipulation_hint`가 포함됩니다.

## Recovery 상태 규칙

정상 task/primitive 실행 중인 primitive는 Availability State에서 `EXECUTING`입니다. 반면 incident recovery protocol 안에서 실행되는 task/primitive는 예외 처리 절차이므로 Availability를 `BLOCKED`로 유지합니다.

Validation Lab과 Interactive UI는 recovery step을 `CODE (RECOVERY)` 형태로 표시합니다. 이 상태 규칙이 깨지면 issue로 기록합니다.

## ROS 2 / RViz / Gazebo Adapter

ROS 2 연동은 HumanoidSim core와 분리된 adapter로 제공합니다.

- Actions: `ExecuteTask`, `ExecutePrimitive`, `RecoverIncident`
- Services: `ExpandTask`, `ValidateTransition`, `InjectIncident`, `GetIncidentProtocol`, `PlayTrace`
- Topics: `/humanoid/{id}/state`, `/humanoidsim/events`, `/tf`, `/joint_states`, `/visualization_marker_array`
- Launch: `rviz_validation.launch.py`, `gazebo_physics_validation.launch.py`

기준 환경은 WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic입니다. 이 adapter는 실제 보행 제어 검증이 아니라 HumanoidSim task/action/state/recovery 흐름을 ROS action, service, topic, RViz marker, Gazebo spawn으로 검증하기 위한 것입니다.

자세한 설치 방법은 [ROS 2 Adapter](../integrations/ros2/README.md)를 참고합니다.
