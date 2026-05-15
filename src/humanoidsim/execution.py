from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .catalog import TaskCatalog, load_task_catalog
from .task_schema import StepCall, TaskInstance, TaskLevel, TaskSpec


@dataclass
class HumanoidProfile:
    humanoid_id: str
    capabilities: list[str] = field(default_factory=list)
    max_payload_kg: float | None = None
    supported_tools: list[str] = field(default_factory=lambda: ["*"])
    supported_vehicles: list[str] = field(default_factory=lambda: ["*"])
    supported_equipment: list[str] = field(default_factory=lambda: ["*"])
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HumanoidProfile":
        return cls(
            humanoid_id=str(data.get("humanoid_id") or data.get("robot_id") or data.get("id") or "HUMANOID-01"),
            capabilities=[str(item) for item in data.get("capabilities", [])],
            max_payload_kg=data.get("max_payload_kg"),
            supported_tools=[str(item) for item in data.get("supported_tools", ["*"])],
            supported_vehicles=[str(item) for item in data.get("supported_vehicles", ["*"])],
            supported_equipment=[str(item) for item in data.get("supported_equipment", ["*"])],
            metadata=dict(data.get("metadata", {})),
        )

    def has_capability(self, capability: str) -> bool:
        return "*" in self.capabilities or capability in self.capabilities

    def supports_tool(self, alias: str, tool_type: str) -> bool:
        return _supports(self.supported_tools, alias, tool_type)

    def supports_vehicle(self, alias: str, vehicle_type: str) -> bool:
        return _supports(self.supported_vehicles, alias, vehicle_type)

    def supports_equipment(self, alias: str, equipment_type: str) -> bool:
        return _supports(self.supported_equipment, alias, equipment_type)


@dataclass
class TaskValidationIssue:
    severity: str
    code: str
    message: str
    instance_id: str | None = None
    task_code: str | None = None


@dataclass
class TaskValidationResult:
    instance_id: str
    task_code: str
    humanoid_id: str
    ok: bool
    issues: list[TaskValidationIssue] = field(default_factory=list)


