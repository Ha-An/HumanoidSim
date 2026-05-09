from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .task_schema import (
    AcquirePolicy,
    Condition,
    EquipmentRequirement,
    EquipmentUseMode,
    LocationRef,
    ParameterSpec,
    ResourceControlMode,
    RetryPolicy,
    RiskLevel,
    SafetyConstraint,
    StepCall,
    SuccessCriterion,
    TaskLevel,
    TaskRegistry,
    TaskSpec,
    ToolRequirement,
    ToolUseMode,
    VehicleRequirement,
    VehicleUseMode,
)


@dataclass
class TaskCatalog:
    root: Path
    index: dict[str, Any]
    registry: TaskRegistry
    tasks: dict[str, TaskSpec]
    primitives: dict[str, TaskSpec]

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def primitive_count(self) -> int:
        return len(self.primitives)

    def get(self, code: str) -> TaskSpec:
        return self.registry.get(code)


def find_project_root(start: Path | str | None = None) -> Path:
    candidates: list[Path] = []
    if start is not None:
        candidates.append(Path(start).resolve())
    candidates.append(Path.cwd().resolve())
    candidates.append(Path(__file__).resolve().parents[2])

    for candidate in candidates:
        for path in [candidate, *candidate.parents]:
            if (path / "data" / "task_catalog_core.json").exists():
                return path
    raise FileNotFoundError("Could not find data/task_catalog_core.json from cwd or package path.")


def load_task_catalog(root: Path | str | None = None, *, validate: bool = True) -> TaskCatalog:
    project_root = find_project_root(root)
    index = _read_json(project_root / "data" / "task_catalog_core.json")
    registry = TaskRegistry()
    primitives: dict[str, TaskSpec] = {}
    tasks: dict[str, TaskSpec] = {}

    for rel_path in index.get("primitive_paths", []):
        spec = task_spec_from_dict(_read_json(project_root / rel_path))
        primitives[spec.code] = spec
        registry.register(spec)

    for rel_path in index.get("task_paths", []):
        spec = task_spec_from_dict(_read_json(project_root / rel_path))
        tasks[spec.code] = spec
        registry.register(spec)

    if validate:
        for code in tasks:
            registry.validate_hierarchy(code)

    return TaskCatalog(root=project_root, index=index, registry=registry, tasks=tasks, primitives=primitives)


