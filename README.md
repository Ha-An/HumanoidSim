# HumanoidSim_v0.1

HumanoidSim은 제조 환경의 휴머노이드 에이전트를 위한 독립 task 정의 및 검증 라이브러리입니다.

![HumanoidSim overview](assets/IMG.png)

## Humanoid State Model

HumanoidSim v0.1은 task와 state를 분리해서 다룹니다. `TaskSpec`은 로봇이 수행해야 하는 목표 작업이고, `StepCall`/primitive는 그 작업을 이루는 실행 단계입니다. 반면 `HumanoidStateSnapshot`은 특정 시점에 로봇이 어떤 운용 상태인지 기록합니다.

상태는 네 개의 축으로 정의합니다.

| 축 | 상태 | 의미 | Task/Primitive와의 관계 |
|---|---|---|---|
| Availability | `AVAILABLE` | 새 task 수락 가능 | 현재 실행 중인 task가 없음 |
| Availability | `ASSIGNED` | task는 받았지만 아직 본격 실행 전 | `TaskInstance`는 할당되었지만 step/primitive 시작 전 |
| Availability | `EXECUTING` | task 실행 중 | 현재 step 또는 primitive 실행 중 |
| Availability | `WAITING` | 조건 대기 중 | resource, input, safety clearance, dependency 등을 기다림 |
| Availability | `BLOCKED` | 진행 불가, 원인 필요 | `reason.code`로 원인을 남겨야 함 |
| Availability | `OFFLINE` | 운용 제외 | planner/execution loop에서 제외 |
| Availability | `DISABLED` | 방전/고장 등으로 작업 불가 | 전원, 고장, 안전 interlock 등으로 task 수행 불가 |
| Mobility | `STATIONARY` | 멈춰 있음 | 이동 primitive가 실행 중이 아님 |
| Mobility | `NAVIGATING` | 목적지로 이동 중 | `NAVIGATE_TO` primitive 실행 중 |
| Mobility | `DOCKING` | 충전기/작업대/설비에 정렬 중 | `DOCK`, `ALIGN` 계열 primitive 실행 중 |
| Power | `POWER_NORMAL` | 정상 전원 상태 | caller가 배터리/전원 기준으로 판단 |
| Power | `POWER_LOW` | 전원 낮음 | caller가 배터리/전원 기준으로 판단 |
| Power | `POWER_CRITICAL` | 전원 위험 수준 | caller가 배터리/전원 기준으로 판단 |
| Power | `DEPLETED` | 방전됨 | 보통 `DISABLED`와 함께 사용 |
| Power | `CHARGING` | 충전 중 | `MANAGE_ROBOT_POWER` task 또는 충전 primitive 수행 중 |
| Manipulation | `FREE` | 손이 비어 있음 | item/tool을 들고 있지 않음 |
| Manipulation | `REACHING` | 대상에 접근 중 | `REACH_TO` primitive 실행 중 |
| Manipulation | `HOLDING` | item/tool을 들고 있음 | `GRASP`, `LIFT` 이후 |
| Manipulation | `PLACING` | 내려놓는 중 | `PLACE`, `RELEASE` primitive 실행 중 |

예시 snapshot은 아래처럼 저장할 수 있습니다.

```json
{
  "humanoid_id": "A1",
  "availability": "EXECUTING",
  "mobility": "STATIONARY",
  "power": "POWER_NORMAL",
  "manipulation": "FREE",
  "task_context": {
    "task_code": "INSPECT_PRODUCT",
    "task_instance_id": "TASK-0007",
    "step_id": "s3_execute_quality_action",
    "primitive_call_code": "EXECUTE_QUALITY_ACTION",
    "execution_status": "RUNNING"
  }
}
```

코드에서는 `humanoidsim.state_schema` 또는 package root에서 바로 import할 수 있습니다.

```python
from humanoidsim import (
    AvailabilityState,
    HumanoidStateSnapshot,
    build_state_snapshot_for_task_lifecycle,
    apply_primitive_state_hint,
)
```

추후 state를 커스터마이즈하려면 `src/humanoidsim/state_schema.py`의 enum, `data/state_schema_core.json`, README 설명, `tests/test_state_schema.py`를 함께 갱신합니다. primitive에 따른 상태 전환이 필요하면 `primitive_state_hint()` mapping에도 새 규칙을 추가합니다.



## 구성

