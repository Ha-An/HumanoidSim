from __future__ import annotations

import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "data" / "tasks"
PRIMITIVES = ROOT / "data" / "primitives"
INCIDENT_SCHEMA = ROOT / "data" / "incident_schema_core.json"
DOCS = ROOT / "docs"


CATEGORY_DESCRIPTIONS = {
    "A": "휴머노이드 자체 운용 준비, 모드 설정, 작업 context 로딩, 전원 관리, fault recovery를 다룹니다.",
    "B": "자재, WIP, 완성품, tool을 위치 사이에서 이동하거나 물류 흐름을 조정하는 작업을 다룹니다.",
    "C": "설비 setup, load/unload, HMI 조작, cycle 제어, configuration 변경과 설비 fault 처리를 다룹니다.",
    "D": "부품 조립, 분해, 체결, 삽입, 제거, 연결 같은 assembly 작업을 다룹니다.",
    "E": "표면 준비, 도포, dispensing, sealing, 경화, 도포 상태 검증을 다룹니다.",
    "F": "절단, trimming, feature 생성, burr 제거, 표면 마감, marking 같은 가공과 rework를 다룹니다.",
    "G": "품질 검사, 측정, 기능 test, item 식별, 검사 결과 기록과 분류를 다룹니다.",
    "H": "예방정비, 설비 점검, 진단, 수리, 부품 교체, 윤활, calibration을 다룹니다.",
    "I": "작업 구역과 asset 청소, scrap 수거, spill 대응, EHS/5S audit, hazard report를 다룹니다.",
    "J": "제품 포장, 개봉, label, package 검증, palletizing, wrapping, shipping 준비를 다룹니다.",
    "K": "입고, putaway, picking, 재고 count/audit, kit 구성, inventory record 갱신을 다룹니다.",
    "L": "work order, operation result, traceability, exception report, evidence/status capture 같은 digital operation을 다룹니다.",
    "M": "operator 지원, item/tool handover, operator로부터 수령, 작업 중 지지/정렬, 공동 lifting/move를 다룹니다.",
    "S": "조선소 선박 section 또는 exterior surface tile의 용접, 표면처리, sealant 적용, 도장, 품질 확인 작업을 다룹니다.",
}


TASK_DESCRIPTIONS = {
    "A": "휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.",
    "B": "자재, WIP, 제품 또는 tool을 위치 사이에서 이동하고 물류 상태를 바꾸는 task입니다.",
    "C": "설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.",
    "D": "부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.",
    "E": "표면이나 대상물에 소재를 적용하거나 적용 상태를 검증하는 task입니다.",
    "F": "부품의 형상, 표면, marker를 가공하거나 rework하는 task입니다.",
    "G": "품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.",
    "H": "설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.",
    "I": "청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.",
    "J": "포장, label, unitization, shipping 준비를 수행하는 task입니다.",
    "K": "창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.",
    "L": "MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.",
    "M": "operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.",
    "S": "선박 section 또는 exterior surface tile을 대상으로 용접, 표면처리, sealant 적용, 도장, 품질 확인을 수행하는 shipyard task입니다.",
}


INCIDENT_DESCRIPTIONS = {
    "OBJECT_RECOGNITION_FAILED": "예상한 대상 물체를 인식하지 못한 상황입니다.",
    "POSE_ESTIMATION_FAILED": "대상은 보이지만 자세나 접근 방향을 추정하지 못한 상황입니다.",
    "LABEL_OR_MARKER_UNREADABLE": "barcode, QR, label, marker, serial, lot 정보 등을 읽지 못한 상황입니다.",
    "TARGET_NOT_FOUND": "계획된 위치에 있어야 할 대상이 현장에 없는 상황입니다.",
    "GRIP_FAILED": "gripper가 item이나 tool을 안정적으로 잡지 못한 상황입니다.",
    "LIFT_FAILED": "대상을 잡았지만 안전하게 들어 올리지 못한 상황입니다.",
    "ITEM_DROPPED": "운반 또는 조작 중 item을 떨어뜨린 상황입니다.",
    "ITEM_SLIPPED": "payload가 완전히 떨어지지는 않았지만 미끄러지거나 불안정해진 상황입니다.",
    "PLACEMENT_FAILED": "목표 위치에 item을 내려놓거나 release하는 데 실패한 상황입니다.",
    "PAYLOAD_OVER_LIMIT": "payload가 휴머노이드의 운반 한계를 초과한 상황입니다.",
    "RESOURCE_PREEMPTED": "예상한 resource를 다른 actor가 먼저 가져가거나 점유한 상황입니다.",
    "RESOURCE_MISSING": "필요한 item, tool, vehicle, equipment 또는 consumable이 없는 상황입니다.",
    "PATH_BLOCKED": "계획된 route를 따라 이동할 수 없을 만큼 경로가 막힌 상황입니다.",
    "WORKSPACE_OBSTRUCTED": "작업 공간이나 service tile이 막혀 task를 진행할 수 없는 상황입니다.",
    "SURFACE_OR_AREA_CONTAMINATED": "바닥, 표면, 작업대 또는 공유 구역이 오염되었거나 안전하지 않은 상황입니다.",
    "TRAFFIC_WAIT": "traffic policy 또는 reservation 때문에 이동을 잠시 기다리는 상황입니다.",
    "NEAR_MISS": "충돌에 가까운 tile 또는 edge 접근이 감지된 상황입니다.",
    "COLLISION": "tile 또는 edge 수준에서 실제 collision이 감지된 상황입니다.",
    "NAVIGATION_DRIFT": "실제 위치가 계획된 route나 예상 tile과 어긋난 상황입니다.",
    "DOCKING_FAILED": "충전기, 작업대, 설비 등 docking target에 정렬하지 못한 상황입니다.",
    "POWER_LOW_UNEXPECTED": "현재 계획보다 빠르게 배터리가 낮아진 상황입니다.",
    "POWER_INTERRUPTION": "전원 순간 장애로 안전한 task 실행이 어려운 상황입니다.",
    "DEPLETED": "배터리가 방전된 상황입니다.",
    "SENSOR_DEGRADED": "sensor 성능 저하로 task 신뢰도가 낮아진 상황입니다.",
    "TOOL_OR_END_EFFECTOR_FAULT": "tool 또는 end-effector 이상으로 안전한 manipulation이 어려운 상황입니다.",
    "ACTUATOR_FAULT": "joint 또는 actuator 이상으로 motion/manipulation이 어려운 상황입니다.",
    "COMMUNICATION_LOST": "controller 또는 외부 시스템과 통신이 일시적으로 끊긴 상황입니다.",
    "COMMAND_TIMEOUT": "명령이나 외부 operation이 제한 시간 안에 응답하지 않은 상황입니다.",
    "MAP_OR_CONTEXT_STALE": "활성 map, work context, task context가 오래되어 신뢰할 수 없는 상황입니다.",
    "RECORD_UPDATE_FAILED": "MES, WMS, log, evidence record 갱신에 실패한 상황입니다.",
    "SAFETY_STOP": "safety stop 또는 interlock이 발생해 운용이 멈춘 상황입니다.",
    "HUMAN_IN_WORK_ZONE": "사람이나 다른 actor가 active work zone에 들어온 상황입니다.",
    "HANDOVER_FAILED": "human/robot 또는 robot/robot handover를 안전하게 완료하지 못한 상황입니다.",
    "OPERATOR_NOT_READY": "operator 또는 협업 actor가 다음 interaction을 수행할 준비가 되지 않은 상황입니다.",
    "UNKNOWN": "원인을 충분히 특정할 수 없는 예외적 중단 상황입니다.",
}


