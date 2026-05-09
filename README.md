# Humanoid_Tasks_v0.1

Humanoid_Tasks는 제조 환경의 휴머노이드 에이전트를 위한 독립 task 정의 및 검증 라이브러리입니다.  

![Humanoid_Tasks overview](assets/IMG.png)



## 구성

- `src/humanoids/task_schema.py` - `TaskSpec`, `TaskInstance`, resource, validation을 위한 public dataclass schema.
- `src/humanoids/catalog.py` - task catalog loader와 registry 구성.
- `src/humanoids/execution.py` - `HumanoidProfile`, sequence validation, timeline simulation.
- `src/humanoids/viewer.py` - task sequence와 animation을 확인하는 정적 HTML viewer 생성.
- `data/tasks/` - 제조 core task 82개의 JSON 정의.
- `data/primitives/` - task step에서 참조하는 primitive skill 정의.
- `data/task_catalog_core.json` - catalog index.
- `data/primitive_templates.json` - 원본 primitive template의 정규화 map.
- `assets/worker_processed/` - ManSim에서 복사한 임시 2-frame task animation placeholder.
- `examples/manufacturing_sequence.json` - humanoid task sequence 예제.
- `outputs/task_sequence_viewer.html` - 생성된 검증 및 animation viewer.

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

Humanoid_Tasks는 task를 세 계층으로 다룹니다.

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

## Task 커스텀 방법

기본 82개 task는 Excel의 `Primitive Template ID`를 바탕으로 template-based step decomposition을 사용합니다. 특정 현장이나 ManSim 시나리오에 맞게 task를 커스텀하려면 아래 순서를 권장합니다.

1. `data/tasks/<task_no>_<TASK_CODE>.json`에서 커스텀할 task를 찾습니다.
2. task code는 유지합니다. 예를 들어 `TRANSFER`는 그대로 두고 `steps`, `required_tools`, `required_equipment`, `metadata.animation`만 조정합니다.
3. 새 primitive가 필요하면 `data/primitives/<NEW_PRIMITIVE>.json`을 추가하고, task step의 `call_code`에서 참조합니다.
4. `metadata.catalog.customization_notes`에 변경 이유를 남깁니다.
5. animation을 바꾸려면 `metadata.animation.frames`에 2개의 frame 경로를 넣습니다.
6. 변경 후 반드시 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoids validate-catalog
.\.venv\Scripts\python.exe -m humanoids validate-sequence examples\manufacturing_sequence.json
```

Excel 원본에서 전체 catalog를 다시 생성하려면 `scripts/generate_catalog.py`를 실행합니다. 단, 이 작업은 `data/tasks/`와 `data/primitives/`의 생성 파일을 다시 쓰므로, 수동 커스텀을 유지하려면 별도 override layer를 두는 편이 안전합니다.

## 명령어

워크스페이스 전용 가상환경을 활성화합니다.

```powershell
cd C:\Github\Humanoid_Tasks
.\.venv\Scripts\Activate.ps1
```

editable package로 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e C:\Github\Humanoid_Tasks
```

Excel workbook에서 catalog를 다시 생성합니다.

```powershell
.\.venv\Scripts\python.exe scripts\generate_catalog.py
```

catalog를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoids validate-catalog
```

task sequence를 검증합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoids validate-sequence examples\manufacturing_sequence.json
```

정적 HTML viewer를 생성합니다.

```powershell
.\.venv\Scripts\python.exe -m humanoids export-viewer examples\manufacturing_sequence.json --out outputs\task_sequence_viewer.html
```

ManSim에서 가져와 쓰려면 ManSim 가상환경에 editable package로 설치합니다.

```powershell
cd C:\Github\ManSim
.\.venv\Scripts\python.exe -m pip install -e C:\Github\Humanoid_Tasks
```

## 설계 메모

- `v0.1`의 82개 core task는 template 기반 decomposition을 사용합니다.
- task code는 유지한 채, 나중에 task별 step override로 세부 동작을 정교화할 수 있습니다.
- animation metadata는 임시로 ManSim worker frame을 사용하며, 이후 task별 humanoid 이미지로 교체할 예정입니다.
- 나중에 ManSim과 통합할 때도 현재 simulation state가 우선이며, Humanoid_Tasks catalog는 task 정의와 검증 기준으로 사용합니다.
