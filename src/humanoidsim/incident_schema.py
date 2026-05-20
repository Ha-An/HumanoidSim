"""General humanoid incident taxonomy and recovery protocol schema."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .catalog import TaskCatalog, find_project_root, load_task_catalog
from .state_schema import AvailabilityState, StateReason, StateTransitionEvent
from .task_schema import TaskLevel


@dataclass(frozen=True)
class IncidentCategory:
    id: str
    name: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IncidentCategory":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


@dataclass(frozen=True)
class RecoveryStep:
    kind: str
    code: str
    optional: bool = False
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryStep":
        return cls(
            kind=str(data.get("kind", "")).strip().lower(),
            code=str(data.get("code", "")).strip(),
            optional=bool(data.get("optional", False)),
            description=str(data.get("description", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


@dataclass(frozen=True)
class IncidentRetryPolicy:
    max_local_retries: int = 0
    retry_delay_min: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "IncidentRetryPolicy":
        data = data if isinstance(data, dict) else {}
        return cls(
            max_local_retries=max(0, int(data.get("max_local_retries", 0) or 0)),
            retry_delay_min=max(0.0, float(data.get("retry_delay_min", 0.0) or 0.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


@dataclass(frozen=True)
class IncidentProfile:
    code: str
    category: str
    severity: str = "warning"
    default_availability: AvailabilityState = AvailabilityState.BLOCKED
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    trigger_primitives: list[str] = field(default_factory=list)
    recovery_protocol: list[RecoveryStep] = field(default_factory=list)
    retry_policy: IncidentRetryPolicy = field(default_factory=IncidentRetryPolicy)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IncidentProfile":
        return cls(
            code=str(data.get("code", "")).strip().upper(),
            category=str(data.get("category", "")).strip(),
            severity=str(data.get("severity", "warning")).strip().lower() or "warning",
            default_availability=AvailabilityState(str(data.get("default_availability", AvailabilityState.BLOCKED.value))),
            description=str(data.get("description", "")),
            aliases=[str(item).strip() for item in data.get("aliases", []) if str(item).strip()],
            trigger_primitives=[str(item).strip() for item in data.get("trigger_primitives", []) if str(item).strip()],
            recovery_protocol=[RecoveryStep.from_dict(row) for row in data.get("recovery_protocol", [])],
            retry_policy=IncidentRetryPolicy.from_dict(data.get("retry_policy")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = dict(asdict(self))
        payload["default_availability"] = self.default_availability.value
        payload["recovery_protocol"] = [step.to_dict() for step in self.recovery_protocol]
        payload["retry_policy"] = self.retry_policy.to_dict()
        return payload


@dataclass(frozen=True)
class IncidentValidationIssue:
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))


@dataclass
class IncidentSchema:
    version: str
    categories: dict[str, IncidentCategory]
    incidents: dict[str, IncidentProfile]
    root: Path
    aliases: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, root: Path) -> "IncidentSchema":
        categories = {row.id: row for row in (IncidentCategory.from_dict(item) for item in data.get("categories", []))}
        incidents = {row.code: row for row in (IncidentProfile.from_dict(item) for item in data.get("incidents", []))}
        aliases: dict[str, str] = {}
        for code, profile in incidents.items():
            aliases[_normalize_lookup_key(code)] = code
            for alias in profile.aliases:
                alias_key = _normalize_lookup_key(alias)
                if alias_key:
                    aliases[alias_key] = code
        return cls(version=str(data.get("version", "0.1.0")), categories=categories, incidents=incidents, root=root, aliases=aliases)

    def get(self, code: str) -> IncidentProfile:
        normalized = _normalize_lookup_key(code)
        normalized = self.aliases.get(normalized, normalized)
        if normalized not in self.incidents:
            raise KeyError(f"Unknown humanoid incident code: {code}")
        return self.incidents[normalized]

    def validate(self, *, catalog: TaskCatalog | None = None) -> list[IncidentValidationIssue]:
        issues: list[IncidentValidationIssue] = []
        catalog = catalog or load_task_catalog(self.root, validate=True)
        primitive_codes = set(catalog.primitives)
        task_codes = set(catalog.tasks)
        for category_id, category in self.categories.items():
            if not category_id:
                issues.append(IncidentValidationIssue("categories", "MISSING_CATEGORY_ID", "Incident category id is required."))
            if not category.name:
                issues.append(IncidentValidationIssue(f"categories.{category_id}", "MISSING_CATEGORY_NAME", "Incident category name is required."))
        for code, profile in self.incidents.items():
            if not code:
                issues.append(IncidentValidationIssue("incidents", "MISSING_INCIDENT_CODE", "Incident code is required."))
            if profile.category not in self.categories:
                issues.append(IncidentValidationIssue(f"incidents.{code}.category", "UNKNOWN_CATEGORY", f"Unknown incident category {profile.category}."))
            if not profile.recovery_protocol:
                issues.append(IncidentValidationIssue(f"incidents.{code}.recovery_protocol", "MISSING_RECOVERY_PROTOCOL", "Recovery protocol is required."))
            for alias in profile.aliases:
                if not _normalize_lookup_key(alias):
                    issues.append(IncidentValidationIssue(f"incidents.{code}.aliases", "EMPTY_ALIAS", "Incident alias must not be empty."))
            for primitive in profile.trigger_primitives:
                if primitive not in primitive_codes:
                    issues.append(IncidentValidationIssue(f"incidents.{code}.trigger_primitives", "UNKNOWN_PRIMITIVE", f"Unknown trigger primitive {primitive}."))
            for step in profile.recovery_protocol:
                if step.kind == "primitive" and step.code not in primitive_codes:
                    issues.append(IncidentValidationIssue(f"incidents.{code}.recovery_protocol", "UNKNOWN_PRIMITIVE", f"Unknown recovery primitive {step.code}."))
                elif step.kind == "task" and step.code not in task_codes:
                    issues.append(IncidentValidationIssue(f"incidents.{code}.recovery_protocol", "UNKNOWN_TASK", f"Unknown recovery task {step.code}."))
                elif step.kind not in {"primitive", "task"}:
                    issues.append(IncidentValidationIssue(f"incidents.{code}.recovery_protocol", "UNKNOWN_RECOVERY_STEP_KIND", f"Unknown recovery step kind {step.kind}."))
        return issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "categories": [category.to_dict() for category in self.categories.values()],
            "incidents": [incident.to_dict() for incident in self.incidents.values()],
        }


def load_incident_schema(root: Path | str | None = None) -> IncidentSchema:
    project_root = find_project_root(root)
    path = project_root / "data" / "incident_schema_core.json"
    return IncidentSchema.from_dict(json.loads(path.read_text(encoding="utf-8")), root=project_root)


def _normalize_lookup_key(value: str) -> str:
    return str(value or "").strip().upper()


def get_incident_profile(code: str, *, schema: IncidentSchema | None = None) -> IncidentProfile:
    return (schema or load_incident_schema()).get(code)


def resolve_incident_code(code_or_alias: str, *, schema: IncidentSchema | None = None) -> str:
    return get_incident_profile(code_or_alias, schema=schema).code


def recovery_protocol_for_incident(code: str, *, schema: IncidentSchema | None = None) -> list[RecoveryStep]:
    return list(get_incident_profile(code, schema=schema).recovery_protocol)


def validate_incident_schema(schema: IncidentSchema | None = None, *, catalog: TaskCatalog | None = None) -> list[IncidentValidationIssue]:
    loaded = schema or load_incident_schema()
    return loaded.validate(catalog=catalog)


def build_incident_transition_event(
    code: str,
    *,
    task_code: str | None = None,
    task_instance_id: str | None = None,
    step_id: str | None = None,
    primitive_call_code: str | None = None,
    timestamp_s: float | None = None,
    message: str = "",
    source: str = "humanoidsim.incident",
    metadata: dict[str, Any] | None = None,
    schema: IncidentSchema | None = None,
) -> StateTransitionEvent:
    profile = get_incident_profile(code, schema=schema)
    if profile.default_availability == AvailabilityState.WAITING:
        event_type = "waiting"
    elif profile.default_availability == AvailabilityState.DISABLED:
        event_type = "disabled"
    else:
        event_type = "blocked"
    reason_metadata = {
        "incident_code": profile.code,
        "incident_category": profile.category,
        "severity": profile.severity,
        "recovery_protocol": [step.to_dict() for step in profile.recovery_protocol],
        "retry_policy": profile.retry_policy.to_dict(),
    }
    reason_metadata.update(dict(metadata or {}))
    return StateTransitionEvent(
        event_type=event_type,
        task_code=task_code,
        task_instance_id=task_instance_id,
        step_id=step_id,
        primitive_call_code=primitive_call_code,
        execution_status="FAILED" if event_type == "blocked" else "RUNNING",
        reason=StateReason(
            code=profile.code,
            message=message or profile.description,
            source=source,
            metadata=reason_metadata,
        ),
        timestamp_s=timestamp_s,
        metadata={
            "reason_code": profile.code,
            "reason_message": message or profile.description,
            "source": source,
            "incident_code": profile.code,
            "incident_category": profile.category,
            "incident_severity": profile.severity,
            "recovery_protocol": [step.to_dict() for step in profile.recovery_protocol],
            **dict(metadata or {}),
        },
    )


__all__ = [
    "IncidentCategory",
    "IncidentProfile",
    "IncidentRetryPolicy",
    "IncidentSchema",
    "IncidentValidationIssue",
    "RecoveryStep",
    "build_incident_transition_event",
    "get_incident_profile",
    "load_incident_schema",
    "recovery_protocol_for_incident",
    "resolve_incident_code",
    "validate_incident_schema",
]
