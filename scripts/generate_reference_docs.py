from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "data" / "tasks"
PRIMITIVES = ROOT / "data" / "primitives"
DOCS = ROOT / "docs"

CATEGORY_DESCRIPTIONS = {
    "A": "로봇 초기화, 자가 점검, 운용 모드, 작업 context, 전원 관리, fault recovery처럼 휴머노이드 자체 운용 준비를 다룹니다.",
    "B": "자재와 WIP의 이동, 보충, 제거, transfer interface, 차량 기반 운반처럼 라인 내부 물류 흐름을 다룹니다.",
    "C": "설비 setup, load/unload, HMI 조작, cycle 제어, configuration 변경, recoverable fault 처리를 다룹니다.",
    "D": "부품 조립/분해, 삽입/제거, 체결/해체, 전기/유체/기계 연결과 flexible component routing을 다룹니다.",
    "E": "표면 준비, 접착제/실란트/코팅 도포, 도포물 제거, 경화, 도포 상태 검증을 다룹니다.",
    "F": "절단, 트리밍, feature 생성, burr/flash 제거, 표면 마감, 부품 marking 같은 가공과 재작업을 다룹니다.",
    "G": "제품 검사, feature 측정, item 식별, 조립 검증, 기능 test, 품질 결과 기록과 분류를 다룹니다.",
    "H": "예방정비, 설비 점검/진단/수리, 부품 교체, fluid/lubrication service, 설비 calibration을 다룹니다.",
    "I": "작업 구역과 asset 청소, 폐기물/스크랩 수거, spill 대응, EHS/5S audit, hazard report를 다룹니다.",
    "J": "제품 포장/개봉, 라벨링, 포장 검증, palletizing/wrapping/strapping 같은 출하 준비를 다룹니다.",
    "K": "입고, putaway, picking, 재고 count/audit, kit 구성, inventory record 갱신을 다룹니다.",
    "L": "work order 시작/완료, operation 결과 보고, traceability 등록, exception report, evidence/status capture를 다룹니다.",
    "M": "operator 요청 fetch, item/tool handover, operator로부터 수령, 작업 중 지지/정렬, lifting/move 보조를 다룹니다.",
}

TASK_DESCRIPTIONS = {
    "A": "휴머노이드 자체 운용 준비와 복구를 위한 task입니다.",
    "B": "자재, WIP, 제품을 위치 사이에서 이동하거나 물류 상태를 바꾸는 task입니다.",
    "C": "설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.",
    "D": "부품을 조립, 분해, 체결, 연결하는 task입니다.",
    "E": "접착제, 실란트, 코팅 등 재료를 표면에 적용하거나 검증하는 task입니다.",
    "F": "부품의 형상, 표면, 마킹을 가공하거나 재작업하는 task입니다.",
    "G": "품질 검사, 측정, test, 결과 기록과 분류를 수행하는 task입니다.",
    "H": "설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.",
    "I": "청소, EHS, 5S, hazard 대응을 수행하는 task입니다.",
    "J": "포장, 라벨링, unitization, 출하 준비를 수행하는 task입니다.",
    "K": "창고, 재고, picking, putaway, kit 구성과 record 갱신을 수행하는 task입니다.",
    "L": "MES, traceability, work order, evidence 기록을 수행하는 digital task입니다.",
    "M": "operator 또는 다른 휴머노이드와의 handover, 수령, 보조를 수행하는 협업 task입니다.",
}

