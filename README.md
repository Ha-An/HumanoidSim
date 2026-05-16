# HumanoidSim_v0.1

HumanoidSim은 제조 환경의 휴머노이드 에이전트를 위한 독립 task, primitive, state 정의 및 검증 라이브러리입니다.

![HumanoidSim overview](assets/IMG.png)

## 핵심 역할

HumanoidSim은 휴머노이드가 수행할 수 있는 일을 `TaskSpec`으로 정의하고, task를 이루는 실행 단계를 `StepCall`과 `Primitive Skill`로 정의합니다. ManSim 같은 시뮬레이션 runtime은 이 정의를 import해서 특정 공장 layout과 시나리오에서 실제로 어떤 일이 벌어지는지 관찰합니다.

현재 버전은 `v0.1`이며, 제조 core task 82개와 primitive skill 59개를 포함합니다.

## Task 구조

HumanoidSim의 task hierarchy는 세 단계입니다.

| Level | 의미 | 구조 규칙 |
| --- | --- | --- |
| `PRIMITIVE_SKILL` | 더 이상 쪼개지지 않는 최소 실행 skill | child step을 갖지 않습니다. |
| `ATOMIC_TASK` | primitive skill만으로 구성된 재사용 가능한 단일 task | 모든 `StepCall.call_code`가 primitive를 참조해야 합니다. |
| `COMPOSITE_TASK` | 하위 task를 직접 포함하는 workflow | 반드시 최소 1개 이상의 child task call을 포함해야 합니다. orchestration용 primitive step을 함께 가질 수 있습니다. |

중요한 점은 `COMPOSITE_TASK`가 단순히 긴 primitive sequence가 아니라는 것입니다. 예를 들어 `REPLENISH_MATERIAL`은 `CHECK_REQUEST -> PRIMITIVE_IDENTIFY_ITEM -> TRANSFER -> VERIFY_LEVEL_OR_QUANTITY -> UPDATE_RECORD` 구조이고, 여기서 `TRANSFER`는 primitive가 아니라 `ATOMIC_TASK` child call입니다.

`StepCall.call_code`는 primitive code뿐 아니라 task code도 참조할 수 있습니다. 이때 `expected_level`은 필수이며 `PRIMITIVE_SKILL`, `ATOMIC_TASK`, `COMPOSITE_TASK` 중 하나로 실제 참조 대상의 level과 일치해야 합니다.

## Task 분류

82개 task는 13개 제조 운영 category로 분류됩니다.

| ID | Category | Count |
| --- | --- | ---: |
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

Level 기준으로는 `ATOMIC_TASK` 50개, `COMPOSITE_TASK` 32개입니다.

## Public API

대표 API는 다음과 같습니다.

```python
from humanoidsim import (
    HumanoidProfile,
    load_task_catalog,
    validate_task_sequence,
    simulate_task_sequence,
    expand_task_steps,
)
```

`expand_task_steps(task_code, args, catalog=...)`는 nested composite task를 펼쳐서 parent task, child task, primitive leaf를 모두 포함한 plan row를 반환합니다. 각 row에는 `path`, `depth`, `parent_task_code`, `call_code`, `call_level`, `step_id`, `args`, `depends_on`이 들어갑니다.

## Humanoid State Model

Task와 State는 분리됩니다.

| 개념 | 의미 |
| --- | --- |
| Task | 휴머노이드가 달성해야 하는 목표 작업입니다. 예: `TRANSFER`, `INSPECT_PRODUCT`, `REPLENISH_MATERIAL` |
| Primitive | Task를 이루는 실행 단계입니다. 예: `NAVIGATE_TO`, `GRASP`, `PLACE` |
| State | 특정 시점의 휴머노이드 운용 상태입니다. 예: `availability=EXECUTING`, `mobility=NAVIGATING` |

State는 네 축으로 정의됩니다.

| 축 | 상태 |
| --- | --- |
| Availability | `AVAILABLE`, `ASSIGNED`, `EXECUTING`, `WAITING`, `BLOCKED`, `OFFLINE`, `DISABLED` |
| Mobility | `STATIONARY`, `NAVIGATING`, `DOCKING` |
| Power | `POWER_NORMAL`, `POWER_LOW`, `POWER_CRITICAL`, `DEPLETED`, `CHARGING` |
| Manipulation | `FREE`, `REACHING`, `HOLDING`, `PLACING` |

예시 snapshot:

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
    "step_id": "s03_execute_quality_action",
    "primitive_call_code": "EXECUTE_QUALITY_ACTION",
    "execution_status": "RUNNING"
  }
}
```

## 구성

- `src/humanoidsim/task_schema.py`: task, step, resource, registry validation schema
- `src/humanoidsim/state_schema.py`: humanoid state enum, snapshot, primitive state hint
- `src/humanoidsim/catalog.py`: task catalog loader
- `src/humanoidsim/execution.py`: profile validation, nested expansion, sequence simulation
- `src/humanoidsim/viewer.py`: task sequence HTML viewer export
- `data/tasks/`: 82개 core task JSON
- `data/primitives/`: primitive skill JSON
- `data/task_catalog_core.json`: catalog index
- `data/primitive_templates.json`: Excel primitive template 기록
- `docs/tasks_reference.md`: task 전체 reference
- `docs/primitives_reference.md`: task step에서 실제 참조되는 active primitive reference

## Reference

- [Task Reference](docs/tasks_reference.md): 82개 task의 level, category, input, resource, nested sequence를 정리합니다.
- [Primitive Reference](docs/primitives_reference.md): task step에서 실제 참조되는 primitive skill과 사용 task를 정리합니다.

## 실행

가상환경을 활성화합니다.

```powershell
cd C:\Github\HumanoidSim
.\.venv\Scripts\Activate.ps1
```

editable package로 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e C:\Github\HumanoidSim
```

catalog를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-catalog
```

예제 sequence를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim validate-sequence examples\manufacturing_sequence.json
```

HTML viewer를 생성합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoidsim export-viewer examples\manufacturing_sequence.json --out outputs\task_sequence_viewer.html
```

Excel workbook에서 catalog를 다시 생성합니다.

```powershell
.\.venv\Scripts\python.exe scripts\generate_catalog.py
```

## Task 커스터마이즈

1. `data/tasks/<task_no>_<TASK_CODE>.json`에서 수정할 task를 찾습니다.
2. 기존 task code는 유지하고 `steps`, resource, animation metadata를 조정합니다.
3. Composite task를 만들 때는 최소 하나의 child task call을 포함합니다.
4. Child task step에는 `expected_level`을 반드시 지정합니다.
5. 새로운 primitive가 필요하면 `data/primitives/<NEW_PRIMITIVE>.json`을 추가하고 task step에서 참조합니다.
6. 변경 후 `validate-catalog`와 `validate-sequence`를 실행합니다.

생성 스크립트를 다시 실행하면 `data/tasks/`와 `data/primitives/`가 재생성됩니다. 장기적으로 유지할 task별 override는 `scripts/generate_catalog.py`의 composite override map에 반영하는 방식을 권장합니다.