CATEGORY_KO = {
    "perception_identification": "인식/식별",
    "manipulation_payload": "조작/적재",
    "resource_environment": "자원/환경",
    "motion_traffic": "이동/교통",
    "power_hardware": "전원/하드웨어",
    "system_communication": "시스템/통신",
    "safety_human_interaction": "안전/상호작용",
    "unknown": "원인 미상",
}


CATEGORY_DESCRIPTION_KO = {
    "perception_identification": "대상 탐지, 식별, 자세 추정, marker 판독, target 존재 여부와 관련된 incident입니다.",
    "manipulation_payload": "grip, lift, placement, payload 안정성, 운반 중 item 상태와 관련된 incident입니다.",
    "resource_environment": "자원 부재/선점, 막힌 경로, 작업 공간 장애물, 오염 또는 접근 불가 환경과 관련된 incident입니다.",
    "motion_traffic": "이동, traffic, docking, collision, route execution과 관련된 incident입니다.",
    "power_hardware": "배터리, 전원, sensor, actuator, tool, end-effector와 관련된 incident입니다.",
    "system_communication": "네트워크, command timeout, map/context, record 동기화와 관련된 incident입니다.",
    "safety_human_interaction": "safety stop, human/robot zone conflict, operator readiness, handover와 관련된 incident입니다.",
    "unknown": "원인을 충분히 특정할 수 없는 incident입니다.",
}

PRIMITIVE_GROUPS = [
    {
        "id": "P01",
        "name": "Mobility & Spatial Alignment",
        "scope": "이동, 경로 추종, 위치 보정, docking, 자세 정렬",
        "state": "`mobility=NAVIGATING` 또는 `DOCKING`",
        "primitives": ["ALIGN", "NAVIGATE_TO", "PARK_OR_RELEASE_VEHICLE"],
        "candidates": ["LOCALIZE_SELF", "FOLLOW_PATH_SEGMENT", "RECOVER_POSITION"],
    },
    {
        "id": "P02",
        "name": "Perception & Identification",
        "scope": "대상 탐지, 식별, marker/label 판독, pose 추정",
        "state": "대개 `STATIONARY`, 조작 state는 유지",
        "primitives": [
            "IDENTIFY_PRODUCT",
            "LOCALIZE_COMPONENTS",
            "LOCALIZE_OBJECT",
            "LOCALIZE_PART",
            "LOCALIZE_SURFACE",
            "PRIMITIVE_IDENTIFY_ITEM",
        ],
        "candidates": ["SCAN_ENVIRONMENT", "ESTIMATE_POSE", "READ_MARKER"],
    },
    {
        "id": "P03",
        "name": "Manipulation & Payload",
        "scope": "팔/그리퍼 접근, 파지, 들기, 놓기, payload 안정성 확인",
        "state": "`REACHING`, `HOLDING`, `PLACING`",
        "primitives": ["FIX_OR_HOLD_PART", "GRASP", "LIFT", "PLACE", "REACH_TO", "RELEASE"],
        "candidates": ["PLAN_GRASP", "MONITOR_FORCE", "CHECK_PAYLOAD_STABILITY"],
    },
    {
        "id": "P04",
        "name": "Safety & Interaction",
        "scope": "안전 구역 확인, 의도 알림, 협업 readiness 확인, clearance 요청",
        "state": "`WAITING` 또는 `EXECUTING` 중 safety reason과 연결 가능",
        "primitives": [
            "ANNOUNCE_INTENT",
            "CHECK_SAFETY_ZONE",
            "CONFIRM_OPERATOR_STATE",
            "EXECUTE_HUMAN_COLLABORATION_ACTION",
            "EXECUTE_ROBOT_COLLABORATION_ACTION",
            "SYNC_WITH_ROBOT",
            "VERIFY_AUTHORIZATION",
            "VERIFY_LOCKOUT_IF_REQUIRED",
        ],
        "candidates": ["REQUEST_CLEARANCE", "YIELD_TO_TRAFFIC", "WAIT_FOR_OPERATOR_READY"],
    },
    {
        "id": "P05",
        "name": "Equipment & Tool Operation",
        "scope": "설비, tool, dispenser, system action 실행",
        "state": "주로 `STATIONARY`, task context에 따라 manipulation 유지",
        "primitives": [
            "EXECUTE_ASSEMBLY_ACTION",
            "EXECUTE_EHS_ACTION",
            "EXECUTE_MACHINE_ACTION",
            "EXECUTE_PACKAGING_ACTION",
            "EXECUTE_SYSTEM_ACTION",
            "OPERATE_TOOL",
            "OPERATE_TOOL_OR_DISPENSER",
            "PREPARE_PACKAGING",
            "PRIMITIVE_APPLY_MATERIAL",
            "PRIMITIVE_PREPARE_SURFACE",
            "PROCESS_FEATURE_OR_SURFACE",
        ],
        "candidates": ["SELECT_TOOL", "CONFIGURE_TOOL", "CHANGE_TOOL_MODE"],
    },
    {
        "id": "P06",
        "name": "Verification & Quality",
        "scope": "상태, 배치, 품질, 수량, 결과 검증 및 분류",
        "state": "대개 `STATIONARY`, 결과에 따라 task branch 발생",
        "primitives": [
            "CLASSIFY_RESULT",
            "EXECUTE_QUALITY_ACTION",
            "INSPECT_AREA",
            "INSPECT_RESULT",
            "PRIMITIVE_VERIFY_ASSEMBLY",
            "PRIMITIVE_VERIFY_PACKAGE",
            "VERIFY_AREA_STATE",
            "VERIFY_COVERAGE_OR_AMOUNT",
            "VERIFY_MACHINE_STATE",
            "VERIFY_PLACEMENT",
        ],
        "candidates": ["COMPARE_MEASUREMENT", "VALIDATE_RESULT", "SAMPLE_SENSOR_READING"],
    },
    {
        "id": "P07",
        "name": "Records & Digital Context",
        "scope": "record 생성/갱신, traceability, map/context 동기화",
        "state": "물리 state 변화는 작고 context 갱신 중심",
        "primitives": [
            "CHECK_CONTEXT",
            "CREATE_OR_UPDATE_RECORD",
            "LOG_RESULT",
            "READ_CONTEXT",
            "RECORD_RESULT",
            "REPORT_RESULT",
            "UPDATE_RECORD",
            "VERIFY_TRANSACTION",
        ],
        "candidates": ["UPDATE_MAP_CONTEXT", "SYNC_WORK_CONTEXT", "CACHE_OBSERVATION"],
    },
    {
        "id": "P08",
        "name": "Recovery & Self-Maintenance",
        "scope": "self check, diagnostics, sensor calibration, fault containment",
        "state": "`BLOCKED` 또는 `DISABLED` 이후 recovery protocol에서 사용",
        "primitives": [
            "EXECUTE_MAINTENANCE_ACTION",
            "INSPECT_OR_DIAGNOSE",
            "READ_MACHINE_STATE",
            "VERIFY_ROBOT_STATE",
        ],
        "candidates": ["CALIBRATE_SENSOR", "RECOVER_BALANCE", "RUN_DIAGNOSTIC_PROBE"],
    },
    {
        "id": "P09",
        "name": "Resource & Inventory Interface",
        "scope": "요청 확인, 재고 수량 검증, warehouse/resource action",
        "state": "resource incident와 연결되기 쉬움",
        "primitives": [
            "CHECK_REQUEST",
            "EXECUTE_WAREHOUSE_ACTION",
            "PRIMITIVE_UPDATE_INVENTORY_RECORD",
            "VERIFY_LEVEL_OR_QUANTITY",
            "VERIFY_RECORD",
        ],
        "candidates": ["RESERVE_RESOURCE", "RELEASE_RESOURCE", "REFRESH_INVENTORY_VIEW"],
    },
]

