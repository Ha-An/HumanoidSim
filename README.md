# HumanoidSim

HumanoidSim은 휴머노이드 로봇의 `State`, `Task`, `Primitive`, `Incident`, `Recovery protocol`을 도메인 독립적으로 정의하고 검증하는 라이브러리입니다. ManSim 같은 시뮬레이터는 HumanoidSim의 정의를 import해서 사용할 수 있지만, HumanoidSim 자체는 ManSim에 의존하지 않습니다.

현재 Python package version은 `0.1.0`, core catalog version은 `0.2.0-core`입니다. ManSim v0.5는 이 repository를 editable install해 최신 catalog와 complexity API를 사용합니다.

![HumanoidSim overview](assets/IMG.png)

## 핵심 원칙

- Humanoid의 기본 의미 정의는 HumanoidSim이 소유합니다.
- Task는 목표 작업, Primitive는 최소 실행 단위, State는 특정 시점의 상태 snapshot입니다.
- Incident는 새 state가 아니라 `StateReason + recovery protocol`입니다.
- Composite task는 child task를 직접 포함하는 workflow입니다.
- Recovery protocol step은 기존 primitive 또는 task를 참조해야 합니다.
- Validation Lab과 ROS adapter는 HumanoidSim 독립 검증 도구이며 ManSim hub나 ManSim artifact에 연결하지 않습니다.

## 현재 카탈로그

| 항목 | 개수 | 설명 |
| --- | ---: | --- |
| Task | 87 | 제조, 조선소, 범용 휴머노이드 작업 카탈로그입니다. |
| Atomic Task | 56 | Primitive sequence만으로 실행되는 단일 task입니다. |
| Composite Task | 31 | 하나 이상의 child task call을 포함하는 workflow task입니다. |
| Primitive | 61 | Task를 구성하는 최소 실행 skill입니다. |
| Incident | 35 | 범용 휴머노이드 돌발상황 taxonomy입니다. |

## Task 구조

| Level | 의미 | 구조 규칙 |
| --- | --- | --- |
| `PRIMITIVE_SKILL` | 더 이상 쪼개지지 않는 최소 실행 skill | child step을 갖지 않습니다. |
| `ATOMIC_TASK` | primitive skill만으로 구성되는 실행 가능한 task | 모든 `StepCall.call_code`가 primitive를 참조합니다. |
| `COMPOSITE_TASK` | 하위 task를 직접 포함하는 workflow | 최소 1개 이상의 child task call을 포함합니다. orchestration primitive를 함께 가질 수 있습니다. |

`StepCall.call_code`는 primitive code뿐 아니라 task code도 참조할 수 있습니다. 이때 `expected_level`은 `PRIMITIVE_SKILL`, `ATOMIC_TASK`, `COMPOSITE_TASK` 중 실제 참조 대상의 level과 일치해야 합니다.

예를 들어 `REPLENISH_MATERIAL`은 generic material request를 받은 뒤 `PRIMITIVE_IDENTIFY_ITEM` 단계에서 실제 material instance를 식별하고, child task인 `TRANSFER`로 운반을 수행합니다.

## Shipyard Task Extension

ManSim `shipyard_basic` scenario 검증을 위해 다음 task가 HumanoidSim catalog에 추가되었습니다. 새 primitive는 만들지 않고 기존 primitive를 재사용합니다.

| Task | Level | Purpose |
| --- | --- | --- |
| `WELD_SEAM` | `ATOMIC_TASK` | Ship section 또는 exterior surface tile의 seam/joint를 안전 확인, 표면 localize, tool operation, result inspection 순서로 용접합니다. |
| `PAINT_SURFACE` | `ATOMIC_TASK` | 준비된 ship section 또는 exterior surface tile에 paint/coating을 적용하고 coverage를 검증합니다. |
| `APPLY_SEALANT` | `ATOMIC_TASK` | 필요한 section/tile joint 또는 edge에 sealant를 적용하고 적용량을 검증합니다. |
| `VERIFY_SHIP_SECTION` | `ATOMIC_TASK` | Ship section 또는 exterior surface tile의 weld, sealant, paint 품질을 검사하고 결과를 분류/기록합니다. |