PRIMITIVE_DESCRIPTIONS = {
    "NAVIGATE_TO": "목표 위치까지 이동합니다.",
    "LOCALIZE_OBJECT": "대상 객체의 위치와 식별 정보를 확인합니다.",
    "PRIMITIVE_IDENTIFY_ITEM": "대상 item을 식별합니다.",
    "REACH_TO": "대상 item이나 tool에 팔 또는 그리퍼를 접근시킵니다.",
    "GRASP": "대상 item이나 tool을 잡습니다.",
    "LIFT": "잡은 대상을 들어 운반 가능한 상태로 만듭니다.",
    "PLACE": "운반한 대상을 목표 위치에 내려놓습니다.",
    "RELEASE": "잡고 있던 대상을 놓습니다.",
    "VERIFY_PLACEMENT": "대상이 올바른 위치에 놓였는지 확인합니다.",
    "CHECK_REQUEST": "보충, 제거, fetch 같은 요청의 유효성과 내용을 확인합니다.",
    "VERIFY_LEVEL_OR_QUANTITY": "보충량, 제거량, 재고 수량이 기준에 맞는지 확인합니다.",
    "UPDATE_RECORD": "작업 결과나 재고 상태를 기록합니다.",
    "CHECK_SAFETY_ZONE": "작업 구역의 안전 조건과 접근 가능 여부를 확인합니다.",
    "READ_MACHINE_STATE": "설비의 현재 상태와 작업 가능 여부를 읽습니다.",
    "VERIFY_MACHINE_STATE": "설비 상태가 목표 조건에 도달했는지 확인합니다.",
    "EXECUTE_MACHINE_ACTION": "설비 setup, load, unload, cycle 제어 같은 machine action을 수행합니다.",
    "EXECUTE_MAINTENANCE_ACTION": "점검, 진단, 수리, 교체, calibration 같은 maintenance action을 수행합니다.",
    "EXECUTE_QUALITY_ACTION": "검사, 측정, test 같은 quality action을 수행합니다.",
    "EXECUTE_HUMAN_COLLABORATION_ACTION": "handover, 수령, 보조 같은 사람 또는 다른 로봇과의 협업 action을 수행합니다.",
    "ANNOUNCE_INTENT": "handover나 협업 전에 의도와 다음 행동을 알립니다.",
    "CONFIRM_OPERATOR_STATE": "operator 또는 협업 대상의 준비 상태와 안전 상태를 확인합니다.",
    "CREATE_OR_UPDATE_RECORD": "업무 결과, 품질, 재고, 예외 record를 생성하거나 갱신합니다.",
    "EXECUTE_SYSTEM_ACTION": "로봇 초기화, mode 변경, 충전, recovery 같은 system action을 수행합니다.",
    "EXECUTE_WAREHOUSE_ACTION": "입고, putaway, picking, counting, kitting 같은 warehouse action을 수행합니다.",
}


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    tasks = [_read_json(path) | {"_path": path} for path in sorted(TASKS.glob("*.json"))]
    primitives = [_read_json(path) | {"_path": path} for path in sorted(PRIMITIVES.glob("*.json"))]
    _write_tasks_reference(tasks)
    _write_primitives_reference(tasks, primitives)
    return 0


