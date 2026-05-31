from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .catalog import TaskCatalog, load_task_catalog
from .execution import HumanoidProfile, expand_task_steps, validate_task_sequence
from .incident_schema import IncidentSchema, build_incident_transition_event, load_incident_schema
from .state_schema import (
    AvailabilityState,
    HumanoidStateSnapshot,
    StateReason,
    StateSchema,
    StateTransitionError,
    StateTransitionEvent,
    default_humanoid_state,
    load_state_schema,
    transition_humanoid_state,
)
from .task_schema import ExecutionStatus, TaskInstance, TaskLevel, TaskSpec


@dataclass
class InteractiveTraceConfig:
    humanoid_id: str = "LAB-H1"
    task_instance_id: str = "LAB-TASK-1"
    step_duration_s: float = 1.0
    max_steps: int = 200


@dataclass
class InteractiveTraceResult:
    ok: bool
    trace_type: str
    humanoid_id: str
    session_id: str
    summary: dict[str, Any]
    events: list[dict[str, Any]]
    issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "trace_type": self.trace_type,
            "humanoid_id": self.humanoid_id,
            "session_id": self.session_id,
            "summary": self.summary,
            "events": self.events,
            "issues": self.issues,
        }


def run_task_trace(
    task_code: str,
    args: dict[str, Any] | None = None,
    *,
    humanoid_id: str = "LAB-H1",
    instance_id: str = "LAB-TASK-1",
    catalog: TaskCatalog | None = None,
    state_schema: StateSchema | None = None,
    config: InteractiveTraceConfig | None = None,
) -> InteractiveTraceResult:
    catalog = catalog or load_task_catalog()
    state_schema = state_schema or load_state_schema()
    cfg = config or InteractiveTraceConfig(humanoid_id=humanoid_id, task_instance_id=instance_id)
    humanoid_id = humanoid_id or cfg.humanoid_id
    instance_id = instance_id or cfg.task_instance_id
    args = dict(args or {})

    issues: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    snapshot = default_humanoid_state(humanoid_id)
    time_s = 0.0
    spec = catalog.get(task_code)
    profile = HumanoidProfile(
        humanoid_id=humanoid_id,
        capabilities=["*"],
        supported_tools=["*"],
        supported_vehicles=["*"],
        supported_equipment=["*"],
        max_payload_kg=10_000.0,
    )
    validation = validate_task_sequence(
        profile,
        [TaskInstance(instance_id=instance_id, task_code=task_code, args=args, assigned_robot_id=humanoid_id)],
        catalog=catalog,
    )
    for issue in validation.issues:
        issues.append(
            {
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "task_code": issue.task_code,
                "instance_id": issue.instance_id,
            }
        )

    for lifecycle in (
        StateTransitionEvent(event_type="task_assigned", task_code=task_code, task_instance_id=instance_id, timestamp_s=time_s),
        StateTransitionEvent(event_type="task_started", task_code=task_code, task_instance_id=instance_id, timestamp_s=time_s),
    ):
        before = snapshot
        snapshot, transition_issue = _transition(snapshot, lifecycle, state_schema)
        if transition_issue:
            issues.append(transition_issue)
        events.append(_event_row(lifecycle.event_type, lifecycle, before, snapshot, time_s, duration_s=0.0))

    try:
        rows = expand_task_steps(task_code, args, catalog=catalog)
    except Exception as exc:  # noqa: BLE001 - interactive trace should return a visible failure.
        issues.append({"severity": "error", "code": "TASK_EXPANSION_FAILED", "message": str(exc), "task_code": task_code})
        rows = []

    for row in rows[: cfg.max_steps]:
        if row.get("call_level") != TaskLevel.PRIMITIVE_SKILL.value:
            events.append(_task_boundary_row(row, time_s, task_code, instance_id, humanoid_id, recovery=False))
            continue

        owner_task = str(row.get("parent_task_code") or task_code)
        primitive_code = str(row.get("call_code", ""))
        step_id = str(row.get("step_id", primitive_code))
        time_s += cfg.step_duration_s
        start_event = StateTransitionEvent(
            event_type="primitive_started",
            task_code=owner_task,
            task_instance_id=instance_id,
            step_id=step_id,
            primitive_call_code=primitive_code,
            execution_status=ExecutionStatus.RUNNING,
            timestamp_s=time_s,
        )
        before = snapshot
        snapshot, transition_issue = _transition(snapshot, start_event, state_schema)
        if transition_issue:
            issues.append(transition_issue)
        events.append(_event_row("primitive_started", start_event, before, snapshot, time_s, row=row, duration_s=cfg.step_duration_s))

        time_s += cfg.step_duration_s
        end_event = StateTransitionEvent(
            event_type="primitive_finished",
            task_code=owner_task,
            task_instance_id=instance_id,
            step_id=step_id,
            primitive_call_code=primitive_code,
            execution_status=ExecutionStatus.SUCCESS,
            timestamp_s=time_s,
        )
        before = snapshot
        snapshot, transition_issue = _transition(snapshot, end_event, state_schema)
        if transition_issue:
            issues.append(transition_issue)
        events.append(_event_row("primitive_finished", end_event, before, snapshot, time_s, row=row, duration_s=0.0))

    before = snapshot
    completed = StateTransitionEvent(event_type="task_completed", task_code=task_code, task_instance_id=instance_id, timestamp_s=time_s)
    snapshot, transition_issue = _transition(snapshot, completed, state_schema)
    if transition_issue:
        issues.append(transition_issue)
    events.append(_event_row("task_completed", completed, before, snapshot, time_s, duration_s=0.0))

    return InteractiveTraceResult(
        ok=validation.ok and not any(row.get("severity") == "error" for row in issues),
        trace_type="task",
        humanoid_id=humanoid_id,
        session_id=instance_id,
        summary={
            "task_code": task_code,
            "task_name": spec.name,
            "instance_id": instance_id,
            "duration_s": round(time_s, 3),
            "event_count": len(events),
            "final_state": snapshot.to_dict(),
        },
        events=events,
        issues=issues,
    )