PRIMITIVE_TO_GROUP = {
    primitive_code: group["id"]
    for group in PRIMITIVE_GROUPS
    for primitive_code in group["primitives"]
}


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    tasks = [_read_json(path) | {"_path": path} for path in sorted(TASKS.glob("*.json"))]
    primitives = [_read_json(path) | {"_path": path} for path in sorted(PRIMITIVES.glob("*.json"))]
    incident_schema = _read_json(INCIDENT_SCHEMA)
    _write_tasks_reference(tasks)
    _write_primitives_reference(tasks, primitives)
    _write_incident_reference(incident_schema)
    return 0


def _write_tasks_reference(tasks: list[dict[str, Any]]) -> None:
    level_counts = Counter(task["level"] for task in tasks)
    category_counts = Counter(_catalog(task).get("category_id", "?") for task in tasks)

    lines = [
        "# Task Reference",
        "",
        "## Inspection Interface 계약",
        "",
        "Inspection item 운반과 inspection 자체는 서로 다른 top-level task입니다. `LOAD_UNLOAD_TRANSFER_INTERFACE(item, interface, action, source, destination)`는 `action=load|unload`를 받아 전체 pick-and-place sequence를 수행합니다. `INSPECT_PRODUCT(target, inspection_plan, workstation=None)`는 지정 workstation에서 정지 상태의 검사만 수행하며 queue에서 item을 꺼내거나 queue로 옮기지 않습니다. Simulator는 독립적인 task ID, 할당, timing과 complexity를 유지하면서 `interface load -> inspect -> interface unload`로 세 task를 연결할 수 있습니다.",
        "",
        "## MANAGE_ROBOT_POWER Dock-Charge 사용",
        "",
        "`MANAGE_ROBOT_POWER`는 `action=dock_charge`, 지정 docking-station reference와 `target_soc`를 입력으로 받습니다. ManSim `mfg_flow_shop`은 worker별 전용 dock에서 직접 충전할 때 이 형식을 사용합니다. 기존 battery management와 같은 atomic task를 사용하므로 별도 charging task나 primitive는 필요하지 않습니다. Dock까지의 이동, 점유, 충전시간과 SOC 진행은 simulator가 담당합니다.",
        "",
        "## Generic Item Request",
        "",
        "일부 task 입력의 `item`은 반드시 concrete item id일 필요가 없습니다. 예를 들어 `REPLENISH_MATERIAL`은 “특정 `MAT-WH-*`를 가져오라”가 아니라 “source에서 사용 가능한 material 하나를 찾아 destination을 target level까지 보충하라”는 generic request로 실행될 수 있습니다. 이 경우 task input은 `entity_type=material`, `selection_policy=available_material_from_source` 같은 request를 담고, concrete item instance는 `PRIMITIVE_IDENTIFY_ITEM` 단계에서 확정됩니다.",
        "",
        "`LOAD_MACHINE`, `INSPECT_PRODUCT`, 일반 `TRANSFER`처럼 특정 queue item이나 machine output이 task 의미의 핵심인 경우에는 concrete item id를 task 생성 시점에 줄 수 있습니다. `SETUP_MACHINE`은 item을 고르거나 운반하지 않고, 이미 machine에 적재된 input을 바탕으로 setup만 수행합니다.",
        "",
        "이 문서는 `data/tasks/*.json`에 정의된 HumanoidSim core task를 사람이 읽기 쉽게 정리한 reference입니다. JSON 파일이 원본이고, 이 문서는 검색과 검토를 위한 요약입니다.",
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
        _html_table(
            ["Level", "개수"],
            [[_code(level), str(level_counts[level])] for level in ("ATOMIC_TASK", "COMPOSITE_TASK")],
            ["72%", "28%"],
        ),
        "",
        "### Task Level 기준",
        "",
        "HumanoidSim v0.1에서 task level은 실행 workflow의 구조로 구분합니다. Primitive 개수나 step 길이가 아니라, step이 어떤 수준의 call을 참조하는지가 기준입니다.",
        "",
        _html_table(
            ["Level", "기준", "예시"],
            [
                [_code("PRIMITIVE_SKILL"), "더 이상 하위 step을 갖지 않는 최소 실행 skill입니다.", f"{_code('NAVIGATE_TO')}, {_code('GRASP')}, {_code('VERIFY_PLACEMENT')}"],
                [_code("ATOMIC_TASK"), "하위 step이 모두 primitive skill로 구성된 실행 가능한 단일 task입니다.", f"{_code('TRANSFER')}, {_code('LOAD_MACHINE')}, {_code('INSPECT_PRODUCT')}"],
                [_code("COMPOSITE_TASK"), "최소 1개 이상의 child task call을 직접 포함하는 workflow입니다. orchestration용 primitive step을 함께 가질 수 있습니다.", f"{_code('REPLENISH_MATERIAL')} -> {_code('TRANSFER')}, {_code('FETCH_FOR_OPERATOR')} -> {_code('HANDOVER_ITEM')}"],
            ],
            ["16%", "56%", "28%"],
        ),
        "",
        "`StepCall.call_code`는 primitive code뿐 아니라 task code도 참조할 수 있습니다. 이때 `expected_level`은 필수이며, nested task step에서는 `ATOMIC_TASK` 또는 `COMPOSITE_TASK`로 명시합니다.",
        "",
        "### Category 설명",
        "",
    ]

    category_rows = []
    for category_id in sorted(category_counts):
        category_name = next(
            _catalog(task).get("category", "")
            for task in tasks
            if _catalog(task).get("category_id") == category_id
        )
        category_rows.append(
            [
                _text(category_id),
                _text(category_name),
                str(category_counts[category_id]),
                _text(CATEGORY_DESCRIPTIONS.get(category_id, "")),
            ]
        )
    lines.append(_html_table(["ID", "Category", "개수", "설명"], category_rows, ["7%", "27%", "8%", "58%"]))

    lines += [
        "",
        "## 전체 Task 목록",
        "",
    ]
    task_rows = []
    for task in tasks:
        catalog = _catalog(task)
        category_id = catalog.get("category_id", "?")
        source = task["_path"].relative_to(ROOT).as_posix()
        task_rows.append(
            [
                _text(catalog.get("task_no", "")),
                _code(task["code"]),
                _code(task["level"]),
                _text(TASK_DESCRIPTIONS.get(category_id, "휴머노이드가 수행할 수 있는 작업 단위입니다.")),
                _inputs(task),
                _capabilities(task),
                _resources(task),
                _text(task.get("safety", {}).get("risk_level", "LOW")),
                _sequence(task),
                _code(source),
            ]
        )
    lines.append(
        _html_table(
            ["No", "Code", "Level", "설명", "입력", "Capabilities", "Resources", "Risk", "Step / Nested Sequence", "원본"],
            task_rows,
            ["4%", "10%", "9%", "26%", "11%", "9%", "9%", "4%", "12%", "6%"],
        )
    )

    _write_doc("tasks_reference.md", lines)