Vehicle 기반 batch logistics는 기존 `OPERATE_VEHICLE_TRANSPORT` task를 사용합니다. ManSim `shipyard_basic`에서는 이 task로 cart가 `weld_wire` 또는 `paint_can`을 source에서 parking spot까지 운반하고, 마지막 작업 tile 공급은 기존 `TRANSFER` task로 표현합니다.

Robot-to-robot handover는 human/operator handover와 분리해서 정의합니다. `HANDOVER_ITEM_TO_ROBOT`은 `SYNC_WITH_ROBOT`과 `EXECUTE_ROBOT_COLLABORATION_ACTION`을 사용하고, 사람 대상 handover는 기존 human collaboration primitive를 유지합니다.

## Primitive Difficulty Weight와 OTC

OTC(Operational Task Complexity)는 시뮬레이션 기간 동안 발생한 task instance들이 얼마나 어려운 primitive 조합으로 구성되어 있는지 누적해서 보는 지표입니다. HumanoidSim의 모든 primitive는 `metadata.operational_complexity.difficulty_weight` 값을 가지며, ManSim 같은 외부 시뮬레이터는 이 값을 읽어 task별 복잡도와 기간별 OTC를 계산할 수 있습니다.

난이도는 `0.0`부터 `1.0`까지 0.1 단위로 부여합니다. 값은 실행 시간 자체가 아니라 동작 정밀도, 조작 난이도, 안전 위험도, 협업 필요성, 실패 복구 부담을 반영합니다.

| 범위 | 그룹 | 의미 |
| --- | --- | --- |
| `0.0 ~ 0.1` | Administrative | 기록, 상태 갱신, 단순 선언처럼 로봇 실행 부담이 거의 없는 primitive |
| `0.2 ~ 0.3` | Low Operational | 낮은 부담의 확인, 검증, 표준 이동 primitive |
| `0.4 ~ 0.5` | Standard Robot Skill | localize, reach, grasp/place 등 일반적인 로봇 skill |
| `0.6 ~ 0.7` | Manipulation & Process | tool, machine, vehicle, material application처럼 물리 상태나 공정 품질을 바꾸는 primitive |
| `0.8 ~ 0.9` | Coordination & Recovery | robot sync, lockout, human/robot collaboration처럼 동기화와 안전 부담이 큰 primitive |
| `1.0` | Critical | 실패 시 system stop, 장기 recovery, 인명/설비 위험으로 이어질 수 있는 primitive |

Task complexity는 task를 primitive leaf step까지 전개한 뒤, 각 primitive 등장 횟수와 difficulty weight의 가중합으로 계산합니다. 자세한 primitive별 값은 [docs/primitives_reference.md](docs/primitives_reference.md)의 Difficulty 컬럼을 참고하세요.

`humanoidsim validate-lab --all`로 생성되는 `validation_dashboard.html`은 각 task trace 옆에 정적 task complexity와 primitive leaf count를 함께 표시합니다. Python API에서는 `task_complexity(task_code)`와 `task_complexity_index()`로 같은 값을 읽을 수 있습니다.

## State 모델

Task와 State는 분리됩니다. 예를 들어 `TRANSFER` 수행 중인 휴머노이드는 `availability=EXECUTING`, `mobility=NAVIGATING`일 수 있고, task 정보는 `task_context`에 기록됩니다.

| 축 | 상태 |
| --- | --- |
| Availability | `AVAILABLE`, `ASSIGNED`, `EXECUTING`, `WAITING`, `BLOCKED`, `OFFLINE`, `DISABLED` |
| Mobility | `STATIONARY`, `NAVIGATING`, `DOCKING` |
| Power | `POWER_NORMAL`, `POWER_LOW`, `POWER_CRITICAL`, `DEPLETED`, `CHARGING` |
| Manipulation | `FREE`, `REACHING`, `HOLDING`, `PLACING` |