def run_incident_trace(
    incident_code: str,
    context: dict[str, Any] | None = None,
    *,
    humanoid_id: str = "LAB-H1",
    catalog: TaskCatalog | None = None,
    state_schema: StateSchema | None = None,
    incident_schema: IncidentSchema | None = None,
    config: InteractiveTraceConfig | None = None,
) -> InteractiveTraceResult:
    catalog = catalog or load_task_catalog()
    state_schema = state_schema or load_state_schema()
    incident_schema = incident_schema or load_incident_schema()
    cfg = config or InteractiveTraceConfig(humanoid_id=humanoid_id)
    context = dict(context or {})
    humanoid_id = humanoid_id or cfg.humanoid_id
    profile = incident_schema.get(incident_code)
    task_code = str(context.get("task_code") or "TRANSFER")
    instance_id = str(context.get("task_instance_id") or f"INC-{profile.code}")

    issues: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    snapshot = default_humanoid_state(humanoid_id)
    time_s = 0.0

    for lifecycle in (
        StateTransitionEvent(event_type="task_assigned", task_code=task_code, task_instance_id=instance_id, timestamp_s=time_s),
        StateTransitionEvent(event_type="task_started", task_code=task_code, task_instance_id=instance_id, timestamp_s=time_s),
    ):
        before = snapshot
        snapshot, transition_issue = _transition(snapshot, lifecycle, state_schema)
        if transition_issue:
            issues.append(transition_issue)
        events.append(_event_row(lifecycle.event_type, lifecycle, before, snapshot, time_s, duration_s=0.0))

    before = snapshot
    incident_event = build_incident_transition_event(
        profile.code,
        task_code=task_code,
        task_instance_id=instance_id,
        primitive_call_code=context.get("primitive_call_code") or (profile.trigger_primitives[0] if profile.trigger_primitives else None),
        timestamp_s=time_s,
        schema=incident_schema,
    )
    snapshot, transition_issue = _transition(snapshot, incident_event, state_schema)
    if transition_issue:
        issues.append(transition_issue)
    events.append(_event_row("incident", incident_event, before, snapshot, time_s, duration_s=0.0, recovery=True))

    if snapshot.availability == AvailabilityState.WAITING:
        before = snapshot
        blocked = StateTransitionEvent(
            event_type="blocked",
            task_code=task_code,
            task_instance_id=instance_id,
            reason=snapshot.reason or StateReason(code=profile.code),
            timestamp_s=time_s,
        )
        snapshot, transition_issue = _transition(snapshot, blocked, state_schema)
        if transition_issue:
            issues.append(transition_issue)
        events.append(_event_row("recovery_blocked", blocked, before, snapshot, time_s, duration_s=0.0, recovery=True))

    for recovery_step in profile.recovery_protocol[: cfg.max_steps]:
        rows = _recovery_rows(recovery_step, catalog, issues)
        for row in rows:
            if row.get("call_level") != TaskLevel.PRIMITIVE_SKILL.value:
                events.append(_task_boundary_row(row, time_s, task_code, instance_id, humanoid_id, recovery=True))
                continue

            primitive_code = str(row.get("call_code", ""))
            step_id = str(row.get("step_id", primitive_code))
            time_s += cfg.step_duration_s
            start_event = StateTransitionEvent(
                event_type="primitive_started",
                task_code=recovery_step.code if recovery_step.kind == "task" else "RECOVERY",
                task_instance_id=instance_id,
                step_id=step_id,
                primitive_call_code=primitive_code,
                execution_status=ExecutionStatus.RUNNING,
                timestamp_s=time_s,
                metadata={"recovery": True, "incident_code": profile.code},
            )
            before = snapshot
            snapshot, transition_issue = _transition(snapshot, start_event, state_schema)
            if transition_issue:
                issues.append(transition_issue)
            events.append(_event_row("recovery_primitive_started", start_event, before, snapshot, time_s, row=row, duration_s=cfg.step_duration_s, recovery=True))

            time_s += cfg.step_duration_s
            end_event = StateTransitionEvent(
                event_type="primitive_finished",
                task_code=recovery_step.code if recovery_step.kind == "task" else "RECOVERY",
                task_instance_id=instance_id,
                step_id=step_id,
                primitive_call_code=primitive_code,
                execution_status=ExecutionStatus.SUCCESS,
                timestamp_s=time_s,
                metadata={"recovery": True, "incident_code": profile.code},
            )
            before = snapshot
            snapshot, transition_issue = _transition(snapshot, end_event, state_schema)
            if transition_issue:
                issues.append(transition_issue)
            events.append(_event_row("recovery_primitive_finished", end_event, before, snapshot, time_s, row=row, duration_s=0.0, recovery=True))

    return InteractiveTraceResult(
        ok=not any(row.get("severity") == "error" for row in issues),
        trace_type="incident",
        humanoid_id=humanoid_id,
        session_id=instance_id,
        summary={
            "incident_code": profile.code,
            "category": profile.category,
            "default_availability": profile.default_availability.value,
            "duration_s": round(time_s, 3),
            "event_count": len(events),
            "final_state": snapshot.to_dict(),
            "recovery_protocol": [step.to_dict() for step in profile.recovery_protocol],
        },
        events=events,
        issues=issues,
    )


