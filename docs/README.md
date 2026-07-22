# HumanoidSim Docs

이 디렉터리는 HumanoidSim의 task, primitive, state, incident와 standalone validation 도구를 설명합니다.

## Current Baseline

- Python package: `0.1.0`
- Core catalog: `0.2.0-core`
- Task: 87 (`ATOMIC_TASK` 56, `COMPOSITE_TASK` 31)
- Primitive: 61
- Incident: 35
- External runtime dependency: 없음
- ManSim integration: optional editable package import

## Reading Order

1. [tasks_reference.md](tasks_reference.md): task category, level, input, resource, nested sequence
2. [primitives_reference.md](primitives_reference.md): primitive group, difficulty weight, state relation, 사용 task
3. [state_reference.md](state_reference.md): Availability, Mobility, Power, Manipulation state와 transition
4. [incident_reference.md](incident_reference.md): incident taxonomy, state reason, recovery protocol
5. [validation_lab.md](validation_lab.md): batch validation, browser UI, RViz/Gazebo adapter

## Generated References

`tasks_reference.md`, `primitives_reference.md`, `incident_reference.md`는 catalog JSON에서 생성됩니다. 원본 정의를 수정한 뒤 생성 스크립트와 검증을 실행합니다.

```powershell
.\.venv\Scripts\python.exe scripts\generate_reference_docs.py
.\.venv\Scripts\python.exe -m humanoidsim validate-catalog
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

State reference는 `src/humanoidsim/state_schema.py`와 `data/state_schema_core.json`의 네 state 축 및 transition 규칙과 함께 유지합니다.

## Ownership Boundary

HumanoidSim은 로봇 행동 의미와 검증을 소유합니다. ManSim 같은 외부 simulator는 task instance 발생 조건과 domain side effect를 소유합니다. HumanoidSim의 Validation Lab, Browser 3D Viewer, ROS2/RViz/Gazebo adapter는 ManSim 없이 독립적으로 실행할 수 있습니다.
