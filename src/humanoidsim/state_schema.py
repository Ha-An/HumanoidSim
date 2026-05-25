"""
Humanoid robot state schema.

TaskSpec and StepCall describe what a humanoid is trying to do. This module
describes the humanoid's current operational state while that work is assigned
or running.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any

from .task_schema import ExecutionStatus


class AvailabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class MobilityState(str, Enum):
    STATIONARY = "STATIONARY"
    NAVIGATING = "NAVIGATING"
    DOCKING = "DOCKING"


class PowerState(str, Enum):
    POWER_NORMAL = "POWER_NORMAL"
    POWER_LOW = "POWER_LOW"
    POWER_CRITICAL = "POWER_CRITICAL"
    DEPLETED = "DEPLETED"
    CHARGING = "CHARGING"


class ManipulationState(str, Enum):
    FREE = "FREE"
    REACHING = "REACHING"
    HOLDING = "HOLDING"
    PLACING = "PLACING"


@dataclass
class TaskContext:
    task_code: str | None = None
    task_instance_id: str | None = None
    step_id: str | None = None
    primitive_call_code: str | None = None
    execution_status: ExecutionStatus | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TaskContext | None":
        if not data:
            return None
        status = data.get("execution_status")
        return cls(
            task_code=_optional_str(data.get("task_code")),
            task_instance_id=_optional_str(data.get("task_instance_id")),
            step_id=_optional_str(data.get("step_id")),
            primitive_call_code=_optional_str(data.get("primitive_call_code")),
            execution_status=ExecutionStatus(status) if status else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class StateReason:
    code: str
    message: str = ""
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StateReason | None":
        if not data:
            return None
        return cls(
            code=str(data.get("code", "")),
            message=str(data.get("message", "")),
            source=str(data.get("source", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class HumanoidStateSnapshot:
    humanoid_id: str
    availability: AvailabilityState = AvailabilityState.AVAILABLE
    mobility: MobilityState = MobilityState.STATIONARY
    power: PowerState = PowerState.POWER_NORMAL
    manipulation: ManipulationState = ManipulationState.FREE
    task_context: TaskContext | None = None
    reason: StateReason | None = None
    timestamp_s: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HumanoidStateSnapshot":
        reason_data = data.get("reason", data.get("state_reason"))
        return cls(
            humanoid_id=str(data.get("humanoid_id") or data.get("robot_id") or data.get("id") or "HUMANOID-01"),
            availability=AvailabilityState(data.get("availability", AvailabilityState.AVAILABLE.value)),
            mobility=MobilityState(data.get("mobility", MobilityState.STATIONARY.value)),
            power=PowerState(data.get("power", PowerState.POWER_NORMAL.value)),
            manipulation=ManipulationState(data.get("manipulation", ManipulationState.FREE.value)),
            task_context=TaskContext.from_dict(data.get("task_context")),
            reason=StateReason.from_dict(reason_data),
            timestamp_s=data.get("timestamp_s"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PrimitiveStateHint:
    mobility: MobilityState | None = None
    power: PowerState | None = None
    manipulation: ManipulationState | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PrimitiveStateProfile:
    call_code: str
    availability_running: AvailabilityState = AvailabilityState.EXECUTING
    allowed: dict[str, list[str]] = field(default_factory=dict)
    effects: dict[str, PrimitiveStateHint] = field(default_factory=dict)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, call_code: str, data: dict[str, Any] | None) -> "PrimitiveStateProfile":
        payload = dict(data or {})
        availability_payload = payload.get("availability", {})
        if isinstance(availability_payload, dict):
            running = availability_payload.get("running", AvailabilityState.EXECUTING.value)
        else:
            running = availability_payload or AvailabilityState.EXECUTING.value
        effects_payload = payload.get("effects", {})
        return cls(
            call_code=str(call_code).upper(),
            availability_running=AvailabilityState(str(running)),
            allowed={
                str(axis): [str(value) for value in values]
                for axis, values in (payload.get("allowed", {}) or {}).items()
                if isinstance(values, list)
            },
            effects={
                str(name): _hint_from_dict(effect)
                for name, effect in (effects_payload or {}).items()
                if isinstance(effect, dict)
            },
            description=str(payload.get("description", "")),
            metadata=dict(payload.get("metadata", {})),
        )

    def effect_for(self, *, finished: bool = False) -> PrimitiveStateHint:
        return self.effects.get("on_end" if finished else "on_start", PrimitiveStateHint())

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability": {"running": self.availability_running.value},
            "allowed": _jsonable(self.allowed),
            "effects": {name: hint.to_dict() for name, hint in self.effects.items()},
            **({"description": self.description} if self.description else {}),
            **({"metadata": _jsonable(self.metadata)} if self.metadata else {}),
        }


@dataclass
class StateTransitionEvent:
    event_type: str
    task_code: str | None = None
    task_instance_id: str | None = None
    step_id: str | None = None
    primitive_call_code: str | None = None
    execution_status: ExecutionStatus | str | None = None
    reason: StateReason | dict[str, Any] | None = None
    timestamp_s: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateTransitionEvent":
        return cls(
            event_type=str(data.get("event_type", "")),
            task_code=_optional_str(data.get("task_code")),
            task_instance_id=_optional_str(data.get("task_instance_id")),
            step_id=_optional_str(data.get("step_id")),
            primitive_call_code=_optional_str(data.get("primitive_call_code")),
            execution_status=data.get("execution_status"),
            reason=data.get("reason"),
            timestamp_s=data.get("timestamp_s"),
            metadata=dict(data.get("metadata", {})),
        )

    def normalized_type(self) -> str:
        return str(self.event_type or "").strip().lower().replace("-", "_")

    def reason_obj(self) -> StateReason | None:
        if isinstance(self.reason, StateReason):
            return self.reason
        if isinstance(self.reason, dict):
            return StateReason.from_dict(self.reason)
        reason_code = str(self.metadata.get("reason_code", "") or "").strip()
        if reason_code:
            return StateReason(
                code=reason_code,
                message=str(self.metadata.get("reason_message", "")),
                source=str(self.metadata.get("source", "")),
                metadata=dict(self.metadata.get("reason_metadata", {}) or {}),
            )
        return None


class StateTransitionError(ValueError):
    """Raised when a HumanoidStateSnapshot transition violates HumanoidSim schema."""


@dataclass
class StateDefinition:
    value: str
    description: str = ""
    relation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateAxisDefinition:
    axis_id: str
    name: str
    description: str
    default: str
    states: dict[str, StateDefinition] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, axis_id: str, data: dict[str, Any]) -> "StateAxisDefinition":
        states: dict[str, StateDefinition] = {}
        rows = data.get("states", [])
        if isinstance(rows, dict):
            rows = [{"value": value, **payload} for value, payload in rows.items()]
        for row in rows:
            value = str(row["value"])
            states[value] = StateDefinition(
                value=value,
                description=str(row.get("description", "")),
                relation=str(row.get("relation", "")),
                metadata=dict(row.get("metadata", {})),
            )
        return cls(
            axis_id=axis_id,
            name=str(data.get("name", axis_id)),
            description=str(data.get("description", "")),
            default=str(data.get("default", "")),
            states=states,
        )

    def has_state(self, value: str) -> bool:
        return value in self.states


@dataclass
class StateValidationIssue:
    field: str
    code: str
    message: str


@dataclass
class StateSchema:
    schema_version: str
    name: str
    axes: dict[str, StateAxisDefinition]
    primitive_state_hints: dict[str, dict[str, str]] = field(default_factory=dict)
    primitive_state_profiles: dict[str, PrimitiveStateProfile] = field(default_factory=dict)
    transitions: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    standard_reason_codes: list[dict[str, str]] = field(default_factory=list)
    customization: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateSchema":
        profiles = {
            str(call_code).upper(): PrimitiveStateProfile.from_dict(str(call_code), payload)
            for call_code, payload in data.get("primitive_state_profiles", {}).items()
        }
        for call_code, payload in data.get("primitive_state_hints", {}).items():
            key = str(call_code).upper()
            profiles.setdefault(key, _profile_from_legacy_hint(key, payload if isinstance(payload, dict) else {}))
        return cls(
            schema_version=str(data.get("schema_version", "0.1.0")),
            name=str(data.get("name", "Humanoid State Schema")),
            axes={
                axis_id: StateAxisDefinition.from_dict(axis_id, axis_data)
                for axis_id, axis_data in data.get("axes", {}).items()
            },
            primitive_state_hints={
                str(call_code): {str(key): str(value) for key, value in payload.items()}
                for call_code, payload in data.get("primitive_state_hints", {}).items()
            },
            primitive_state_profiles=profiles,
            transitions={
                str(axis): {
                    str(source): [str(target) for target in targets]
                    for source, targets in axis_transitions.items()
                    if isinstance(targets, list)
                }
                for axis, axis_transitions in data.get("transitions", {}).items()
                if isinstance(axis_transitions, dict)
            },
            standard_reason_codes=[
                {"code": str(row.get("code", "")), "description": str(row.get("description", ""))}
                for row in data.get("standard_reason_codes", [])
                if isinstance(row, dict)
            ],
            customization=dict(data.get("customization", {})),
        )

    def validate_snapshot(self, snapshot: HumanoidStateSnapshot | dict[str, Any]) -> list[StateValidationIssue]:
        payload = snapshot.to_dict() if isinstance(snapshot, HumanoidStateSnapshot) else dict(snapshot)
        issues: list[StateValidationIssue] = []

        for axis_id, axis in self.axes.items():
            value = payload.get(axis_id)
            if value is None:
                issues.append(StateValidationIssue(axis_id, "MISSING_STATE", f"{axis_id} is required."))
            elif not axis.has_state(str(value)):
                issues.append(StateValidationIssue(axis_id, "UNKNOWN_STATE", f"{value!r} is not defined for {axis_id}."))

        availability = str(payload.get("availability", ""))
        if availability in {AvailabilityState.WAITING.value, AvailabilityState.BLOCKED.value, AvailabilityState.DISABLED.value}:
            reason = payload.get("reason") or {}
            if not isinstance(reason, dict) or not str(reason.get("code", "")).strip():
                issues.append(
                    StateValidationIssue(
                        "reason",
                        "MISSING_STATE_REASON",
                        f"{availability} requires a reason.code.",
                    )
                )

        return issues

    def primitive_profile(self, primitive_call_code: str, *, task_code: str | None = None) -> PrimitiveStateProfile:
        call_code = str(primitive_call_code or "").upper()
        scoped_key = f"{call_code}:{str(task_code or '').upper()}" if task_code else ""
        if scoped_key and scoped_key in self.primitive_state_profiles:
            return self.primitive_state_profiles[scoped_key]
        if call_code in self.primitive_state_profiles:
            return self.primitive_state_profiles[call_code]
        raise KeyError(f"Primitive state profile is not defined for {call_code!r}.")

    def validate_profile(self, profile: PrimitiveStateProfile) -> list[StateValidationIssue]:
        issues: list[StateValidationIssue] = []
        if profile.availability_running != AvailabilityState.EXECUTING:
            issues.append(
                StateValidationIssue(
                    f"primitive_state_profiles.{profile.call_code}.availability.running",
                    "INVALID_RUNNING_AVAILABILITY",
                    "All running primitives must use availability=EXECUTING.",
                )
            )
        for axis, values in profile.allowed.items():
            definition = self.axes.get(axis)
            if definition is None:
                issues.append(
                    StateValidationIssue(
                        f"primitive_state_profiles.{profile.call_code}.allowed.{axis}",
                        "UNKNOWN_AXIS",
                        f"{axis!r} is not a known state axis.",
                    )
                )
                continue
            for value in values:
                if not definition.has_state(str(value)):
                    issues.append(
                        StateValidationIssue(
                            f"primitive_state_profiles.{profile.call_code}.allowed.{axis}",
                            "UNKNOWN_STATE",
                            f"{value!r} is not defined for {axis}.",
                        )
                    )
        for effect_name, hint in profile.effects.items():
            for axis, value in hint.to_dict().items():
                if value is None:
                    continue
                definition = self.axes.get(axis)
                if definition is None:
                    issues.append(
                        StateValidationIssue(
                            f"primitive_state_profiles.{profile.call_code}.effects.{effect_name}.{axis}",
                            "UNKNOWN_AXIS",
                            f"{axis!r} is not a known state axis.",
                        )
                    )
                elif not definition.has_state(str(value)):
                    issues.append(
                        StateValidationIssue(
                            f"primitive_state_profiles.{profile.call_code}.effects.{effect_name}.{axis}",
                            "UNKNOWN_STATE",
                            f"{value!r} is not defined for {axis}.",
                        )
                    )
        return issues


DEFAULT_HUMANOID_STATE = HumanoidStateSnapshot(humanoid_id="HUMANOID-01")

_AXIS_ENUMS = {
    "availability": AvailabilityState,
    "mobility": MobilityState,
    "power": PowerState,
    "manipulation": ManipulationState,
}

_TERMINAL_AVAILABILITY = {AvailabilityState.OFFLINE, AvailabilityState.DISABLED, AvailabilityState.BLOCKED}


def default_humanoid_state(humanoid_id: str = "HUMANOID-01") -> HumanoidStateSnapshot:
    return HumanoidStateSnapshot(humanoid_id=humanoid_id)


def parse_humanoid_state_snapshot(data: dict[str, Any]) -> HumanoidStateSnapshot:
    return HumanoidStateSnapshot.from_dict(data)


def derive_availability_state(
    *,
    has_task: bool = False,
    step_running: bool = False,
    waiting: bool = False,
    blocked: bool = False,
    offline: bool = False,
    disabled: bool = False,
) -> AvailabilityState:
    if offline:
        return AvailabilityState.OFFLINE
    if disabled:
        return AvailabilityState.DISABLED
    if blocked:
        return AvailabilityState.BLOCKED
    if waiting:
        return AvailabilityState.WAITING
    if step_running:
        return AvailabilityState.EXECUTING
    if has_task:
        return AvailabilityState.ASSIGNED
    return AvailabilityState.AVAILABLE


def build_state_snapshot_for_task_lifecycle(
    humanoid_id: str,
    *,
    task_code: str | None = None,
    task_instance_id: str | None = None,
    step_id: str | None = None,
    primitive_call_code: str | None = None,
    execution_status: ExecutionStatus | str | None = None,
    waiting_reason: StateReason | None = None,
    blocked_reason: StateReason | None = None,
    disabled_reason: StateReason | None = None,
    offline: bool = False,
    disabled: bool = False,
    timestamp_s: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> HumanoidStateSnapshot:
    has_task = any([task_code, task_instance_id])
    waiting = waiting_reason is not None
    blocked = blocked_reason is not None
    availability = derive_availability_state(
        has_task=has_task,
        step_running=primitive_call_code is not None or step_id is not None,
        waiting=waiting,
        blocked=blocked,
        offline=offline,
        disabled=disabled or disabled_reason is not None,
    )
    reason = disabled_reason or blocked_reason or waiting_reason
    context = None
    if any([task_code, task_instance_id, step_id, primitive_call_code, execution_status]):
        context = TaskContext(
            task_code=task_code,
            task_instance_id=task_instance_id,
            step_id=step_id,
            primitive_call_code=primitive_call_code,
            execution_status=_execution_status(execution_status),
        )
    snapshot = HumanoidStateSnapshot(
        humanoid_id=humanoid_id,
        availability=availability,
        task_context=context,
        reason=reason,
        timestamp_s=timestamp_s,
        metadata=dict(metadata or {}),
    )
    if primitive_call_code and availability not in {
        AvailabilityState.OFFLINE,
        AvailabilityState.DISABLED,
        AvailabilityState.BLOCKED,
    }:
        snapshot = apply_primitive_state_hint(snapshot, primitive_call_code, task_code=task_code)
    return snapshot


def primitive_state_hint(
    primitive_call_code: str,
    *,
    task_code: str | None = None,
    primitive_finished: bool = False,
) -> PrimitiveStateHint:
    try:
        profile = get_primitive_state_profile(primitive_call_code, task_code=task_code)
    except KeyError:
        return PrimitiveStateHint()
    return profile.effect_for(finished=primitive_finished)


def apply_primitive_state_hint(
    snapshot: HumanoidStateSnapshot,
    primitive_call_code: str,
    *,
    task_code: str | None = None,
    primitive_finished: bool = False,
) -> HumanoidStateSnapshot:
    event = StateTransitionEvent(
        event_type="primitive_finished" if primitive_finished else "primitive_started",
        task_code=task_code or (snapshot.task_context.task_code if snapshot.task_context else None),
        task_instance_id=snapshot.task_context.task_instance_id if snapshot.task_context else None,
        step_id=snapshot.task_context.step_id if snapshot.task_context else None,
        primitive_call_code=primitive_call_code,
        execution_status=ExecutionStatus.SUCCESS if primitive_finished else ExecutionStatus.RUNNING,
        timestamp_s=snapshot.timestamp_s,
        metadata={"strict": False},
    )
    return transition_humanoid_state(snapshot, event)


def get_primitive_state_profile(
    primitive_call_code: str,
    *,
    task_code: str | None = None,
    schema: StateSchema | None = None,
) -> PrimitiveStateProfile:
    return (schema or load_state_schema()).primitive_profile(primitive_call_code, task_code=task_code)


def validate_primitive_state_profile(
    profile: PrimitiveStateProfile | dict[str, Any],
    *,
    call_code: str | None = None,
    schema: StateSchema | None = None,
) -> list[StateValidationIssue]:
    loaded_schema = schema or load_state_schema()
    profile_obj = profile if isinstance(profile, PrimitiveStateProfile) else PrimitiveStateProfile.from_dict(call_code or "", profile)
    return loaded_schema.validate_profile(profile_obj)


def transition_humanoid_state(
    snapshot: HumanoidStateSnapshot | dict[str, Any],
    event: StateTransitionEvent | dict[str, Any],
    *,
    schema: StateSchema | None = None,
    strict: bool = True,
) -> HumanoidStateSnapshot:
    loaded_schema = schema or load_state_schema()
    previous = snapshot if isinstance(snapshot, HumanoidStateSnapshot) else HumanoidStateSnapshot.from_dict(snapshot)
    transition_event = event if isinstance(event, StateTransitionEvent) else StateTransitionEvent.from_dict(event)
    event_type = transition_event.normalized_type()
    metadata = dict(previous.metadata)
    metadata.update(dict(transition_event.metadata or {}))
    timestamp_s = transition_event.timestamp_s if transition_event.timestamp_s is not None else previous.timestamp_s
    reason = transition_event.reason_obj()

    next_snapshot = replace(previous, timestamp_s=timestamp_s, metadata=metadata)

    def _axis_reason() -> StateReason | None:
        # Axis-only events such as power or cargo changes must not erase the
        # reason for an unresolved WAITING/BLOCKED/DISABLED availability state.
        return reason if reason is not None else next_snapshot.reason

    if event_type in {"task_assigned", "assigned"}:
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.ASSIGNED,
            task_context=_event_context(transition_event, default_status=ExecutionStatus.PENDING),
            reason=None,
        )
    elif event_type in {"task_started", "task_start"}:
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.EXECUTING,
            task_context=_event_context(transition_event, default_status=ExecutionStatus.RUNNING),
            reason=None,
        )
    elif event_type in {"task_completed", "task_finished", "available"}:
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.AVAILABLE,
            mobility=MobilityState.STATIONARY,
            power=PowerState.POWER_NORMAL if metadata.get("power_normal", True) else next_snapshot.power,
            manipulation=ManipulationState.HOLDING if _metadata_bool(metadata, "cargo_present") else ManipulationState.FREE,
            task_context=None,
            reason=None,
        )
    elif event_type in {"task_failed", "blocked", "task_blocked"}:
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.BLOCKED,
            mobility=MobilityState.STATIONARY if event_type == "task_failed" else next_snapshot.mobility,
            task_context=_event_context(transition_event, default_status=ExecutionStatus.FAILED),
            reason=reason or StateReason(code=str(metadata.get("reason_code") or "blocked"), source=str(metadata.get("source", ""))),
        )
    elif event_type in {"waiting", "task_waiting"}:
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.WAITING,
            task_context=_event_context(transition_event, default_status=ExecutionStatus.RUNNING) or next_snapshot.task_context,
            reason=reason or StateReason(code=str(metadata.get("reason_code") or "waiting"), source=str(metadata.get("source", ""))),
        )
    elif event_type in {"disabled", "battery_depleted"}:
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.DISABLED,
            mobility=MobilityState.STATIONARY,
            power=PowerState.DEPLETED,
            reason=reason or StateReason(code=str(metadata.get("reason_code") or "disabled"), source=str(metadata.get("source", ""))),
        )
    elif event_type == "offline":
        next_snapshot = replace(
            next_snapshot,
            availability=AvailabilityState.OFFLINE,
            mobility=MobilityState.STATIONARY,
            reason=reason,
        )
    elif event_type in {"cargo_changed", "cargo_picked", "cargo_dropped"}:
        cargo_present = event_type == "cargo_picked" or _metadata_bool(metadata, "cargo_present")
        if event_type == "cargo_dropped":
            cargo_present = False
        next_snapshot = replace(
            next_snapshot,
            manipulation=ManipulationState.HOLDING if cargo_present else ManipulationState.FREE,
            reason=_axis_reason(),
        )
    elif event_type in {"primitive_started", "primitive_start", "primitive_finished", "primitive_end"}:
        finished = event_type in {"primitive_finished", "primitive_end"}
        next_snapshot = _transition_primitive(next_snapshot, transition_event, loaded_schema, finished=finished)
    elif event_type in {"power_charging"}:
        next_snapshot = replace(next_snapshot, power=PowerState.CHARGING, reason=_axis_reason())
    elif event_type in {"power_normal"}:
        next_snapshot = replace(next_snapshot, power=PowerState.POWER_NORMAL, reason=_axis_reason())
    elif event_type in {"power_low"}:
        next_snapshot = replace(next_snapshot, power=PowerState.POWER_LOW, reason=_axis_reason())
    elif event_type in {"power_critical"}:
        next_snapshot = replace(next_snapshot, power=PowerState.POWER_CRITICAL, reason=_axis_reason())
    else:
        raise StateTransitionError(f"Unknown humanoid state transition event_type={transition_event.event_type!r}.")

    validate_state_transition(previous, next_snapshot, transition_event, schema=loaded_schema, strict=strict)
    return next_snapshot


def validate_state_transition(
    previous: HumanoidStateSnapshot | dict[str, Any],
    next_snapshot: HumanoidStateSnapshot | dict[str, Any],
    event: StateTransitionEvent | dict[str, Any],
    *,
    schema: StateSchema | None = None,
    strict: bool = True,
) -> list[StateValidationIssue]:
    loaded_schema = schema or load_state_schema()
    prev = previous if isinstance(previous, HumanoidStateSnapshot) else HumanoidStateSnapshot.from_dict(previous)
    nxt = next_snapshot if isinstance(next_snapshot, HumanoidStateSnapshot) else HumanoidStateSnapshot.from_dict(next_snapshot)
    transition_event = event if isinstance(event, StateTransitionEvent) else StateTransitionEvent.from_dict(event)
    issues = loaded_schema.validate_snapshot(nxt)
    for axis in ("availability", "mobility", "power", "manipulation"):
        source = getattr(prev, axis).value
        target = getattr(nxt, axis).value
        if source == target:
            continue
        allowed = loaded_schema.transitions.get(axis, {}).get(source)
        if allowed is not None and target not in allowed:
            issues.append(
                StateValidationIssue(
                    axis,
                    "INVALID_STATE_TRANSITION",
                    f"{axis} cannot transition from {source} to {target} for event {transition_event.event_type}.",
                )
            )

    event_type = transition_event.normalized_type()
    if event_type in {"primitive_started", "primitive_start", "primitive_finished", "primitive_end"}:
        try:
            profile = loaded_schema.primitive_profile(
                transition_event.primitive_call_code or "",
                task_code=transition_event.task_code,
            )
        except KeyError as exc:
            issues.append(StateValidationIssue("primitive_call_code", "UNKNOWN_PRIMITIVE_PROFILE", str(exc)))
        else:
            issues.extend(loaded_schema.validate_profile(profile))
            if nxt.availability not in _TERMINAL_AVAILABILITY and nxt.availability != profile.availability_running:
                issues.append(
                    StateValidationIssue(
                        "availability",
                        "INVALID_PRIMITIVE_AVAILABILITY",
                        f"{profile.call_code} must run with availability={profile.availability_running.value}.",
                    )
                )
            for axis, values in profile.allowed.items():
                current_value = getattr(nxt, axis).value
                if current_value not in values:
                    issues.append(
                        StateValidationIssue(
                            axis,
                            "PRIMITIVE_STATE_NOT_ALLOWED",
                            f"{profile.call_code} does not allow {axis}={current_value}.",
                        )
                    )

    if issues and strict:
        message = "; ".join(f"{issue.field}:{issue.code}:{issue.message}" for issue in issues)
        raise StateTransitionError(message)
    return issues


def _transition_primitive(
    snapshot: HumanoidStateSnapshot,
    event: StateTransitionEvent,
    schema: StateSchema,
    *,
    finished: bool,
) -> HumanoidStateSnapshot:
    try:
        profile = schema.primitive_profile(event.primitive_call_code or "", task_code=event.task_code)
    except KeyError as exc:
        raise StateTransitionError(str(exc)) from exc
    context = _event_context(
        event,
        default_status=ExecutionStatus.SUCCESS if finished else ExecutionStatus.RUNNING,
    )
    availability = snapshot.availability
    if availability not in _TERMINAL_AVAILABILITY:
        availability = profile.availability_running
    hint = profile.effect_for(finished=finished)
    return replace(
        snapshot,
        availability=availability,
        mobility=hint.mobility or snapshot.mobility,
        power=hint.power or snapshot.power,
        manipulation=hint.manipulation or snapshot.manipulation,
        task_context=context or snapshot.task_context,
        reason=None if availability == AvailabilityState.EXECUTING else snapshot.reason,
    )


def _event_context(event: StateTransitionEvent, *, default_status: ExecutionStatus | None) -> TaskContext | None:
    if not any([event.task_code, event.task_instance_id, event.step_id, event.primitive_call_code, event.execution_status, default_status]):
        return None
    return TaskContext(
        task_code=event.task_code,
        task_instance_id=event.task_instance_id,
        step_id=event.step_id,
        primitive_call_code=event.primitive_call_code,
        execution_status=_execution_status(event.execution_status) or default_status,
    )


def _metadata_bool(metadata: dict[str, Any], key: str) -> bool:
    value = metadata.get(key)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _hint_from_dict(payload: dict[str, Any]) -> PrimitiveStateHint:
    return PrimitiveStateHint(
        mobility=MobilityState(payload["mobility"]) if payload.get("mobility") else None,
        power=PowerState(payload["power"]) if payload.get("power") else None,
        manipulation=ManipulationState(payload["manipulation"]) if payload.get("manipulation") else None,
    )


def _profile_from_legacy_hint(call_code: str, payload: dict[str, str]) -> PrimitiveStateProfile:
    return PrimitiveStateProfile(
        call_code=str(call_code).upper(),
        allowed=_default_allowed_for_primitive(str(call_code).upper(), payload),
        effects={"on_start": _hint_from_dict(payload)},
    )


def _default_allowed_for_primitive(call_code: str, effect: dict[str, str] | None = None) -> dict[str, list[str]]:
    effect = effect or {}
    mobility = [MobilityState.STATIONARY.value]
    manipulation = [state.value for state in ManipulationState]
    power = [state.value for state in PowerState]
    if effect.get("mobility"):
        mobility = [str(effect["mobility"])]
    if effect.get("manipulation"):
        manipulation = [str(effect["manipulation"])]
    return {"mobility": mobility, "manipulation": manipulation, "power": power}


def load_state_schema(path: Path | str | None = None) -> StateSchema:
    schema_path = Path(path) if path is not None else _project_root() / "data" / "state_schema_core.json"
    return StateSchema.from_dict(json.loads(schema_path.read_text(encoding="utf-8")))


def validate_state_snapshot(
    snapshot: HumanoidStateSnapshot | dict[str, Any],
    *,
    schema: StateSchema | None = None,
) -> list[StateValidationIssue]:
    return (schema or load_state_schema()).validate_snapshot(snapshot)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _execution_status(value: ExecutionStatus | str | None) -> ExecutionStatus | None:
    if value is None or isinstance(value, ExecutionStatus):
        return value
    return ExecutionStatus(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


__all__ = [
    "AvailabilityState",
    "DEFAULT_HUMANOID_STATE",
    "HumanoidStateSnapshot",
    "ManipulationState",
    "MobilityState",
    "PowerState",
    "PrimitiveStateHint",
    "PrimitiveStateProfile",
    "StateAxisDefinition",
    "StateDefinition",
    "StateReason",
    "StateSchema",
    "StateTransitionError",
    "StateTransitionEvent",
    "StateValidationIssue",
    "TaskContext",
    "apply_primitive_state_hint",
    "build_state_snapshot_for_task_lifecycle",
    "default_humanoid_state",
    "derive_availability_state",
    "get_primitive_state_profile",
    "load_state_schema",
    "parse_humanoid_state_snapshot",
    "primitive_state_hint",
    "transition_humanoid_state",
    "validate_primitive_state_profile",
    "validate_state_snapshot",
    "validate_state_transition",
]