def _recovery_rows(recovery_step: Any, catalog: TaskCatalog, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if recovery_step.kind == "primitive":
        return [
            {
                "path": f"RECOVERY/{recovery_step.code}",
                "depth": 1,
                "parent_task_code": "RECOVERY",
                "call_code": recovery_step.code,
                "call_level": TaskLevel.PRIMITIVE_SKILL.value,
                "step_id": recovery_step.code,
                "args": {},
                "depends_on": [],
            }
        ]
    if recovery_step.kind == "task":
        try:
            spec = catalog.get(recovery_step.code)
            return expand_task_steps(spec.code, _mock_args_for_spec(spec), catalog=catalog)
        except Exception as exc:  # noqa: BLE001
            issues.append(
                {
                    "severity": "error",
                    "code": "RECOVERY_TASK_EXPANSION_FAILED",
                    "message": str(exc),
                    "task_code": recovery_step.code,
                }
            )
            return []
    issues.append(
        {
            "severity": "error",
            "code": "UNKNOWN_RECOVERY_STEP_KIND",
            "message": str(recovery_step.kind),
            "task_code": recovery_step.code,
        }
    )
    return []


def _transition(
    snapshot: HumanoidStateSnapshot,
    event: StateTransitionEvent,
    schema: StateSchema,
) -> tuple[HumanoidStateSnapshot, dict[str, Any] | None]:
    try:
        return transition_humanoid_state(snapshot, event, schema=schema), None
    except StateTransitionError as exc:
        return snapshot, {
            "severity": "error",
            "code": "INVALID_STATE_TRANSITION",
            "message": str(exc),
            "event": event.__dict__,
            "previous": snapshot.to_dict(),
        }


def _event_row(
    kind: str,
    event: StateTransitionEvent,
    before: HumanoidStateSnapshot,
    after: HumanoidStateSnapshot,
    time_s: float,
    *,
    row: dict[str, Any] | None = None,
    duration_s: float,
    recovery: bool = False,
) -> dict[str, Any]:
    primitive_code = str(event.primitive_call_code or "")
    display_code = f"{primitive_code} (RECOVERY)" if recovery and primitive_code else primitive_code
    return {
        "kind": kind,
        "time_s": round(time_s, 3),
        "duration_s": round(duration_s, 3),
        "task_code": event.task_code,
        "task_instance_id": event.task_instance_id,
        "step_id": event.step_id,
        "primitive_call_code": primitive_code or None,
        "display_code": display_code or event.event_type,
        "is_recovery": recovery,
        "path": row.get("path") if row else None,
        "depth": row.get("depth") if row else None,
        "args": row.get("args", {}) if row else {},
        "state_before": before.to_dict(),
        "state_after": after.to_dict(),
        "motion_hint": _motion_hint(primitive_code, after),
        "manipulation_hint": _manipulation_hint(primitive_code, after),
    }


def _task_boundary_row(
    row: dict[str, Any],
    time_s: float,
    task_code: str,
    instance_id: str,
    humanoid_id: str,
    *,
    recovery: bool,
) -> dict[str, Any]:
    snapshot = default_humanoid_state(humanoid_id)
    snapshot.task_context = None
    code = str(row.get("call_code", ""))
    return {
        "kind": "recovery_task_boundary" if recovery else "task_boundary",
        "time_s": round(time_s, 3),
        "duration_s": 0.0,
        "task_code": task_code,
        "task_instance_id": instance_id,
        "step_id": row.get("step_id"),
        "primitive_call_code": None,
        "display_code": f"{code} (RECOVERY)" if recovery else code,
        "is_recovery": recovery,
        "path": row.get("path"),
        "depth": row.get("depth"),
        "args": row.get("args", {}),
        "state_before": snapshot.to_dict(),
        "state_after": snapshot.to_dict(),
        "motion_hint": {"type": "task_boundary"},
        "manipulation_hint": {"type": "none"},
    }


def _motion_hint(primitive_code: str, snapshot: HumanoidStateSnapshot) -> dict[str, Any]:
    code = primitive_code.upper()
    if code == "NAVIGATE_TO":
        return {"type": "translate", "distance_m": 0.8, "heading_rad": 0.0}
    if code == "ALIGN":
        return {"type": "rotate", "angle_rad": 1.5708}
    if snapshot.mobility.value == "DOCKING":
        return {"type": "dock"}
    if snapshot.mobility.value == "NAVIGATING":
        return {"type": "translate", "distance_m": 0.5, "heading_rad": 0.0}
    return {"type": "stationary"}


def _manipulation_hint(primitive_code: str, snapshot: HumanoidStateSnapshot) -> dict[str, Any]:
    code = primitive_code.upper()
    if code in {"REACH_TO", "GRASP", "LIFT", "PLACE", "RELEASE"}:
        return {"type": code.lower()}
    if snapshot.manipulation.value != "FREE":
        return {"type": snapshot.manipulation.value.lower()}
    return {"type": "work"}


def _mock_args_for_spec(spec: TaskSpec) -> dict[str, Any]:
    return {param.name: _mock_value(param.name, param.type_hint, param.default, param.allowed_values) for param in spec.inputs}


def _mock_value(name: str, type_hint: str, default: Any, allowed_values: list[Any]) -> Any:
    if default is not None:
        return default
    if allowed_values:
        return allowed_values[0]
    normalized = name.lower()
    type_lower = str(type_hint).lower()
    if "entity" in type_lower or normalized in {"item", "material", "product", "component", "part", "tool"}:
        return {"entity_type": normalized or "item", "entity_id": f"MOCK-{normalized.upper() or 'ITEM'}-1", "weight_kg": 1.0}
    if "location" in type_lower or normalized in {"source", "destination", "location", "workstation"}:
        return {"location_id": f"MOCK-{normalized.upper() or 'LOCATION'}"}
    if "machine" in normalized or "equipment" in normalized:
        return {"entity_type": "equipment", "entity_id": f"MOCK-{normalized.upper()}"}
    if "int" in type_lower:
        return 1
    if "float" in type_lower or "number" in type_lower:
        return 1.0
    if "bool" in type_lower:
        return True
    if "list" in type_lower:
        return []
    if "dict" in type_lower:
        return {"value": f"mock_{normalized}"}
    return f"mock_{normalized or 'value'}"


def trace_to_json(trace: InteractiveTraceResult) -> str:
    return json.dumps(trace.to_dict(), ensure_ascii=False)


__all__ = [
    "InteractiveTraceConfig",
    "InteractiveTraceResult",
    "run_incident_trace",
    "run_task_trace",
    "trace_to_json",
]