def _write_primitives_reference(tasks: list[dict[str, Any]], primitives: list[dict[str, Any]]) -> None:
    used_by: dict[str, set[str]] = defaultdict(set)
    for task in tasks:
        for step in task.get("steps", []):
            if step.get("expected_level") == "PRIMITIVE_SKILL":
                used_by[step.get("call_code", "")].add(task["code"])
    active_primitives = [primitive for primitive in primitives if used_by.get(primitive["code"])]
    _validate_primitive_grouping(primitives)

    lines = [
        "# Primitive Reference",
        "",
        "## Generic Request Resolution",
        "",
        "`PRIMITIVE_IDENTIFY_ITEM`은 이미 정해진 item id를 확인하는 데에도 쓰이고, generic item request를 concrete item instance로 확정하는 데에도 쓰입니다. 예를 들어 `REPLENISH_MATERIAL`이 `entity_type=material`, `selection_policy=available_material_from_source`를 입력으로 받으면, 이 primitive 단계에서 실제로 집을 수 있는 material slot과 `MAT-WH-*` item id를 선택합니다.",
        "",
        "이 primitive는 task 의미를 바꾸지 않습니다. Task는 “material 보충”이라는 목표를 유지하고, primitive는 그 목표를 실행 가능한 concrete 대상에 연결합니다.",
        "",
        "이 문서는 task step에서 실제로 참조되는 active primitive skill과 primitive registry를 정리한 reference입니다. Primitive는 task를 구성하는 가장 작은 실행 skill이며, `ATOMIC_TASK`와 `COMPOSITE_TASK`의 step에서 참조됩니다.",
        "",
        "## 요약",
        "",
        f"- Active primitive 수: {len(active_primitives)}",
        f"- Registry primitive 수: {len(primitives)}",
        "- 원본 primitive 정의: `data/primitives/*.json`",
        "- Primitive template index: `data/primitive_templates.json`",
        "- State relation 원본: 각 primitive JSON의 `metadata.state`, `data/state_schema_core.json`의 `primitive_state_profiles`",
        "- 정상적으로 실행 중인 모든 primitive는 Availability State 중 `EXECUTING`으로 표현됩니다.",
        "- Incident recovery protocol 안에서 실행되는 primitive는 예외적으로 `BLOCKED` 상태를 유지합니다. 이때 primitive code는 `task_context.primitive_call_code`에 기록되며, UI에서는 `CODE (RECOVERY)`처럼 표시할 수 있습니다.",
        "",
        "## Active Primitive와 Registry Primitive",
        "",
        _html_table(
            ["용어", "의미", "기준 파일/필드", "사용 목적"],
            [
                ["Active primitive", "현재 task catalog의 `steps`에서 `expected_level=PRIMITIVE_SKILL`로 직접 참조되는 primitive입니다. 실제 task sequence를 이루는 실행 leaf step입니다.", "`data/tasks/*.json`의 `steps[].call_code`", "task reference, 실행 coverage, ManSim primitive 지원 범위 확인"],
                ["Registry primitive", "HumanoidSim primitive registry에 등록된 전체 primitive 정의입니다. 현재 task가 쓰지 않더라도, 추후 task나 recovery protocol에서 재사용할 수 있습니다.", "`data/primitives/*.json`, `data/task_catalog_core.json`의 primitive entry", "schema validation, hierarchy validation, custom task 확장"],
            ],
            ["16%", "44%", "20%", "20%"],
        ),
        "",
        "개념적으로는 `active primitive <= registry primitive`입니다. 현재 v0.1 catalog에서는 둘의 수가 같을 수 있지만, custom task를 만들거나 future primitive를 먼저 등록하면 registry에만 존재하는 primitive가 생길 수 있습니다.",
        "",
        "## Primitive와 State 관계",
        "",
        "Primitive는 Humanoid가 지금 어떤 실행 단계를 수행하는지를 나타냅니다. State는 그 실행 동안 Humanoid가 어떤 운용 상태인지를 나타냅니다. 따라서 primitive 자체가 state는 아니지만, primitive 시작/종료 event가 HumanoidSim state transition을 유도합니다.",
        "",
        _html_table(
            ["필드", "의미"],
            [
                [_code("metadata.state.availability.running"), "primitive 실행 중의 Availability State입니다. 모든 primitive는 `EXECUTING`을 사용합니다."],
                [_code("metadata.state.allowed.mobility"), "primitive 실행 중 허용되는 Mobility State입니다."],
                [_code("metadata.state.allowed.manipulation"), "primitive 실행 중 허용되는 Manipulation State입니다."],
                [_code("metadata.state.allowed.power"), "primitive 실행 중 허용되는 Power State입니다."],
                [_code("metadata.state.effects.on_start"), "primitive 시작 시 적용되는 state effect입니다."],
                [_code("metadata.state.effects.on_end"), "primitive 종료 시 적용되는 state effect입니다."],
            ],
            ["35%", "65%"],
        ),
        "",
        "`NAVIGATE_TO`는 시작 시 `mobility=NAVIGATING`, 종료 시 `mobility=STATIONARY`이 됩니다. `GRASP`, `LIFT`는 `manipulation=HOLDING`을 사용하고, `PLACE`, `RELEASE`는 내려놓는 동안 `PLACING`을 거쳐 종료 후 `FREE`로 돌아갑니다. 확인/기록 계열 primitive는 보통 `STATIONARY`이며, cargo 관련 manipulation state는 caller의 cargo event에 따라 유지됩니다.",
        "",
        "## Primitive Registry와 Task Catalog의 관계",
        "",
        "Primitive는 task catalog의 현재 workflow에 포함될 수도 있고, 아직 특정 task에 연결되지 않은 registry capability로 존재할 수도 있습니다. Task는 업무 목적을 가진 workflow이고, primitive는 그 workflow를 구성하거나 state transition, safety, recovery, context 갱신을 지원하는 재사용 가능한 실행 능력입니다.",
        "",
        "따라서 primitive registry는 현재 task catalog보다 넓은 범위를 가질 수 있습니다. 현재 task에서 참조되는 primitive는 active primitive로 분류하고, 아직 task에 직접 연결되지 않았지만 custom task, incident recovery protocol, 도메인별 adapter에서 사용할 수 있는 primitive는 registry primitive로 유지합니다.",
        "",
        _html_table(
            ["Primitive 유형", "예시", "역할"],
            [
                ["Active primitive", f"{_code('NAVIGATE_TO')}, {_code('GRASP')}, {_code('UPDATE_RECORD')}", "현재 task catalog의 `steps`에서 직접 참조되는 primitive입니다."],
                ["Registry primitive", f"{_code('SCAN_ENVIRONMENT')}, {_code('LOCALIZE_SELF')}, {_code('RECOVER_BALANCE')}", "현재 task에 직접 연결되지 않아도 HumanoidSim이 보유할 수 있는 기본 능력입니다."],
                ["Recovery primitive", f"{_code('MONITOR_FORCE')}, {_code('CHECK_PAYLOAD_STABILITY')}, {_code('CALIBRATE_SENSOR')}", "incident 발생 후 복구, 재시도, 안전 확인을 지원하는 primitive입니다."],
                ["Context primitive", f"{_code('UPDATE_MAP_CONTEXT')}, {_code('REQUEST_CLEARANCE')}", "환경 정보, permission, map/context 동기화를 지원하는 primitive입니다."],
            ],
            ["22%", "28%", "50%"],
        ),
        "",
        "비-task 성격 primitive는 특정 업무 목표를 직접 완결하지 않더라도, task 실행의 안정성, 관찰성, 복구 가능성을 높이는 기본 능력으로 정의할 수 있습니다. 이들은 task가 아니라도 primitive registry에 포함될 수 있으며, 필요 시 composite task나 incident recovery protocol에서 참조합니다.",
        "",
        "## Primitive Grouping",
        "",
        "Primitive는 task category가 아니라 휴머노이드 기능 축을 기준으로 그룹화합니다. Task category는 업무 도메인을 설명하고, primitive group은 휴머노이드가 수행하는 저수준 능력과 state 변화 방식을 설명합니다. 현재 registry primitive는 아래 9개 그룹 중 하나에 반드시 속합니다.",
        "",
        _html_table(
            ["Group ID", "Group", "범위", "대표 State 영향", "Primitive"],
            _primitive_group_rows(include_candidates=False),
            ["8%", "18%", "25%", "19%", "30%"],
        ),
        "",
        "비-task 성격 확장 후보는 아래처럼 같은 group 체계에 배치합니다. 이 목록은 아직 registry에 등록된 primitive가 아니라, 향후 `data/primitives/*.json`에 추가할 수 있는 후보입니다.",
        "",
        _html_table(
            ["Group ID", "Group", "확장 후보 Primitive"],
            _primitive_group_rows(include_candidates=True),
            ["8%", "24%", "68%"],
        ),
        "",
        "권장 schema는 primitive JSON의 `metadata.group`에 `group_id`, `group_name`, `capability_axis`, `state_axes`를 추가하는 방식입니다. 이렇게 하면 task reference와 runtime executor가 primitive를 임의로 묶지 않고 HumanoidSim 정의를 그대로 사용할 수 있습니다.",
        "",
        "## Primitive Difficulty Weight",
        "",
        "OTC(Operational Task Complexity) 계산을 위해 모든 primitive는 `metadata.operational_complexity.difficulty_weight` 값을 가집니다. 값은 `0.0`부터 `1.0`까지 0.1 단위로 부여하며, 실행 시간보다는 motion precision, manipulation difficulty, safety risk, collaboration burden, recovery burden을 반영합니다.",
        "",
        _html_table(
            ["Weight", "Group", "기준"],
            [
                ["0.0", "Administrative", "기록/상태 갱신처럼 로봇 실행 부담이 거의 없는 primitive"],
                ["0.1", "Administrative", "단순 선언, read, report 등 물리 동작이 거의 없는 primitive"],
                ["0.2", "Low Operational", "낮은 부담의 확인/검증 primitive"],
                ["0.3", "Low Operational", "표준 이동, 수량/상태 확인처럼 경로 또는 인지 부담이 조금 있는 primitive"],
                ["0.4", "Standard Robot Skill", "localize, reach, inspect, verify처럼 위치/인지 정확도가 필요한 primitive"],
                ["0.5", "Standard Robot Skill", "grasp/place 같은 표준 manipulation primitive"],
                ["0.6", "Manipulation & Process", "lift, tool, machine, vehicle 등 물리 상태를 바꾸는 primitive"],
                ["0.7", "Manipulation & Process", "공정 품질, payload, safety gate가 얽힌 고부담 primitive"],
                ["0.8", "Coordination & Recovery", "robot sync, lockout, coordination처럼 동기화와 안전 영향이 큰 primitive"],
                ["0.9", "Coordination & Recovery", "human collaboration, EHS action처럼 실패 시 안전/복구 부담이 매우 큰 primitive"],
                ["1.0", "Critical", "시스템 중단, 장기 recovery, 인명/설비 위험으로 이어질 수 있는 critical primitive"],
            ],
            ["10%", "24%", "66%"],
        ),
        "",
        "## Primitive 목록",
        "",
    ]

    primitive_rows = []
    for primitive in active_primitives:
        code = primitive["code"]
        source = primitive["_path"].relative_to(ROOT).as_posix()
        primitive_rows.append(
            [
                _code(code),
                _primitive_group_label(code),
                _primitive_difficulty(primitive),
                _text(_primitive_description(primitive)),
                _code(_availability_text(primitive)),
                _state_axis_text(primitive, "mobility"),
                _state_axis_text(primitive, "manipulation"),
                _inputs(primitive),
                _outputs(primitive),
                _used_by_tasks(used_by.get(code, set())),
                _code(source),
            ]
        )
    lines.append(
        _html_table(
            ["Code", "Group", "Difficulty", "설명", "Availability State", "Mobility State", "Manipulation State", "입력", "출력", "사용 Task", "원본"],
            primitive_rows,
            ["9%", "9%", "6%", "20%", "8%", "9%", "9%", "8%", "6%", "10%", "6%"],
        )
    )

    lines += [
        "",
        "## Primitive 추가/수정 방법",
        "",
        "1. `data/primitives/<CODE>.json`을 추가하거나 수정합니다.",
        "2. `metadata.state.availability.running`, `allowed`, `effects.on_start`, `effects.on_end`를 명시합니다.",
        "3. `data/state_schema_core.json`의 `primitive_state_profiles`에도 같은 state profile을 반영합니다.",
        "4. task에서 사용하려면 `data/tasks/*.json` step에 `call_code=<CODE>`, `expected_level=PRIMITIVE_SKILL`로 참조합니다.",
        "5. `python -m unittest discover -s tests`로 primitive profile과 task hierarchy validation을 확인합니다.",
    ]

    _write_doc("primitives_reference.md", lines)