def task_spec_from_dict(data: dict[str, Any]) -> TaskSpec:
    return TaskSpec(
        code=str(data["code"]),
        level=TaskLevel(data["level"]),
        version=str(data.get("version", "1.0.0")),
        name=str(data.get("name", "")),
        description=str(data.get("description", "")),
        inputs=[_parameter(row) for row in data.get("inputs", [])],
        outputs=[_parameter(row) for row in data.get("outputs", [])],
        required_capabilities=[str(item) for item in data.get("required_capabilities", [])],
        required_tools=[_tool(row) for row in data.get("required_tools", [])],
        required_vehicles=[_vehicle(row) for row in data.get("required_vehicles", [])],
        required_equipment=[_equipment(row) for row in data.get("required_equipment", [])],
        safety=_safety(data.get("safety", {})),
        preconditions=[_condition(row) for row in data.get("preconditions", [])],
        postconditions=[_condition(row) for row in data.get("postconditions", [])],
        success_criteria=[_success(row) for row in data.get("success_criteria", [])],
        steps=[_step(row) for row in data.get("steps", [])],
        metadata=dict(data.get("metadata", {})),
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parameter(data: dict[str, Any]) -> ParameterSpec:
    return ParameterSpec(
        name=str(data["name"]),
        type_hint=str(data.get("type_hint", "Any")),
        required=bool(data.get("required", True)),
        description=str(data.get("description", "")),
        default=data.get("default"),
        unit=data.get("unit"),
        allowed_values=list(data.get("allowed_values", [])),
    )


def _condition(data: dict[str, Any]) -> Condition:
    return Condition(expression=str(data.get("expression", "")), description=str(data.get("description", "")))


def _success(data: dict[str, Any]) -> SuccessCriterion:
    return SuccessCriterion(
        metric=str(data.get("metric", "")),
        operator=str(data.get("operator", "==")),
        value=data.get("value"),
        unit=data.get("unit"),
        description=str(data.get("description", "")),
    )


def _location(data: dict[str, Any] | None) -> LocationRef | None:
    if not isinstance(data, dict):
        return None
    return LocationRef(
        location_id=str(data.get("location_id", "")),
        pose_id=data.get("pose_id"),
        frame_id=data.get("frame_id"),
        zone_id=data.get("zone_id"),
        metadata=dict(data.get("metadata", {})),
    )


def _tool(data: dict[str, Any]) -> ToolRequirement:
    return ToolRequirement(
        alias=str(data["alias"]),
        tool_type=str(data.get("tool_type", data["alias"])),
        tool_id=data.get("tool_id"),
        use_mode=ToolUseMode(data.get("use_mode", ToolUseMode.GENERAL.value)),
        control_mode=ResourceControlMode(data.get("control_mode", ResourceControlMode.ROBOT_OPERATED.value)),
        acquire_policy=AcquirePolicy(data.get("acquire_policy", AcquirePolicy.PICK_FROM_LOCATION.value)),
        pickup_location=_location(data.get("pickup_location")),
        return_location=_location(data.get("return_location")),
        calibration_required=bool(data.get("calibration_required", False)),
        settings=dict(data.get("settings", {})),
        required_capabilities=[str(item) for item in data.get("required_capabilities", [])],
        required_authorizations=[str(item) for item in data.get("required_authorizations", [])],
        required_for_steps=[str(item) for item in data.get("required_for_steps", [])],
        safety_notes=str(data.get("safety_notes", "")),
    )


def _vehicle(data: dict[str, Any]) -> VehicleRequirement:
    return VehicleRequirement(
        alias=str(data["alias"]),
        vehicle_type=str(data.get("vehicle_type", data["alias"])),
        vehicle_id=data.get("vehicle_id"),
        use_mode=VehicleUseMode(data.get("use_mode", VehicleUseMode.OPERATE.value)),
        control_mode=ResourceControlMode(data.get("control_mode", ResourceControlMode.ROBOT_OPERATED.value)),
        interface_type=data.get("interface_type"),
        acquire_policy=AcquirePolicy(data.get("acquire_policy", AcquirePolicy.RESERVED_RESOURCE.value)),
        pickup_location=_location(data.get("pickup_location")),
        return_location=_location(data.get("return_location")),
        payload_capacity_kg=data.get("payload_capacity_kg"),
        allowed_routes=[str(item) for item in data.get("allowed_routes", [])],
        required_capabilities=[str(item) for item in data.get("required_capabilities", [])],
        required_authorizations=[str(item) for item in data.get("required_authorizations", [])],
        required_for_steps=[str(item) for item in data.get("required_for_steps", [])],
        safety_notes=str(data.get("safety_notes", "")),
    )


def _equipment(data: dict[str, Any]) -> EquipmentRequirement:
    return EquipmentRequirement(
        alias=str(data["alias"]),
        equipment_type=str(data.get("equipment_type", data["alias"])),
        equipment_id=data.get("equipment_id"),
        use_mode=EquipmentUseMode(data.get("use_mode", EquipmentUseMode.OTHER.value)),
        control_mode=ResourceControlMode(data.get("control_mode", ResourceControlMode.PASSIVE.value)),
        interface_type=data.get("interface_type"),
        location=_location(data.get("location")),
        settings=dict(data.get("settings", {})),
        required_capabilities=[str(item) for item in data.get("required_capabilities", [])],
        required_authorizations=[str(item) for item in data.get("required_authorizations", [])],
        required_for_steps=[str(item) for item in data.get("required_for_steps", [])],
        safety_notes=str(data.get("safety_notes", "")),
    )


def _safety(data: dict[str, Any]) -> SafetyConstraint:
    data = data if isinstance(data, dict) else {}
    return SafetyConstraint(
        risk_level=RiskLevel(data.get("risk_level", RiskLevel.LOW.value)),
        human_clearance_required=bool(data.get("human_clearance_required", False)),
        lockout_tagout_required=bool(data.get("lockout_tagout_required", False)),
        ppe_required=[str(item) for item in data.get("ppe_required", [])],
        allowed_zones=[str(item) for item in data.get("allowed_zones", [])],
        forbidden_zones=[str(item) for item in data.get("forbidden_zones", [])],
        max_payload_kg=data.get("max_payload_kg"),
        max_speed_mps=data.get("max_speed_mps"),
        max_force_n=data.get("max_force_n"),
        max_torque_nm=data.get("max_torque_nm"),
        required_authorizations=[str(item) for item in data.get("required_authorizations", [])],
        notes=str(data.get("notes", "")),
    )


def _step(data: dict[str, Any]) -> StepCall:
    retry_data = data.get("retry", {})
    expected_level = data.get("expected_level")
    return StepCall(
        step_id=str(data["step_id"]),
        call_code=str(data["call_code"]),
        args=dict(data.get("args", {})),
        expected_level=TaskLevel(expected_level) if expected_level else None,
        depends_on=[str(item) for item in data.get("depends_on", [])],
        optional=bool(data.get("optional", False)),
        timeout_s=data.get("timeout_s"),
        retry=RetryPolicy(
            max_attempts=int(retry_data.get("max_attempts", 1)),
            retry_on=[str(item) for item in retry_data.get("retry_on", [])],
            recovery_step_code=retry_data.get("recovery_step_code"),
        ),
        uses_tools=[str(item) for item in data.get("uses_tools", [])],
        uses_vehicles=[str(item) for item in data.get("uses_vehicles", [])],
        uses_equipment=[str(item) for item in data.get("uses_equipment", [])],
        preconditions=[_condition(row) for row in data.get("preconditions", [])],
        success_criteria=[_success(row) for row in data.get("success_criteria", [])],
    )