- `src/humanoidsim/task_schema.py` - `TaskSpec`, `TaskInstance`, resource, validation을 위한 public dataclass schema.
- `src/humanoidsim/catalog.py` - task catalog loader와 registry 구성.
- `src/humanoidsim/execution.py` - `HumanoidProfile`, sequence validation, timeline simulation.
- `src/humanoidsim/viewer.py` - task sequence와 animation을 확인하는 정적 HTML viewer 생성.
- `data/tasks/` - 제조 core task 82개의 JSON 정의.
- `data/primitives/` - task step에서 참조하는 primitive skill 정의.
- `data/task_catalog_core.json` - catalog index.
- `data/primitive_templates.json` - 원본 primitive template의 정규화 map.
- `docs/tasks_reference.md` - 82개 task별 목적, 입력, capability, resource, primitive sequence를 정리한 reference.
- `docs/primitives_reference.md` - 64개 primitive별 설명과 어떤 task에서 쓰이는지 정리한 reference.
- `assets/worker_processed/` - ManSim에서 복사한 임시 2-frame task animation placeholder.
- `examples/manufacturing_sequence.json` - humanoid task sequence 예제.
- `outputs/task_sequence_viewer.html` - 생성된 검증 및 animation viewer.

## Reference 문서

Task와 Primitive를 빠르게 훑어볼 때는 아래 문서를 먼저 보면 됩니다.

- [Task Reference](docs/tasks_reference.md): 전체 82개 task를 level, category, primitive sequence와 함께 표로 정리했습니다.
- [Primitive Reference](docs/primitives_reference.md): 전체 64개 primitive skill과 각 primitive를 사용하는 task 목록을 표로 정리했습니다.

## Task 개수와 분류

현재 catalog에는 총 `82`개의 제조 core task가 포함되어 있습니다. 이 task들은 13개 업무 영역으로 분류됩니다.

| Category ID | 분류 | Task 수 |
|---|---:|---:|
| A | Robot Readiness & Self-Operation | 8 |
| B | Mobility, Intralogistics & Material Flow | 5 |
| C | Machine Tending & Equipment Operation | 7 |
| D | Assembly, Fastening & Connection | 9 |
| E | Material Application, Dispensing & Sealing | 5 |
| F | Processing, Rework & Surface Treatment | 5 |
| G | Quality Inspection, Measurement & Testing | 7 |
| H | Maintenance, Repair & Calibration | 7 |
| I | Cleaning, 5S, EHS & Safety Patrol | 6 |
| J | Packaging, Unitization & Shipping | 5 |
| K | Warehouse, Inventory & Material Control | 6 |
| L | MES, Traceability & Digital Operations | 6 |
| M | Human Collaboration & Operator Assistance | 6 |

Task level 기준으로는 `Atomic Task` 50개, `Composite Task` 32개입니다. 이 task들이 참조하는 `Primitive Skill`은 현재 64개가 생성되어 있습니다.

## 휴머노이드를 위한 Task 분류체계

HumanoidSim은 task를 세 계층으로 다룹니다.

- `Primitive Skill`
  - planner나 execution engine이 호출하는 최소 의미 단위입니다.
  - 예: `NAVIGATE_TO`, `LOCALIZE_OBJECT`, `GRASP`, `PLACE`, `VERIFY_PLACEMENT`.
  - child step을 가지지 않습니다.
- `Atomic Task`
  - primitive skill들의 조합으로 구성된 단일 작업 단위입니다.
  - 예: `TRANSFER`, `LOAD_MACHINE`, `INSPECT_PRODUCT`, `FASTEN_COMPONENT`.
  - child step은 primitive skill만 호출해야 합니다.
- `Composite Task`
  - primitive, atomic, 다른 composite task를 조합할 수 있는 workflow입니다.
  - 예: `REPLENISH_MATERIAL`, `SETUP_MACHINE`, `REPAIR_MACHINE`, `FETCH_FOR_OPERATOR`.
  - 복합 제조 job이나 운영 절차를 표현합니다.

## Task Level 판정 기준

`Atomic Task`와 `Composite Task`는 primitive 개수로 구분하지 않습니다. 핵심 기준은 task가 표현하는 작업 의미의 범위와 실행 중 workflow 성격입니다.

| Level | 판정 기준 | 대표 신호 | 예시 |
|---|---|---|---|
| `ATOMIC_TASK` | 하나의 명확한 목표를 가진 단일 작업 단위 | 입력과 결과가 비교적 직접적이며, 실행 흐름이 큰 정책 분기 없이 primitive sequence로 닫힘 | `TRANSFER`, `LOAD_MACHINE`, `INSPECT_PRODUCT`, `FASTEN_COMPONENT` |
| `COMPOSITE_TASK` | 여러 작업, 절차, 정책 판단, 시스템 update, 에스컬레이션을 묶은 운영 workflow | 조건에 따라 세부 절차가 달라지거나, 여러 resource/location/system을 조합하거나, 하위 atomic task로 분해 가능 | `REPLENISH_MATERIAL`, `SETUP_MACHINE`, `REPAIR_MACHINE`, `RECOVER_FROM_FAULT` |