정상적으로 실행 중인 모든 primitive는 Availability State에서 `EXECUTING`입니다. Incident recovery protocol 안에서 실행되는 task/primitive는 예외 처리 절차이므로 Availability를 `BLOCKED`로 유지하고, 현재 recovery step은 `task_context`에 기록합니다.

## Incident 모델

Incident는 perception, manipulation, resource, traffic, power, communication, safety, unknown 계열로 분류됩니다. 예시는 다음과 같습니다.

- `OBJECT_RECOGNITION_FAILED`
- `GRIP_FAILED`
- `ITEM_DROPPED`
- `RESOURCE_PREEMPTED`
- `PATH_BLOCKED`
- `TRAFFIC_WAIT`
- `UNKNOWN`

Runtime이 관찰한 domain-specific reason은 alias resolution을 통해 canonical incident code로 연결할 수 있습니다. 예를 들어 `material_shelf_slot_empty` 같은 외부 reason은 `RESOURCE_PREEMPTED` 또는 `RESOURCE_MISSING`으로 해석될 수 있습니다.

## Generic Item Request

Task input의 `item`은 concrete item id일 수도 있고 generic request일 수도 있습니다. 예를 들어 `REPLENISH_MATERIAL`은 `entity_type=material`, `selection_policy=available_material_from_source` 형태로 “사용 가능한 material 하나”를 요청할 수 있습니다. 이 경우 concrete item instance는 task 후보 생성 시점이 아니라 `PRIMITIVE_IDENTIFY_ITEM` 실행 단계에서 확정됩니다.

## Public API

```python
from humanoidsim import (
    HumanoidProfile,
    load_task_catalog,
    validate_task_sequence,
    simulate_task_sequence,
    expand_task_steps,
    transition_humanoid_state,
    run_task_trace,
    run_incident_trace,
)
```

`expand_task_steps(task_code, args, catalog=...)`는 nested composite task를 parent task, child task, primitive leaf까지 보존한 plan row로 반환합니다.

## ManSim v0.5 Integration

HumanoidSim과 ManSim의 책임 경계는 다음과 같습니다.

- HumanoidSim은 task hierarchy, primitive difficulty, state transition, incident recovery 의미를 제공합니다.
- ManSim은 factory/shipyard 조건에서 task instance를 만들고 item, machine, queue, battery 같은 domain side effect를 실행합니다.
- ManSim의 OTC는 완료된 top-level task instance와 HumanoidSim `task_complexity()` 결과를 결합해 계산합니다.
- ManSim이 최신 local 정의를 사용하도록 `python -m pip install -e ..\HumanoidSim` 형태의 editable install을 권장합니다.
- HumanoidSim Validation Lab과 ROS adapter는 ManSim Hub나 ManSim artifact에 의존하지 않습니다.

## 실행

가상환경을 활성화하고 editable package로 설치합니다.

```powershell
cd C:\Github\HumanoidSim
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e C:\Github\HumanoidSim
```

카탈로그와 sequence를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-catalog
.\.venv\Scripts\python.exe -m humanoidsim validate-sequence examples\manufacturing_sequence.json
```

정적 task sequence viewer를 생성합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim export-viewer examples\manufacturing_sequence.json --out outputs\task_sequence_viewer.html
```

## Standalone Validation Lab

전체 validation lab을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-lab --all --out outputs\validation\latest
```

이 명령은 catalog/schema validation, mock primitive executor 기반 task/recovery 실행, state transition coverage, fuzz validation을 수행하고 `validation_dashboard.html`을 생성합니다.

## Interactive Validation UI

브라우저에서 Task 또는 Incident를 선택해 실행 trace를 바로 관찰할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim lab-ui --host 127.0.0.1 --port 8765
```