def _write_tasks_reference(tasks: list[dict[str, Any]]) -> None:
    level_counts = Counter(task["level"] for task in tasks)
    category_counts = Counter(_catalog(task).get("category_id", "?") for task in tasks)

    lines = [
        "# Task Reference",
        "",
        "이 문서는 `data/tasks/*.json`에 정의된 HumanoidSim core task 82개를 사람이 읽기 쉽게 정리한 reference입니다. JSON 파일이 원본이고, 이 문서는 탐색과 검토를 위한 요약입니다.",
        "",
        "## 요약",
        "",
        f"- Task 수: {len(tasks)}",
        "- 원본 task 정의: `data/tasks/*.json`",
        "- 통합 index: `data/task_catalog_core.json`",
        "- Primitive template index: `data/primitive_templates.json`",
        "",
        "### Level별 개수",
        "",
        "| Level | Count |",
        "| --- | ---: |",
    ]
    for level in ("ATOMIC_TASK", "COMPOSITE_TASK"):
        lines.append(f"| `{level}` | {level_counts[level]} |")

    lines += [
        "",
        "### Task Level 기준",
        "",
        "HumanoidSim v0.1에서 task level은 실행 workflow의 구조로 구분합니다. Primitive 개수나 step 길이가 아니라, step이 어떤 수준의 call을 참조하는지가 기준입니다.",
        "",
        "| Level | 기준 | 예시 |",
        "| --- | --- | --- |",
        "| `PRIMITIVE_SKILL` | 더 이상 하위 step을 갖지 않는 최소 실행 skill입니다. | `NAVIGATE_TO`, `GRASP`, `VERIFY_PLACEMENT` |",
        "| `ATOMIC_TASK` | 하위 step이 모두 `PRIMITIVE_SKILL`인 재사용 가능한 단일 task입니다. | `TRANSFER`, `LOAD_MACHINE`, `INSPECT_PRODUCT` |",
        "| `COMPOSITE_TASK` | 반드시 최소 1개 이상의 child task call을 포함하는 workflow입니다. child는 `ATOMIC_TASK` 또는 다른 `COMPOSITE_TASK`일 수 있고, orchestration용 primitive step을 함께 가질 수 있습니다. | `REPLENISH_MATERIAL -> TRANSFER`, `SETUP_MACHINE -> LOAD_MACHINE` |",
        "",
        "`StepCall.call_code`는 primitive code뿐 아니라 task code도 참조할 수 있습니다. 이때 `expected_level`은 필수이며, nested task step에서는 `ATOMIC_TASK` 또는 `COMPOSITE_TASK`로 명시됩니다.",
        "",
        "### Category 설명",
        "",
        "| ID | Category | Count | 설명 |",
        "| --- | --- | ---: | --- |",
    ]
    for category_id in sorted(category_counts):
        category_name = next(_catalog(task).get("category", "") for task in tasks if _catalog(task).get("category_id") == category_id)
        lines.append(f"| {category_id} | {_escape(category_name)} | {category_counts[category_id]} | {CATEGORY_DESCRIPTIONS.get(category_id, '')} |")

    lines += [
        "",
        "## 전체 Task 표",
        "",
        "| No | Code | Level | Description | Inputs | Capabilities | Resources | Risk | Step / Nested Sequence | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for task in tasks:
        catalog = _catalog(task)
        category_id = catalog.get("category_id", "?")
        source = task["_path"].relative_to(ROOT).as_posix()
        lines.append(
            f"| {catalog.get('task_no', '')} | `{task['code']}` | `{task['level']}` | "
            f"{TASK_DESCRIPTIONS.get(category_id, '제조 현장에서 사용하는 휴머노이드 task입니다.')} | "
            f"{_inputs(task)} | {_capabilities(task)} | {_resources(task)} | "
            f"{task.get('safety', {}).get('risk_level', 'LOW')} | {_sequence(task)} | `{source}` |"
        )

    (DOCS / "tasks_reference.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_primitives_reference(tasks: list[dict[str, Any]], primitives: list[dict[str, Any]]) -> None:
    used_by: dict[str, set[str]] = defaultdict(set)
    for task in tasks:
        for step in task.get("steps", []):
            if step.get("expected_level") == "PRIMITIVE_SKILL":
                used_by[step.get("call_code", "")].add(task["code"])
    active_primitives = [primitive for primitive in primitives if used_by.get(primitive["code"])]

    lines = [
        "# Primitive Reference",
        "",
        "이 문서는 task step에서 실제로 참조되는 active primitive skill을 정리한 reference입니다. Primitive는 task를 구성하는 가장 작은 실행 skill이며, `ATOMIC_TASK`와 `COMPOSITE_TASK`의 step에서 참조됩니다.",
        "",
        "## 요약",
        "",
        f"- Active primitive 수: {len(active_primitives)}",
        f"- Registry primitive 수: {len(primitives)}",
        "- 원본 primitive 정의: `data/primitives/*.json`",
        "- Primitive template index: `data/primitive_templates.json`",
        "- 이 표에는 현재 task catalog의 `steps`에서 참조되는 primitive만 표시합니다.",
        "",
        "## 용어",
        "",
        "| 용어 | 의미 | 기준 파일/필드 | 사용 목적 |",
        "| --- | --- | --- | --- |",
        "| Active primitive | 현재 task catalog의 `steps`에서 `expected_level=PRIMITIVE_SKILL`로 직접 참조되는 primitive입니다. 실제 task sequence를 펼쳤을 때 실행 leaf step으로 등장할 수 있습니다. | `data/tasks/*.json`의 `steps[].call_code` | task reference, 실행 coverage, ManSim primitive 지원 범위 확인 |",
        "| Registry primitive | HumanoidSim primitive registry에 등록된 전체 primitive 정의입니다. 현재 task가 사용하지 않더라도, 향후 task에서 참조하거나 확장하기 위해 존재할 수 있습니다. | `data/primitives/*.json`, `data/task_catalog_core.json`의 primitive entry | schema validation, hierarchy validation, custom task 확장 |",
        "",
        "현재 v0.1 catalog에서는 active primitive와 registry primitive가 모두 59개라 숫자가 같습니다. 하지만 개념적으로는 `active primitive ⊆ registry primitive`입니다. 새 primitive JSON만 추가하고 task step에서 아직 참조하지 않으면 registry primitive에는 포함되지만 active primitive 표에는 나타나지 않습니다.",
        "",
        "ManSim 같은 실행 환경은 active primitive 중 자신이 실제로 지원하는 subset을 primitive executor에 연결합니다. 따라서 HumanoidSim registry에 있다는 것은 schema상 정의되어 있다는 뜻이고, 특정 runtime에서 반드시 실행 가능하다는 뜻은 아닙니다.",
        "",
        "## Active Primitive 표",
        "",
        "| Code | Name | Description | Inputs | Outputs | Used by Tasks | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for primitive in active_primitives:
        code = primitive["code"]
        description = PRIMITIVE_DESCRIPTIONS.get(code, f"`{code}` 실행 단계를 나타내는 primitive skill입니다.")
        source = primitive["_path"].relative_to(ROOT).as_posix()
        outputs = "<br>".join(f"{row['name']}: {row.get('type_hint', 'Any')}" for row in primitive.get("outputs", [])) or "-"
        users = "<br>".join(f"`{code}`" for code in sorted(used_by.get(code, []))) or "-"
        lines.append(f"| `{code}` | {_escape(primitive.get('name', ''))} | {description} | {_inputs(primitive)} | {outputs} | {users} | `{source}` |")

    (DOCS / "primitives_reference.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog(task: dict[str, Any]) -> dict[str, Any]:
    return task.get("metadata", {}).get("catalog", {})


def _inputs(spec: dict[str, Any]) -> str:
    rows = []
    for item in spec.get("inputs", []):
        mark = "*" if item.get("required", True) else ""
        rows.append(f"{item['name']}{mark}: {_escape(item.get('type_hint', 'Any'))}")
    return "<br>".join(rows) or "-"


def _capabilities(task: dict[str, Any]) -> str:
    return "<br>".join(_escape(item) for item in task.get("required_capabilities", [])) or "-"


def _resources(task: dict[str, Any]) -> str:
    rows = []
    for label, key in (("tool", "required_tools"), ("vehicle", "required_vehicles"), ("equipment", "required_equipment")):
        for item in task.get(key, []):
            rows.append(f"{label}:{_escape(item.get('alias', ''))}")
    return "<br>".join(rows) or "-"


def _sequence(task: dict[str, Any]) -> str:
    rows = []
    for step in task.get("steps", []):
        call_code = step.get("call_code", "")
        level = step.get("expected_level", "")
        rows.append(f"{call_code} [{level}]" if level and level != "PRIMITIVE_SKILL" else call_code)
    return "<br>".join(rows) or "-"


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