따라서 primitive sequence가 짧아도 workflow 성격이 강하면 `COMPOSITE_TASK`가 될 수 있습니다. 예를 들어 `RECOVER_FROM_FAULT`는 현재 `CHECK_CONTEXT -> EXECUTE_SYSTEM_ACTION -> VERIFY_ROBOT_STATE -> LOG_RESULT`로 표현되지만, fault code와 policy에 따라 자동 복구, 실패 처리, assistance 요청, 안전 절차가 달라질 수 있으므로 composite로 분류합니다. 반대로 primitive가 여러 개여도 목표가 좁고 실행 의미가 단일하면 atomic으로 유지합니다.

## Task 커스텀 방법

기본 82개 task는 Excel의 `Primitive Template ID`를 바탕으로 template-based step decomposition을 사용합니다. 특정 현장이나 ManSim 시나리오에 맞게 task를 커스텀하려면 아래 순서를 권장합니다.

1. `data/tasks/<task_no>_<TASK_CODE>.json`에서 커스텀할 task를 찾습니다.
2. task code는 유지합니다. 예를 들어 `TRANSFER`는 그대로 두고 `steps`, `required_tools`, `required_equipment`, `metadata.animation`만 조정합니다.
3. 새 primitive가 필요하면 `data/primitives/<NEW_PRIMITIVE>.json`을 추가하고, task step의 `call_code`에서 참조합니다.
4. `metadata.catalog.customization_notes`에 변경 이유를 남깁니다.
5. animation을 바꾸려면 `metadata.animation.frames`에 2개의 frame 경로를 넣습니다.
6. 변경 후 반드시 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-catalog
.\.venv\Scripts\python.exe -m humanoidsim validate-sequence examples\manufacturing_sequence.json
```

## Traffic Reason Codes

ManSim 같은 runtime은 이동 중 발생하는 traffic incident를 State나 Task로 새로 정의하지 않고,
`HumanoidStateSnapshot.reason.code`로 연결합니다. v0.1에서 표준으로 사용하는 reason code는 아래와 같습니다.

| Reason code | 의미 |
|---|---|
| `path_overlap` | 두 worker의 planned path가 같은 tile 또는 edge를 공유함 |
| `tile_conflict` | 같은 시간 구간에 같은 tile에 진입하거나 점유함 |
| `edge_conflict` | 같은 edge를 반대 방향으로 동시에 통과함 |
| `near_miss` | traffic headway 기준보다 짧은 간격으로 지나감 |
| `collision` | tile/edge conflict가 실제 이동 구간에서 겹침 |
| `traffic_wait` | traffic policy 또는 reservation 때문에 이동을 대기함 |

이 reason code들은 `data/state_schema_core.json`의 `standard_reason_codes`에도 정의되어 있습니다.
새로운 traffic 상황을 추가할 때는 enum을 늘리기보다 먼저 reason code를 추가하고, runtime event와 Replay/KPI가 그 code를 읽도록 연결합니다.

Excel 원본에서 전체 catalog를 다시 생성하려면 `scripts/generate_catalog.py`를 실행합니다. 단, 이 작업은 `data/tasks/`와 `data/primitives/`의 생성 파일을 다시 쓰므로, 수동 커스텀을 유지하려면 별도 override layer를 두는 편이 안전합니다.

## 명령어

워크스페이스 전용 가상환경을 활성화합니다.

```powershell
cd C:\Github\HumanoidSim
.\.venv\Scripts\Activate.ps1
```

editable package로 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e C:\Github\HumanoidSim
```

Excel workbook에서 catalog를 다시 생성합니다.

```powershell
.\.venv\Scripts\python.exe scripts\generate_catalog.py
```

catalog를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-catalog
```

task sequence를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-sequence examples\manufacturing_sequence.json
```

정적 HTML viewer를 생성합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim export-viewer examples\manufacturing_sequence.json --out outputs\task_sequence_viewer.html
```

ManSim에서 가져와 쓰려면 ManSim 가상환경에 editable package로 설치합니다.

```powershell
cd C:\Github\ManSim
.\.venv\Scripts\python.exe -m pip install -e C:\Github\HumanoidSim
```

## 설계 메모

- `v0.1`의 82개 core task는 template 기반 decomposition을 사용합니다.
- task code는 유지한 채, 나중에 task별 step override로 세부 동작을 정교화할 수 있습니다.
- animation metadata는 임시로 ManSim worker frame을 사용하며, 이후 task별 humanoid 이미지로 교체할 예정입니다.
- 나중에 ManSim과 통합할 때도 현재 simulation state가 우선이며, HumanoidSim catalog는 task 정의와 검증 기준으로 사용합니다.