@dataclass
class SequenceValidationResult:
    ok: bool
    task_results: list[TaskValidationResult]
    issues: list[TaskValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_sequence_file(path: Path | str) -> tuple[dict[str, HumanoidProfile], list[TaskInstance]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    profiles = {
        profile.humanoid_id: profile
        for profile in (HumanoidProfile.from_dict(row) for row in payload.get("humanoids", []))
    }
    instances = [_task_instance_from_dict(row) for row in payload.get("tasks", [])]
    return profiles, instances


def validate_task_sequence(
    profile: HumanoidProfile | dict[str, HumanoidProfile] | Iterable[HumanoidProfile],
    task_instances: Iterable[TaskInstance],
    *,
    catalog: TaskCatalog | None = None,
) -> SequenceValidationResult:
    catalog = catalog or load_task_catalog()
    profiles = _profile_map(profile)
    task_results: list[TaskValidationResult] = []
    sequence_issues: list[TaskValidationIssue] = []

    for instance in task_instances:
        humanoid_id = instance.assigned_robot_id or next(iter(profiles.keys()), "")
        humanoid = profiles.get(humanoid_id)
        if humanoid is None:
            issue = TaskValidationIssue(
                severity="error",
                code="UNKNOWN_HUMANOID",
                message=f"No HumanoidProfile found for assigned_robot_id={humanoid_id!r}.",
                instance_id=instance.instance_id,
                task_code=instance.task_code,
            )
            task_results.append(TaskValidationResult(instance.instance_id, instance.task_code, humanoid_id, False, [issue]))
            continue

        issues = _validate_one(humanoid, instance, catalog)
        task_results.append(TaskValidationResult(instance.instance_id, instance.task_code, humanoid_id, not _has_errors(issues), issues))

    for result in task_results:
        sequence_issues.extend(result.issues)
    return SequenceValidationResult(ok=not _has_errors(sequence_issues), task_results=task_results, issues=sequence_issues)


def expand_task_steps(
    task_code: str,
    args: dict[str, Any] | None = None,
    *,
    catalog: TaskCatalog | None = None,
) -> list[dict[str, Any]]:
    """Expand a task into nested step rows while preserving task boundaries.

    Composite tasks may call other tasks directly. This helper keeps every row
    in the plan, including child task rows and primitive leaf rows, so callers
    can either execute leaf primitives or display the parent/child workflow.
    """
    catalog = catalog or load_task_catalog()
    root_spec = catalog.get(task_code)
    rows: list[dict[str, Any]] = []
    _expand_steps_recursive(
        spec=root_spec,
        args=dict(args or {}),
        catalog=catalog,
        rows=rows,
        path_prefix=root_spec.code,
        depth=0,
        parent_task_code=None,
        stack=[],
    )
    return rows


def simulate_task_sequence(
    profile: HumanoidProfile | dict[str, HumanoidProfile] | Iterable[HumanoidProfile],
    task_instances: Iterable[TaskInstance],
    *,
    catalog: TaskCatalog | None = None,
    step_duration_s: float = 1.0,
) -> dict[str, Any]:
    catalog = catalog or load_task_catalog()
    profiles = _profile_map(profile)
    instances = list(task_instances)
    validation = validate_task_sequence(profiles, instances, catalog=catalog)
    task_ok = {row.instance_id: row.ok for row in validation.task_results}
    events: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    time_cursor = 0.0

    for instance in instances:
        spec = catalog.tasks.get(instance.task_code) or catalog.primitives.get(instance.task_code)
        if spec is None:
            continue
        humanoid_id = instance.assigned_robot_id or next(iter(profiles.keys()), "")
        frames = list(spec.metadata.get("animation", {}).get("frames", []))
        start = time_cursor
        step_rows = expand_task_steps(instance.task_code, instance.args, catalog=catalog)
        if not step_rows:
            step_rows = [
                {
                    "path": spec.code,
                    "depth": 0,
                    "parent_task_code": None,
                    "call_code": spec.code,
                    "call_level": spec.level.value,
                    "step_id": spec.code,
                    "args": dict(instance.args),
                    "depends_on": [],
                }
            ]
        for step in step_rows:
            end = time_cursor + step_duration_s
            events.append(
                {
                    "type": "step",
                    "humanoid_id": humanoid_id,
                    "instance_id": instance.instance_id,
                    "task_code": instance.task_code,
                    "path": step["path"],
                    "depth": step["depth"],
                    "parent_task_code": step["parent_task_code"],
                    "step_id": step["step_id"],
                    "call_code": step["call_code"],
                    "call_level": step["call_level"],
                    "start_s": round(time_cursor, 3),
                    "end_s": round(end, 3),
                    "status": "SUCCESS" if task_ok.get(instance.instance_id, False) else "FAILED",
                    "frames": frames,
                }
            )
            time_cursor = end
        if not step_rows:
            time_cursor += step_duration_s
        tasks.append(
            {
                "instance_id": instance.instance_id,
                "task_code": instance.task_code,
                "task_name": spec.name,
                "humanoid_id": humanoid_id,
                "start_s": round(start, 3),
                "end_s": round(time_cursor, 3),
                "status": "SUCCESS" if task_ok.get(instance.instance_id, False) else "FAILED",
                "frames": frames,
                "risk": spec.safety.risk_level.value,
                "category": spec.metadata.get("catalog", {}).get("category", ""),
            }
        )

    return {
        "duration_s": round(time_cursor, 3),
        "validation": validation.to_dict(),
        "tasks": tasks,
        "events": events,
    }


def _task_instance_from_dict(data: dict[str, Any]) -> TaskInstance:
    return TaskInstance(
        instance_id=str(data["instance_id"]),
        task_code=str(data["task_code"]),
        args=dict(data.get("args", {})),
        work_order_id=data.get("work_order_id"),
        assigned_robot_id=data.get("assigned_robot_id") or data.get("assigned_humanoid_id"),
        priority=int(data.get("priority", 0)),
        metadata=dict(data.get("metadata", {})),
    )


def _validate_one(profile: HumanoidProfile, instance: TaskInstance, catalog: TaskCatalog) -> list[TaskValidationIssue]:
    issues: list[TaskValidationIssue] = []
    try:
        spec = catalog.get(instance.task_code)
    except KeyError:
        return [
            TaskValidationIssue(
                severity="error",
                code="UNKNOWN_TASK",
                message=f"Unknown task_code={instance.task_code!r}.",
                instance_id=instance.instance_id,
                task_code=instance.task_code,
            )
        ]

    try:
        spec.validate_instance_args(instance.args)
    except ValueError as exc:
        issues.append(_issue("MISSING_INPUT", str(exc), instance, "error"))

    missing_caps = [cap for cap in spec.required_capabilities if not profile.has_capability(cap)]
    if missing_caps:
        issues.append(_issue("MISSING_CAPABILITY", f"Humanoid lacks capabilities: {missing_caps}", instance, "error"))

    _validate_payload(profile, instance, issues)
    _validate_resources(profile, spec, instance, issues)
    _validate_nested_task_calls(profile, spec, instance.args, catalog, instance, issues, path=spec.code, stack=[])
    _validate_animation(spec, catalog.root, instance, issues)
    return issues


def _expand_steps_recursive(
    *,
    spec: TaskSpec,
    args: dict[str, Any],
    catalog: TaskCatalog,
    rows: list[dict[str, Any]],
    path_prefix: str,
    depth: int,
    parent_task_code: str | None,
    stack: list[str],
) -> None:
    if spec.code in stack:
        raise ValueError(f"Task cycle detected while expanding: {' -> '.join(stack + [spec.code])}")

    for step in spec.steps:
        called = _get_called_spec(catalog, step.call_code)
        call_level = called.level if called is not None else step.expected_level
        if call_level is None:
            raise ValueError(f"{spec.code}.{step.step_id}: cannot determine level of {step.call_code}.")

        resolved_args = _resolve_step_args(step, args)
        row_path = f"{path_prefix}/{step.step_id}"
        rows.append(
            {
                "path": row_path,
                "depth": depth + 1,
                "parent_task_code": spec.code,
                "call_code": step.call_code,
                "call_level": call_level.value,
                "step_id": step.step_id,
                "args": resolved_args,
                "depends_on": list(step.depends_on),
                "optional": bool(step.optional),
            }
        )

        if called is not None and call_level != TaskLevel.PRIMITIVE_SKILL:
            child_args = dict(args)
            child_args.update(resolved_args)
            _expand_steps_recursive(
                spec=called,
                args=child_args,
                catalog=catalog,
                rows=rows,
                path_prefix=row_path,
                depth=depth + 1,
                parent_task_code=spec.code,
                stack=stack + [spec.code],
            )


def _validate_nested_task_calls(
    profile: HumanoidProfile,
    spec: TaskSpec,
    args: dict[str, Any],
    catalog: TaskCatalog,
    root_instance: TaskInstance,
    issues: list[TaskValidationIssue],
    *,
    path: str,
    stack: list[str],
) -> None:
    if spec.code in stack:
        issues.append(_issue("NESTED_TASK_CYCLE", f"Nested task cycle at {path}.", root_instance, "error"))
        return

    for step in spec.steps:
        called = _get_called_spec(catalog, step.call_code)
        if called is None or called.level == TaskLevel.PRIMITIVE_SKILL:
            continue

        child_args = dict(args)
        child_args.update(_resolve_step_args(step, args))
        child_instance = TaskInstance(
            instance_id=f"{root_instance.instance_id}:{step.step_id}",
            task_code=called.code,
            args=child_args,
            work_order_id=root_instance.work_order_id,
            assigned_robot_id=root_instance.assigned_robot_id,
            priority=root_instance.priority,
            metadata={"nested_path": f"{path}/{step.step_id}", "parent_task_code": spec.code},
        )

        try:
            called.validate_instance_args(child_args)
        except ValueError as exc:
            issues.append(
                TaskValidationIssue(
                    severity="error",
                    code="NESTED_MISSING_INPUT",
                    message=f"{path}/{step.step_id}: {exc}",
                    instance_id=root_instance.instance_id,
                    task_code=called.code,
                )
            )

        missing_caps = [cap for cap in called.required_capabilities if not profile.has_capability(cap)]
        if missing_caps:
            issues.append(
                TaskValidationIssue(
                    severity="error",
                    code="NESTED_MISSING_CAPABILITY",
                    message=f"{path}/{step.step_id}: Humanoid lacks capabilities for {called.code}: {missing_caps}",
                    instance_id=root_instance.instance_id,
                    task_code=called.code,
                )
            )

        _validate_payload(profile, child_instance, issues)
        _validate_resources(profile, called, child_instance, issues)
        _validate_nested_task_calls(
            profile,
            called,
            child_args,
            catalog,
            root_instance,
            issues,
            path=f"{path}/{step.step_id}",
            stack=stack + [spec.code],
        )


def _get_called_spec(catalog: TaskCatalog, code: str) -> TaskSpec | None:
    try:
        return catalog.get(code)
    except KeyError:
        return None


def _resolve_step_args(step: StepCall, parent_args: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in step.args.items():
        resolved_value, present = _resolve_arg_value(value, parent_args)
        if present:
            resolved[key] = resolved_value
    return resolved


def _resolve_arg_value(value: Any, parent_args: dict[str, Any]) -> tuple[Any, bool]:
    if isinstance(value, str) and value.startswith("$inputs."):
        input_name = value.removeprefix("$inputs.")
        if input_name not in parent_args:
            return None, False
        return parent_args[input_name], True

    if isinstance(value, list):
        output: list[Any] = []
        for item in value:
            resolved, present = _resolve_arg_value(item, parent_args)
            if present:
                output.append(resolved)
        return output, True

    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            resolved, present = _resolve_arg_value(item, parent_args)
            if present:
                output[str(key)] = resolved
        return output, True

    return value, True


def _validate_payload(profile: HumanoidProfile, instance: TaskInstance, issues: list[TaskValidationIssue]) -> None:
    if profile.max_payload_kg is None:
        return
    for key, value in instance.args.items():
        weight = value.get("weight_kg") if isinstance(value, dict) else None
        if isinstance(weight, (int, float)) and float(weight) > float(profile.max_payload_kg):
            issues.append(_issue("PAYLOAD_LIMIT", f"{key} weight_kg={weight} exceeds max_payload_kg={profile.max_payload_kg}.", instance, "error"))


def _validate_resources(profile: HumanoidProfile, spec: TaskSpec, instance: TaskInstance, issues: list[TaskValidationIssue]) -> None:
    optional = spec.metadata.get("resources", {}).get("optional_aliases", {})
    optional_tools = set(optional.get("tools", []))
    optional_vehicles = set(optional.get("vehicles", []))
    optional_equipment = set(optional.get("equipment", []))

    for tool in spec.required_tools:
        if tool.alias not in optional_tools and not profile.supports_tool(tool.alias, tool.tool_type):
            issues.append(_issue("UNSUPPORTED_TOOL", f"Unsupported tool: {tool.alias} ({tool.tool_type}).", instance, "error"))
    for vehicle in spec.required_vehicles:
        if vehicle.alias not in optional_vehicles and not profile.supports_vehicle(vehicle.alias, vehicle.vehicle_type):
            issues.append(_issue("UNSUPPORTED_VEHICLE", f"Unsupported vehicle: {vehicle.alias} ({vehicle.vehicle_type}).", instance, "error"))
    for equipment in spec.required_equipment:
        if equipment.alias not in optional_equipment and not profile.supports_equipment(equipment.alias, equipment.equipment_type):
            issues.append(_issue("UNSUPPORTED_EQUIPMENT", f"Unsupported equipment: {equipment.alias} ({equipment.equipment_type}).", instance, "error"))


def _validate_animation(spec: TaskSpec, root: Path, instance: TaskInstance, issues: list[TaskValidationIssue]) -> None:
    frames = spec.metadata.get("animation", {}).get("frames", [])
    if len(frames) != 2:
        issues.append(_issue("ANIMATION_FRAME_COUNT", f"{spec.code} must define exactly 2 animation frames.", instance, "error"))
        return
    for frame in frames:
        if not (root / str(frame)).exists():
            issues.append(_issue("ANIMATION_FRAME_MISSING", f"Animation frame does not exist: {frame}", instance, "error"))


def _issue(code: str, message: str, instance: TaskInstance, severity: str) -> TaskValidationIssue:
    return TaskValidationIssue(severity=severity, code=code, message=message, instance_id=instance.instance_id, task_code=instance.task_code)


def _supports(values: list[str], alias: str, resource_type: str) -> bool:
    normalized = {item.strip().lower() for item in values}
    return "*" in normalized or alias.lower() in normalized or resource_type.lower() in normalized


def _profile_map(profile: HumanoidProfile | dict[str, HumanoidProfile] | Iterable[HumanoidProfile]) -> dict[str, HumanoidProfile]:
    if isinstance(profile, HumanoidProfile):
        return {profile.humanoid_id: profile}
    if isinstance(profile, dict):
        return profile
    return {row.humanoid_id: row for row in profile}


def _has_errors(issues: Iterable[TaskValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)