ROS 2/RViz와 Gazebo 버튼까지 표시하려면 다음처럼 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim lab-ui --ros --gazebo --wsl-distro Ubuntu-24.04
```

Interactive UI는 다음을 제공합니다.

- Task category -> Task 선택 흐름
- Incident 선택 및 context JSON 입력
- Step timeline과 state axes 동기화
- WebGL 기반 Browser 3D Viewer
- viewer 확대, 회전, pan, reset controls
- primitive별 이동, 팔/다리/그리퍼 scripted motion
- recovery step의 `CODE (RECOVERY)` 표시
- RViz launch와 `PlayTrace` 연동
- Gazebo physics validation launch

Browser 3D Viewer는 ROS 없이 `motion_hint`와 `manipulation_hint`를 즉시 재생하는 빠른 검증 경로입니다. RViz는 같은 trace를 ROS 2 `/tf`, `/joint_states`, marker로 publish해 minimal humanoid URDF 움직임을 비교합니다. Gazebo는 minimal humanoid model이 physics scene에 spawn되는지 확인하는 별도 validation mode입니다.

Gazebo physics validation만 직접 실행할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim physics-validation --wsl-distro Ubuntu-24.04
```

## ROS 2 / RViz / Gazebo Adapter

ROS 2 연동은 HumanoidSim core와 분리된 adapter로 제공합니다. 기준 환경은 WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic입니다.

자세한 설치와 실행 방법은 [ROS 2 Adapter](integrations/ros2/README.md)를 참고합니다.

## Reference

- [Docs Index](docs/README.md): 현재 catalog 기준과 권장 읽기 순서를 정리합니다.
- [Task Reference](docs/tasks_reference.md): task level, category, input, resource, nested sequence를 정리합니다.
- [Primitive Reference](docs/primitives_reference.md): primitive group, state relation, 사용 task를 정리합니다.
- [State Reference](docs/state_reference.md): Availability, Mobility, Power, Manipulation 축과 transition diagram을 정리합니다.
- [Incident Reference](docs/incident_reference.md): incident taxonomy, state reason, recovery protocol을 정리합니다.
- [Validation Lab](docs/validation_lab.md): standalone validation, interactive UI, ROS/RViz/Gazebo 검증 방법을 정리합니다.

## 주요 파일

- `src/humanoidsim/task_schema.py`: task, step, resource, registry validation schema
- `src/humanoidsim/state_schema.py`: humanoid state enum, snapshot, primitive state profile, transition API
- `src/humanoidsim/incident_schema.py`: incident taxonomy, recovery protocol, incident transition event
- `src/humanoidsim/interactive_trace.py`: browser/RViz용 task and incident trace runner
- `src/humanoidsim/interactive_lab_ui.py`: standalone local web UI
- `src/humanoidsim/validation_lab.py`: batch validation lab runner and dashboard generator
- `integrations/ros2/`: ROS 2/RViz/Gazebo adapter
- `data/tasks/`: task JSON catalog
- `data/primitives/`: primitive JSON catalog
- `data/state_schema_core.json`: state axes, primitive state profile, transition graph
- `data/incident_schema_core.json`: incident taxonomy and recovery protocol

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Reference 문서는 catalog JSON에서 생성합니다. Task, primitive, incident definition을 수정한 뒤 다음 명령으로 문서를 다시 만들고 catalog와 전체 test를 검증합니다.

```powershell
.\.venv\Scripts\python.exe scripts\generate_reference_docs.py
.\.venv\Scripts\python.exe -m humanoidsim validate-catalog
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Customization

Task를 추가할 때는 task JSON을 만들고 `data/task_catalog_core.json`에 등록한 뒤 `validate-catalog`와 unit test를 실행합니다.

State를 추가할 때는 enum, `data/state_schema_core.json`, primitive profile, 문서, 테스트를 함께 갱신합니다.

Incident를 추가할 때는 `data/incident_schema_core.json`에 uppercase canonical code를 추가하고 category, severity, default availability, trigger primitives, recovery protocol, retry policy를 정의합니다. Recovery protocol은 반드시 기존 primitive 또는 task를 참조해야 합니다.