def _write_incident_reference(schema: dict[str, Any]) -> None:
    categories = {category["id"]: category for category in schema.get("categories", [])}
    incidents = schema.get("incidents", [])
    category_counts = Counter(incident["category"] for incident in incidents)

    lines = [
        "# Humanoid Incident Reference",
        "",
        "## 개요",
        "",
        f"HumanoidSim v0.1은 범용 휴머노이드가 실행 중 겪을 수 있는 **{len(incidents)}개 incident**를 정의합니다. Incident는 새로운 state가 아니라 `StateReason + recovery protocol`입니다. 휴머노이드의 현재 상태는 Availability, Mobility, Power, Manipulation 네 축으로 표현하고, 돌발상황의 원인과 후속 대응 절차는 `reason`과 incident profile에 기록합니다.",
        "",
        "Incident code는 정의 단계부터 모두 대문자 canonical code를 사용합니다. 예: `GRIP_FAILED`, `ITEM_DROPPED`, `RESOURCE_PREEMPTED`, `UNKNOWN`",
        "",
        "## 카테고리별 개수",
        "",
    ]

    category_rows = []
    for category in schema.get("categories", []):
        category_id = category["id"]
        category_rows.append(
            [
                _code(category_id),
                _text(category.get("name", "")),
                _text(CATEGORY_KO.get(category_id, "")),
                str(category_counts[category_id]),
                _text(CATEGORY_DESCRIPTION_KO.get(category_id, category.get("description", ""))),
            ]
        )
    lines.append(_html_table(["Category ID", "Category", "한글명", "개수", "설명"], category_rows, ["20%", "21%", "12%", "7%", "40%"]))

    lines += [
        "",
        f"총 incident 수: **{len(incidents)}개**",
        "",
        "## Incident Model",
        "",
        _html_table(
            ["요소", "설명"],
            [
                ["Incident Code", "incident를 식별하는 안정적인 canonical code입니다. 모든 code는 대문자로 정의합니다."],
                ["Category", "incident를 해석하기 위한 범용 분류입니다. 제조 전용 의미에 묶이지 않습니다."],
                ["Default Availability", "incident 발생 직후 기본 Availability 전이입니다. 대부분 `BLOCKED`, 짧은 재시도 대기는 `WAITING`, 로봇 자체가 작업 불가하면 `DISABLED`입니다."],
                ["Trigger Primitives", "incident가 자연스럽게 발생할 수 있는 primitive입니다. 예: `GRASP` 중 `GRIP_FAILED`"],
                ["Aliases", "runtime에서 관찰한 세부 실패 reason을 canonical incident code로 해석하기 위한 별칭입니다."],
                ["Recovery Protocol", "복구, 재시도, 보고, 재작업을 표현하는 step sequence입니다. 모든 step은 기존 task 또는 primitive code를 참조합니다."],
                ["Retry Policy", "local retry 횟수와 지연 시간입니다. 실제 정책 최적화는 runtime 또는 manager layer가 담당합니다."],
            ],
            ["24%", "76%"],
        ),
        "",
        "## Incident Codes",
        "",
    ]

    incident_rows = []
    for incident in incidents:
        category = categories.get(incident["category"], {})
        incident_rows.append(
            [
                _code(incident["code"]),
                _text(category.get("name", incident["category"])),
                _text(INCIDENT_DESCRIPTIONS.get(incident["code"], incident.get("description", ""))),
                _code(incident.get("default_availability", "")),
                _code_list(incident.get("trigger_primitives", [])) or "all primitives",
                _recovery_protocol(incident.get("recovery_protocol", [])),
            ]
        )
    lines.append(
        _html_table(
            ["Code", "Category", "설명", "Default Availability", "Trigger Primitives", "Recovery Protocol"],
            incident_rows,
            ["15%", "14%", "31%", "9%", "13%", "18%"],
        )
    )

    alias_rows = []
    for incident in incidents:
        for alias in incident.get("aliases", []):
            alias_rows.append([_code(alias), _code(incident["code"]), _text(INCIDENT_DESCRIPTIONS.get(incident["code"], ""))])

    lines += [
        "",
        "## Alias Resolution",
        "",
        "Incident의 canonical code는 HumanoidSim이 소유합니다. ManSim 같은 runtime은 scenario에서 관찰한 세부 reason 문자열을 전달할 수 있고, HumanoidSim은 `IncidentProfile.aliases`를 통해 이를 canonical incident로 해석합니다.",
        "",
    ]
    if alias_rows:
        lines.append(_html_table(["Alias", "Canonical Incident", "의미"], alias_rows, ["25%", "25%", "50%"]))
    else:
        lines.append("현재 등록된 alias가 없습니다.")

    lines += [
        "",
        "## Recovery Protocol 검증",
        "",
        "Recovery protocol의 각 step은 `kind=primitive` 또는 `kind=task`를 갖습니다.",
        "",
        "- `kind=primitive`이면 `code`가 HumanoidSim primitive registry에 존재해야 합니다.",
        "- `kind=task`이면 `code`가 HumanoidSim task catalog에 존재해야 합니다.",
        "- 존재하지 않는 primitive/task를 참조하면 `validate_incident_schema()`가 실패합니다.",
        "",
        f"현재 v0.1 schema 기준 recovery step은 총 {_recovery_step_count(incidents)}개이며, 모두 정의된 primitive 또는 task를 참조합니다.",
        "",
        "Recovery protocol은 incident로 인해 막힌 상태를 해소하기 위한 절차입니다. 따라서 recovery step이 task 또는 primitive를 실행하더라도 Availability는 정상 작업의 `EXECUTING`으로 바꾸지 않고 `BLOCKED`를 유지합니다. 현재 수행 중인 recovery step은 `task_context.task_code` 또는 `task_context.primitive_call_code`에 기록하고, UI나 replay에서는 `CODE (RECOVERY)`처럼 일반 작업과 구분해서 표시합니다. Recovery protocol이 끝나면 runtime은 task 취소, 재할당, 재시도 같은 후속 정책에 따라 `AVAILABLE`, `ASSIGNED`, 또는 계속 `BLOCKED` 중 하나로 전이시킬 수 있습니다.",
        "",
        "## State Transition",
        "",
        "Incident는 주로 Availability 축에 영향을 줍니다. Mobility, Manipulation, Power는 incident 순간의 물리 상태를 유지하거나 power/hardware incident처럼 명확한 경우에만 함께 바뀝니다.",
        "",
        "```mermaid",
        "flowchart TB",
        "  subgraph O[Operational States]",
        "    AVAILABLE[AVAILABLE]",
        "    ASSIGNED[ASSIGNED]",
        "    EXECUTING[EXECUTING]",
        "    WAITING[WAITING]",
        "  end",
        "",
        "  subgraph U[Unavailable States]",
        "    BLOCKED[BLOCKED]",
        "    DISABLED[DISABLED]",
        "    OFFLINE[OFFLINE]",
        "  end",
        "",
        "  EXECUTING -->|TRAFFIC_WAIT, OPERATOR_NOT_READY, short retry| WAITING",
        "  WAITING -->|condition resolved| EXECUTING",
        "  WAITING -->|timeout or condition changed| BLOCKED",
        "  EXECUTING -->|perception/manipulation/resource/COLLISION/UNKNOWN| BLOCKED",
        "  EXECUTING -->|DEPLETED, severe hardware, safety interlock| DISABLED",
        "  BLOCKED -->|recovery protocol step runs| BLOCKED",
        "  BLOCKED -->|recovery completed and replan needed| AVAILABLE",
        "  BLOCKED -->|recovery completed and retry assigned| ASSIGNED",
        "  DISABLED -->|maintenance or power recovery assigned| ASSIGNED",
        "  ASSIGNED --> EXECUTING",
        "  EXECUTING -->|task completed| AVAILABLE",
        "  BLOCKED -->|task canceled| AVAILABLE",
        "  OFFLINE -->|returned to operation| AVAILABLE",
        "```",
        "",
        "## Runtime 사용 예시",
        "",
        "```python",
        "from humanoidsim import build_incident_transition_event, transition_humanoid_state",
        "",
        "event = build_incident_transition_event(",
        '    "GRIP_FAILED",',
        '    task_code="TRANSFER",',
        '    primitive_call_code="GRASP",',
        ")",
        "next_snapshot = transition_humanoid_state(current_snapshot, event)",
        "```",
        "",
        "Alias도 같은 API로 해석됩니다.",
        "",
        "```python",
        'event = build_incident_transition_event("material_shelf_slot_empty")',
        'assert event.reason.code == "RESOURCE_PREEMPTED"',
        "```",
        "",
        "ManSim 같은 runtime은 incident 발생 확률과 발생 조건만 판단합니다. Incident code, alias resolution, 기본 state transition, recovery protocol의 의미는 HumanoidSim 정의를 사용합니다.",
    ]

    _write_doc("incident_reference.md", lines)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_doc(name: str, lines: list[str]) -> None:
    (DOCS / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _catalog(task: dict[str, Any]) -> dict[str, Any]:
    return task.get("metadata", {}).get("catalog", {})


def _inputs(spec: dict[str, Any]) -> str:
    rows = []
    for item in spec.get("inputs", []):
        mark = "*" if item.get("required", True) else ""
        rows.append(f"{_text(item['name'])}{mark}: {_text(item.get('type_hint', 'Any'))}")
    return _join(rows)


def _outputs(spec: dict[str, Any]) -> str:
    rows = []
    for item in spec.get("outputs", []):
        rows.append(f"{_text(item['name'])}: {_text(item.get('type_hint', 'Any'))}")
    return _join(rows)


def _capabilities(task: dict[str, Any]) -> str:
    return _join(_text(item) for item in task.get("required_capabilities", []))


def _resources(task: dict[str, Any]) -> str:
    rows = []
    for label, key in (("tool", "required_tools"), ("vehicle", "required_vehicles"), ("equipment", "required_equipment")):
        for item in task.get(key, []):
            rows.append(f"{label}:{_text(item.get('alias', ''))}")
    return _join(rows)


def _sequence(task: dict[str, Any]) -> str:
    rows = []
    for step in task.get("steps", []):
        call_code = step.get("call_code", "")
        level = step.get("expected_level", "")
        if level and level != "PRIMITIVE_SKILL":
            rows.append(f"{_code(call_code)} [{_text(level)}]")
        else:
            rows.append(_code(call_code))
    return _join(rows)


def _used_by_tasks(task_codes: set[str]) -> str:
    return _join(_code(code) for code in sorted(task_codes))


def _primitive_description(primitive: dict[str, Any]) -> str:
    code = primitive["code"]
    if code == "NAVIGATE_TO":
        return "목표 위치나 대상의 service tile까지 이동합니다."
    if code == "ALIGN":
        return "설비, 충전기, 작업대 또는 대상 위치에 정렬하거나 docking합니다."
    if code in {"REACH_TO", "GRASP", "LIFT", "PLACE", "RELEASE"}:
        return {
            "REACH_TO": "대상 item이나 tool에 팔 또는 gripper를 접근시킵니다.",
            "GRASP": "대상 item이나 tool을 잡거나 지지합니다.",
            "LIFT": "잡은 대상을 들어 운반 가능한 상태로 만듭니다.",
            "PLACE": "운반 중인 대상을 목표 위치에 내려놓습니다.",
            "RELEASE": "잡고 있던 대상이나 tool을 놓습니다.",
        }[code]
    if code.startswith("LOCALIZE"):
        return "대상 객체, 부품, 표면 또는 영역의 위치와 접근 정보를 확인합니다."
    if "IDENTIFY" in code:
        return "대상 item, 제품, 부품 또는 label의 정체를 식별합니다."
    if code.startswith("CHECK"):
        return "요청, context, 안전 조건 또는 사전 조건을 확인합니다."
    if code.startswith("READ"):
        return "설비, 시스템 또는 작업 맥락의 현재 상태를 읽습니다."
    if code.startswith("VERIFY") or code.startswith("PRIMITIVE_VERIFY"):
        return "작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다."
    if code.startswith("EXECUTE"):
        return "task context에 맞는 domain action을 수행합니다."
    if code.startswith("OPERATE"):
        return "tool, dispenser, interface 또는 장치를 조작합니다."
    if code in {"UPDATE_RECORD", "LOG_RESULT", "RECORD_RESULT", "CREATE_OR_UPDATE_RECORD"}:
        return "작업 결과, traceability, 재고 또는 예외 정보를 기록하거나 갱신합니다."
    if code == "ANNOUNCE_INTENT":
        return "handover나 공동 작업 전에 의도와 다음 행동을 알립니다."
    if code == "CONFIRM_OPERATOR_STATE":
        return "operator 또는 협업 대상의 준비 상태와 안전 상태를 확인합니다."
    return "task context에 따라 사용되는 휴머노이드 primitive skill입니다."


def _validate_primitive_grouping(primitives: list[dict[str, Any]]) -> None:
    registry_codes = {primitive["code"] for primitive in primitives}
    grouped_codes = set(PRIMITIVE_TO_GROUP)
    missing = sorted(registry_codes - grouped_codes)
    extra = sorted(grouped_codes - registry_codes)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing group: {', '.join(missing)}")
        if extra:
            details.append(f"unknown primitive in group map: {', '.join(extra)}")
        raise ValueError("; ".join(details))


def _primitive_group_rows(include_candidates: bool) -> list[list[str]]:
    rows = []
    for group in PRIMITIVE_GROUPS:
        if include_candidates:
            rows.append(
                [
                    _text(group["id"]),
                    _text(group["name"]),
                    _code_list(group["candidates"]),
                ]
            )
        else:
            rows.append(
                [
                    _text(group["id"]),
                    _text(group["name"]),
                    _text(group["scope"]),
                    _text(group["state"]),
                    _code_list(group["primitives"]),
                ]
            )
    return rows


def _primitive_group_label(code: str) -> str:
    group_id = PRIMITIVE_TO_GROUP.get(code, "")
    if not group_id:
        return "-"
    group_name = next(group["name"] for group in PRIMITIVE_GROUPS if group["id"] == group_id)
    return f"{_text(group_id)}<br>{_text(group_name)}"


def _primitive_difficulty(primitive: dict[str, Any]) -> str:
    complexity = primitive.get("metadata", {}).get("operational_complexity", {})
    weight = complexity.get("difficulty_weight")
    group = complexity.get("difficulty_group", "")
    if weight is None:
        return "-"
    return f"{_text(f'{float(weight):.1f}')}<br>{_text(group)}"


def _availability_text(primitive: dict[str, Any]) -> str:
    return primitive.get("metadata", {}).get("state", {}).get("availability", {}).get("running", "EXECUTING")


def _state_axis_text(primitive: dict[str, Any], axis: str) -> str:
    state = primitive.get("metadata", {}).get("state", {})
    effects = state.get("effects", {})
    on_start = effects.get("on_start", {}).get(axis)
    on_end = effects.get("on_end", {}).get(axis)
    if on_start or on_end:
        rows = []
        if on_start:
            rows.append(f"시작 {_code(on_start)}")
        if on_end:
            rows.append(f"종료 {_code(on_end)}")
        return " / ".join(rows)
    allowed = state.get("allowed", {}).get(axis, [])
    if not allowed:
        return "-"
    if len(allowed) > 2:
        return "상황 의존: " + _code_list(allowed)
    return _code_list(allowed)


def _recovery_protocol(steps: list[dict[str, Any]]) -> str:
    rows = []
    for step in steps:
        label = _code(step.get("code", ""))
        if step.get("optional"):
            label += " (optional)"
        rows.append(label)
    return " -> ".join(rows) if rows else "-"


def _recovery_step_count(incidents: list[dict[str, Any]]) -> int:
    return sum(len(incident.get("recovery_protocol", [])) for incident in incidents)


def _code_list(values: list[str]) -> str:
    return ", ".join(_code(value) for value in values)


def _join(values: Any) -> str:
    rows = [value for value in values if value]
    return "<br>".join(rows) if rows else "-"


def _code(value: Any) -> str:
    return f"<code>{escape(str(value))}</code>"


def _text(value: Any) -> str:
    return escape(str(value)).replace("\n", " ")


def _html_table(headers: list[str], rows: list[list[str]], widths: list[str] | None = None) -> str:
    lines = ["<table>"]
    if widths:
        lines.append("  <colgroup>")
        for width in widths:
            lines.append(f'    <col style="width: {width};" />')
        lines.append("  </colgroup>")
    lines.append("  <thead>")
    lines.append("    <tr>")
    for header in headers:
        lines.append(f"      <th>{_text(header)}</th>")
    lines.append("    </tr>")
    lines.append("  </thead>")
    lines.append("  <tbody>")
    for row in rows:
        lines.append("    <tr>")
        for cell in row:
            lines.append(f"      <td>{cell}</td>")
        lines.append("    </tr>")
    lines.append("  </tbody>")
    lines.append("</table>")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
