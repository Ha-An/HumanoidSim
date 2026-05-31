from __future__ import annotations

import html
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .catalog import TaskCatalog, find_project_root, load_task_catalog
from .execution import HumanoidProfile, expand_task_steps, validate_task_sequence
from .incident_schema import (
    IncidentSchema,
    build_incident_transition_event,
    load_incident_schema,
    validate_incident_schema,
)
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
    validate_primitive_state_profile,
)
from .task_schema import ExecutionStatus, TaskInstance, TaskLevel, TaskSpec


@dataclass
class LabIssue:
    severity: str
    code: str
    message: str
    subject: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ValidationLabConfig:
    seed: int = 42
    fuzz_cases: int = 200
    max_steps: int = 200
    step_duration_s: float = 1.0
    humanoid_id: str = "LAB-H1"


@dataclass
class ValidationLabResult:
    ok: bool
    output_dir: Path
    summary: dict[str, Any]
    issues: list[LabIssue]
    artifacts: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "output_dir": str(self.output_dir),
            "summary": _jsonable(self.summary),
            "issues": [issue.to_dict() for issue in self.issues],
            "artifacts": dict(self.artifacts),
        }


def run_validation_lab(
    *,
    out_dir: Path | str | None = None,
    root: Path | str | None = None,
    config: ValidationLabConfig | None = None,
) -> ValidationLabResult:
    """Run standalone HumanoidSim catalog, execution, recovery, and fuzz checks."""

    cfg = config or ValidationLabConfig()
    project_root = find_project_root(root)
    output_dir = _resolve_output_dir(project_root, out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog = load_task_catalog(project_root, validate=True)
    state_schema = load_state_schema(project_root / "data" / "state_schema_core.json")
    incident_schema = load_incident_schema(project_root)
    profile = HumanoidProfile(
        humanoid_id=cfg.humanoid_id,
        capabilities=["*"],
        supported_tools=["*"],
        supported_vehicles=["*"],
        supported_equipment=["*"],
        max_payload_kg=10_000.0,
    )

    issues: list[LabIssue] = []
    catalog_summary = _validate_catalog_definitions(catalog, state_schema, incident_schema, profile, issues)
    task_traces, transition_observations = _run_all_task_traces(catalog, state_schema, profile, cfg, issues)
    incident_traces, incident_observations = _run_all_incident_recovery_traces(catalog, state_schema, incident_schema, cfg, issues)
    transition_observations.extend(incident_observations)
    coverage = _build_transition_coverage(state_schema, transition_observations)
    fuzz_report = _run_fuzz_checks(catalog, state_schema, incident_schema, cfg, profile)
    for row in fuzz_report.get("failures", []):
        issues.append(
            LabIssue(
                severity="error",
                code="FUZZ_FAILURE",
                message=str(row.get("message", "Fuzz case failed.")),
                subject=str(row.get("subject", "")),
                context=dict(row),
            )
        )

    artifacts = _write_artifacts(
        output_dir=output_dir,
        catalog_summary=catalog_summary,
        task_traces=task_traces,
        incident_traces=incident_traces,
        coverage=coverage,
        fuzz_report=fuzz_report,
        issues=issues,
    )
    summary = {
        "ok": not any(issue.severity == "error" for issue in issues),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "catalog": catalog_summary,
        "task_trace_count": len(task_traces),
        "incident_trace_count": len(incident_traces),
        "transition_coverage": coverage.get("summary", {}),
        "fuzz": fuzz_report.get("summary", {}),
        "issue_counts": _issue_counts(issues),
        "artifacts": artifacts,
    }
    (output_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    artifacts["validation_summary.json"] = str((output_dir / "validation_summary.json").resolve())
    dashboard = _render_dashboard(summary, task_traces, incident_traces, coverage, fuzz_report, issues, project_root)
    dashboard_path = output_dir / "validation_dashboard.html"
    dashboard_path.write_text(dashboard, encoding="utf-8")
    artifacts["validation_dashboard.html"] = str(dashboard_path.resolve())

    return ValidationLabResult(
        ok=bool(summary["ok"]),
        output_dir=output_dir,
        summary=summary,
        issues=issues,
        artifacts=artifacts,
    )


def _validate_catalog_definitions(
    catalog: TaskCatalog,
    state_schema: StateSchema,
    incident_schema: IncidentSchema,
    profile: HumanoidProfile,
    issues: list[LabIssue],
) -> dict[str, Any]:
    state_profile_issues = []
    missing_profiles = []
    for primitive_code in sorted(catalog.primitives):
        try:
            profile_obj = state_schema.primitive_profile(primitive_code)
        except KeyError:
            missing_profiles.append(primitive_code)
            issues.append(
                LabIssue(
                    severity="error",
                    code="MISSING_PRIMITIVE_STATE_PROFILE",
                    message=f"Primitive {primitive_code} has no state profile.",
                    subject=primitive_code,
                )
            )
            continue
        for issue in validate_primitive_state_profile(profile_obj, schema=state_schema):
            state_profile_issues.append(issue)
            issues.append(
                LabIssue(
                    severity="error",
                    code=issue.code,
                    message=issue.message,
                    subject=issue.field,
                )
            )

    incident_issues = validate_incident_schema(incident_schema, catalog=catalog)
    for issue in incident_issues:
        issues.append(
            LabIssue(
                severity="error",
                code=issue.code,
                message=issue.message,
                subject=issue.field,
            )
        )

    task_validation_errors = 0
    for spec in catalog.tasks.values():
        instance = TaskInstance(
            instance_id=f"LAB-{spec.code}",
            task_code=spec.code,
            args=_mock_args_for_spec(spec),
            assigned_robot_id=profile.humanoid_id,
        )
        result = validate_task_sequence(profile, [instance], catalog=catalog)
        if not result.ok:
            task_validation_errors += 1
            for issue in result.issues:
                issues.append(
                    LabIssue(
                        severity=issue.severity,
                        code=issue.code,
                        message=issue.message,
                        subject=issue.task_code or spec.code,
                        context={"instance_id": issue.instance_id},
                    )
                )

    return {
        "task_count": catalog.task_count,
        "primitive_count": catalog.primitive_count,
        "incident_count": len(incident_schema.incidents),
        "state_axis_count": len(state_schema.axes),
        "missing_primitive_state_profiles": missing_profiles,
        "state_profile_issue_count": len(state_profile_issues),
        "incident_schema_issue_count": len(incident_issues),
        "task_validation_error_count": task_validation_errors,
    }


def _run_all_task_traces(
    catalog: TaskCatalog,
    state_schema: StateSchema,
    profile: HumanoidProfile,
    cfg: ValidationLabConfig,
    issues: list[LabIssue],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    traces: list[dict[str, Any]] = []
    observations: list[dict[str, str]] = []
    for spec in sorted(catalog.tasks.values(), key=lambda row: row.code):
        trace = _execute_task_trace(spec, catalog, state_schema, profile, cfg)
        traces.append(trace)
        observations.extend(trace.get("transition_observations", []))
        for failure in trace.get("failures", []):
            issues.append(
                LabIssue(
                    severity="error",
                    code=str(failure.get("code", "TASK_TRACE_FAILURE")),
                    message=str(failure.get("message", "")),
                    subject=spec.code,
                    context=dict(failure),
                )
            )
    return traces, observations


def _execute_task_trace(
    spec: TaskSpec,
    catalog: TaskCatalog,
    state_schema: StateSchema,
    profile: HumanoidProfile,
    cfg: ValidationLabConfig,
) -> dict[str, Any]:
    instance_id = f"LAB-{spec.code}"
    args = _mock_args_for_spec(spec)
    trace: dict[str, Any] = {
        "trace_type": "task",
        "task_code": spec.code,
        "instance_id": instance_id,
        "steps": [],
        "failures": [],
        "transition_observations": [],
    }
    validation = validate_task_sequence(
        profile,
        [TaskInstance(instance_id=instance_id, task_code=spec.code, args=args, assigned_robot_id=profile.humanoid_id)],
        catalog=catalog,
    )
    trace["task_validation_ok"] = validation.ok
    if not validation.ok:
        trace["failures"].extend(
            {
                "code": issue.code,
                "message": issue.message,
                "severity": issue.severity,
            }
            for issue in validation.issues
            if issue.severity == "error"
        )

    snapshot = default_humanoid_state(cfg.humanoid_id)
    time_cursor = 0.0
    for event in (
        StateTransitionEvent(event_type="task_assigned", task_code=spec.code, task_instance_id=instance_id, timestamp_s=time_cursor),
        StateTransitionEvent(event_type="task_started", task_code=spec.code, task_instance_id=instance_id, timestamp_s=time_cursor),
    ):
        snapshot = _safe_transition(snapshot, event, state_schema, trace)

    rows = expand_task_steps(spec.code, args, catalog=catalog)
    for row in rows[: cfg.max_steps]:
        if row["call_level"] != TaskLevel.PRIMITIVE_SKILL.value:
            trace["steps"].append(
                {
                    "kind": "task_boundary",
                    "path": row["path"],
                    "code": row["call_code"],
                    "level": row["call_level"],
                    "depth": row["depth"],
                }
            )
            continue
        owner_task = str(row.get("parent_task_code") or spec.code)
        time_cursor += cfg.step_duration_s
        before = snapshot
        start_event = StateTransitionEvent(
            event_type="primitive_started",
            task_code=owner_task,
            task_instance_id=instance_id,
            step_id=str(row["step_id"]),
            primitive_call_code=str(row["call_code"]),
            execution_status=ExecutionStatus.RUNNING,
            timestamp_s=time_cursor,
        )
        snapshot = _safe_transition(snapshot, start_event, state_schema, trace)
        _observe_transition(trace, before, snapshot, start_event)
        trace["steps"].append(_step_trace(row, "primitive_start", before, snapshot, recovery=False))

        time_cursor += cfg.step_duration_s
        before = snapshot
        end_event = StateTransitionEvent(
            event_type="primitive_finished",
            task_code=owner_task,
            task_instance_id=instance_id,
            step_id=str(row["step_id"]),
            primitive_call_code=str(row["call_code"]),
            execution_status=ExecutionStatus.SUCCESS,
            timestamp_s=time_cursor,
        )
        snapshot = _safe_transition(snapshot, end_event, state_schema, trace)
        _observe_transition(trace, before, snapshot, end_event)
        trace["steps"].append(_step_trace(row, "primitive_end", before, snapshot, recovery=False))

    before = snapshot
    snapshot = _safe_transition(
        snapshot,
        StateTransitionEvent(event_type="task_completed", task_code=spec.code, task_instance_id=instance_id, timestamp_s=time_cursor),
        state_schema,
        trace,
    )
    _observe_transition(trace, before, snapshot, StateTransitionEvent(event_type="task_completed"))
    trace["final_state"] = snapshot.to_dict()
    trace["ok"] = validation.ok and not trace["failures"]
    return trace


def _run_all_incident_recovery_traces(
    catalog: TaskCatalog,
    state_schema: StateSchema,
    incident_schema: IncidentSchema,
    cfg: ValidationLabConfig,
    issues: list[LabIssue],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    traces: list[dict[str, Any]] = []
    observations: list[dict[str, str]] = []
    for profile in sorted(incident_schema.incidents.values(), key=lambda row: row.code):
        trace = _execute_incident_trace(profile.code, catalog, state_schema, incident_schema, cfg)
        traces.append(trace)
        observations.extend(trace.get("transition_observations", []))
        for failure in trace.get("failures", []):
            issues.append(
                LabIssue(
                    severity="error",
                    code=str(failure.get("code", "INCIDENT_TRACE_FAILURE")),
                    message=str(failure.get("message", "")),
                    subject=profile.code,
                    context=dict(failure),
                )
            )
    return traces, observations


def _execute_incident_trace(
    incident_code: str,
    catalog: TaskCatalog,
    state_schema: StateSchema,
    incident_schema: IncidentSchema,
    cfg: ValidationLabConfig,
) -> dict[str, Any]:
    profile = incident_schema.get(incident_code)
    instance_id = f"INC-{profile.code}"
    trace: dict[str, Any] = {
        "trace_type": "incident",
        "incident_code": profile.code,
        "category": profile.category,
        "default_availability": profile.default_availability.value,
        "recovery_protocol": [step.to_dict() for step in profile.recovery_protocol],
        "steps": [],
        "failures": [],
        "transition_observations": [],
    }
    snapshot = default_humanoid_state(cfg.humanoid_id)
    snapshot = _safe_transition(
        snapshot,
        StateTransitionEvent(event_type="task_started", task_code="TRANSFER", task_instance_id=instance_id, timestamp_s=0.0),
        state_schema,
        trace,
    )
    before = snapshot
    incident_event = build_incident_transition_event(
        profile.code,
        task_code="TRANSFER",
        task_instance_id=instance_id,
        primitive_call_code=profile.trigger_primitives[0] if profile.trigger_primitives else None,
        timestamp_s=0.0,
        schema=incident_schema,
    )
    snapshot = _safe_transition(snapshot, incident_event, state_schema, trace)
    _observe_transition(trace, before, snapshot, incident_event)
    trace["incident_state"] = snapshot.to_dict()

    # Recovery procedures represent exception handling. For recoverable WAITING
    # incidents, move into BLOCKED before executing recovery steps so the trace
    # validates the documented recovery-state rule.
    if snapshot.availability == AvailabilityState.WAITING:
        before = snapshot
        snapshot = _safe_transition(
            snapshot,
            StateTransitionEvent(
                event_type="blocked",
                task_code="TRANSFER",
                task_instance_id=instance_id,
                reason=snapshot.reason or StateReason(code=profile.code),
                timestamp_s=0.0,
            ),
            state_schema,
            trace,
        )
        _observe_transition(trace, before, snapshot, StateTransitionEvent(event_type="blocked"))

    time_cursor = 0.0
    for recovery_step in profile.recovery_protocol[: cfg.max_steps]:
        if recovery_step.kind == "primitive":
            rows = [
                {
                    "path": f"{profile.code}/{recovery_step.code}",
                    "depth": 1,
                    "parent_task_code": "RECOVERY",
                    "call_code": recovery_step.code,
                    "call_level": TaskLevel.PRIMITIVE_SKILL.value,
                    "step_id": recovery_step.code,
                    "args": {},
                    "depends_on": [],
                }
            ]
        elif recovery_step.kind == "task":
            try:
                spec = catalog.get(recovery_step.code)
                rows = expand_task_steps(spec.code, _mock_args_for_spec(spec), catalog=catalog)
            except Exception as exc:  # noqa: BLE001 - validation trace must continue.
                trace["failures"].append({"code": "RECOVERY_TASK_EXPANSION_FAILED", "message": str(exc), "step": recovery_step.to_dict()})
                continue
        else:
            trace["failures"].append({"code": "UNKNOWN_RECOVERY_STEP_KIND", "message": recovery_step.kind, "step": recovery_step.to_dict()})
            continue

        for row in rows:
            if row["call_level"] != TaskLevel.PRIMITIVE_SKILL.value:
                trace["steps"].append(
                    {
                        "kind": "recovery_task_boundary",
                        "path": row["path"],
                        "code": row["call_code"],
                        "display_code": f"{row['call_code']} (RECOVERY)",
                        "level": row["call_level"],
                    }
                )
                continue
            time_cursor += cfg.step_duration_s
            before = snapshot
            start_event = StateTransitionEvent(
                event_type="primitive_started",
                task_code=recovery_step.code if recovery_step.kind == "task" else "RECOVERY",
                task_instance_id=instance_id,
                step_id=str(row["step_id"]),
                primitive_call_code=str(row["call_code"]),
                execution_status=ExecutionStatus.RUNNING,
                timestamp_s=time_cursor,
                metadata={"recovery": True, "incident_code": profile.code},
            )
            snapshot = _safe_transition(snapshot, start_event, state_schema, trace)
            _observe_transition(trace, before, snapshot, start_event)
            trace["steps"].append(_step_trace(row, "recovery_primitive_start", before, snapshot, recovery=True))

            time_cursor += cfg.step_duration_s
            before = snapshot
            end_event = StateTransitionEvent(
                event_type="primitive_finished",
                task_code=recovery_step.code if recovery_step.kind == "task" else "RECOVERY",
                task_instance_id=instance_id,
                step_id=str(row["step_id"]),
                primitive_call_code=str(row["call_code"]),
                execution_status=ExecutionStatus.SUCCESS,
                timestamp_s=time_cursor,
                metadata={"recovery": True, "incident_code": profile.code},
            )
            snapshot = _safe_transition(snapshot, end_event, state_schema, trace)
            _observe_transition(trace, before, snapshot, end_event)
            trace["steps"].append(_step_trace(row, "recovery_primitive_end", before, snapshot, recovery=True))

    trace["final_state"] = snapshot.to_dict()
    trace["ok"] = not trace["failures"]
    return trace


def _safe_transition(
    snapshot: HumanoidStateSnapshot,
    event: StateTransitionEvent,
    schema: StateSchema,
    trace: dict[str, Any],
) -> HumanoidStateSnapshot:
    try:
        return transition_humanoid_state(snapshot, event, schema=schema)
    except StateTransitionError as exc:
        trace.setdefault("failures", []).append(
            {
                "code": "INVALID_STATE_TRANSITION",
                "message": str(exc),
                "event": event.__dict__,
                "previous": snapshot.to_dict(),
            }
        )
        return snapshot


def _observe_transition(
    trace: dict[str, Any],
    before: HumanoidStateSnapshot,
    after: HumanoidStateSnapshot,
    event: StateTransitionEvent,
) -> None:
    for axis in ("availability", "mobility", "power", "manipulation"):
        source = getattr(before, axis).value
        target = getattr(after, axis).value
        if source == target:
            continue
        trace.setdefault("transition_observations", []).append(
            {"axis": axis, "source": source, "target": target, "event_type": event.event_type}
        )


def _step_trace(
    row: dict[str, Any],
    kind: str,
    before: HumanoidStateSnapshot,
    after: HumanoidStateSnapshot,
    *,
    recovery: bool,
) -> dict[str, Any]:
    code = str(row["call_code"])
    return {
        "kind": kind,
        "path": row["path"],
        "step_id": row["step_id"],
        "code": code,
        "display_code": f"{code} (RECOVERY)" if recovery else code,
        "level": row["call_level"],
        "parent_task_code": row.get("parent_task_code"),
        "before": before.to_dict(),
        "after": after.to_dict(),
    }


def _build_transition_coverage(schema: StateSchema, observations: Iterable[dict[str, str]]) -> dict[str, Any]:
    covered: dict[str, set[str]] = {}
    for observation in observations:
        axis = observation["axis"]
        key = f"{observation['source']}->{observation['target']}"
        covered.setdefault(axis, set()).add(key)

    axes: dict[str, Any] = {}
    total_defined = 0
    total_covered = 0
    for axis, graph in schema.transitions.items():
        defined_edges = [f"{source}->{target}" for source, targets in graph.items() for target in targets if source != target]
        covered_edges = sorted(set(defined_edges).intersection(covered.get(axis, set())))
        missing_edges = sorted(set(defined_edges).difference(covered.get(axis, set())))
        total_defined += len(set(defined_edges))
        total_covered += len(covered_edges)
        axes[axis] = {
            "defined_edge_count": len(set(defined_edges)),
            "covered_edge_count": len(covered_edges),
            "coverage_ratio": round(len(covered_edges) / max(1, len(set(defined_edges))), 4),
            "covered_edges": covered_edges,
            "missing_edges": missing_edges,
        }
    return {
        "summary": {
            "defined_edge_count": total_defined,
            "covered_edge_count": total_covered,
            "coverage_ratio": round(total_covered / max(1, total_defined), 4),
        },
        "axes": axes,
    }


def _run_fuzz_checks(
    catalog: TaskCatalog,
    state_schema: StateSchema,
    incident_schema: IncidentSchema,
    cfg: ValidationLabConfig,
    profile: HumanoidProfile,
) -> dict[str, Any]:
    rng = random.Random(cfg.seed)
    task_codes = sorted(catalog.tasks)
    incident_codes = sorted(incident_schema.incidents)
    failures: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    for index in range(cfg.fuzz_cases):
        task_code = rng.choice(task_codes)
        incident_code = rng.choice(incident_codes)
        try:
            task_trace = _execute_task_trace(catalog.tasks[task_code], catalog, state_schema, profile, cfg)
            if task_trace.get("failures"):
                failures.append(
                    {
                        "case": index,
                        "subject": task_code,
                        "message": "Task trace failed during fuzz.",
                        "failures": task_trace.get("failures", []),
                    }
                )
            if rng.random() < 0.5:
                incident_trace = _execute_incident_trace(incident_code, catalog, state_schema, incident_schema, cfg)
                if incident_trace.get("failures"):
                    failures.append(
                        {
                            "case": index,
                            "subject": incident_code,
                            "message": "Incident trace failed during fuzz.",
                            "failures": incident_trace.get("failures", []),
                        }
                    )
            cases.append({"case": index, "task_code": task_code, "incident_code": incident_code})
        except Exception as exc:  # noqa: BLE001 - fuzz should preserve reproducible failure details.
            failures.append({"case": index, "subject": task_code, "message": str(exc)})

    negative_checks = []
    try:
        transition_humanoid_state(
            default_humanoid_state(cfg.humanoid_id),
            StateTransitionEvent(event_type="primitive_started", task_code="TRANSFER", primitive_call_code="UNKNOWN_PRIMITIVE"),
            schema=state_schema,
        )
        negative_checks.append({"name": "unknown_primitive_rejected", "ok": False, "message": "UNKNOWN_PRIMITIVE did not fail."})
        failures.append({"subject": "UNKNOWN_PRIMITIVE", "message": "Negative transition check did not fail."})
    except StateTransitionError as exc:
        negative_checks.append({"name": "unknown_primitive_rejected", "ok": True, "message": str(exc)})

    return {
        "summary": {
            "seed": cfg.seed,
            "case_count": cfg.fuzz_cases,
            "failure_count": len(failures),
            "negative_check_count": len(negative_checks),
        },
        "cases": cases,
        "failures": failures,
        "negative_checks": negative_checks,
    }


def _write_artifacts(
    *,
    output_dir: Path,
    catalog_summary: dict[str, Any],
    task_traces: list[dict[str, Any]],
    incident_traces: list[dict[str, Any]],
    coverage: dict[str, Any],
    fuzz_report: dict[str, Any],
    issues: list[LabIssue],
) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    _write_jsonl(output_dir / "task_execution_traces.jsonl", task_traces)
    _write_jsonl(output_dir / "incident_recovery_traces.jsonl", incident_traces)
    (output_dir / "state_transition_coverage.json").write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "fuzz_report.json").write_text(json.dumps(fuzz_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "catalog_validation.json").write_text(json.dumps(catalog_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "validation_issues.json").write_text(
        json.dumps([issue.to_dict() for issue in issues], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    for name in (
        "task_execution_traces.jsonl",
        "incident_recovery_traces.jsonl",
        "state_transition_coverage.json",
        "fuzz_report.json",
        "catalog_validation.json",
        "validation_issues.json",
    ):
        artifacts[name] = str((output_dir / name).resolve())
    return artifacts


def _render_dashboard(
    summary: dict[str, Any],
    task_traces: list[dict[str, Any]],
    incident_traces: list[dict[str, Any]],
    coverage: dict[str, Any],
    fuzz_report: dict[str, Any],
    issues: list[LabIssue],
    project_root: Path,
) -> str:
    status = "PASS" if summary.get("ok") else "FAIL"
    issue_rows = "".join(
        "<tr>"
        f"<td>{html.escape(issue.severity)}</td>"
        f"<td>{html.escape(issue.code)}</td>"
        f"<td>{html.escape(issue.subject)}</td>"
        f"<td>{html.escape(issue.message)}</td>"
        "</tr>"
        for issue in issues[:200]
    ) or "<tr><td colspan='4'>No issues.</td></tr>"
    task_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('task_code', '')))}</td>"
        f"<td>{'PASS' if row.get('ok') else 'FAIL'}</td>"
        f"<td>{len(row.get('steps', []))}</td>"
        f"<td>{len(row.get('failures', []))}</td>"
        "</tr>"
        for row in task_traces
    )
    incident_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('incident_code', '')))}</td>"
        f"<td>{html.escape(str(row.get('category', '')))}</td>"
        f"<td>{html.escape(str(row.get('default_availability', '')))}</td>"
        f"<td>{'PASS' if row.get('ok') else 'FAIL'}</td>"
        f"<td>{len(row.get('steps', []))}</td>"
        "</tr>"
        for row in incident_traces
    )
    coverage_rows = "".join(
        "<tr>"
        f"<td>{html.escape(axis)}</td>"
        f"<td>{payload.get('covered_edge_count', 0)}</td>"
        f"<td>{payload.get('defined_edge_count', 0)}</td>"
        f"<td>{payload.get('coverage_ratio', 0):.2%}</td>"
        "</tr>"
        for axis, payload in coverage.get("axes", {}).items()
    )
    viewer_path = project_root / "outputs" / "task_sequence_viewer.html"
    viewer_link = (
        f"<a href='{html.escape(viewer_path.resolve().as_uri())}'>Open existing task sequence viewer</a>"
        if viewer_path.exists()
        else "Task sequence viewer has not been exported yet."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>HumanoidSim Validation Lab</title>
  <style>
    body {{ margin: 0; font-family: Inter, Segoe UI, Arial, sans-serif; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 28px; }}
    h1, h2 {{ margin: 0 0 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
    .card, .panel {{ background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 16px; }}
    .value {{ font-size: 28px; font-weight: 800; }}
    .label {{ color: #93c5fd; font-size: 12px; text-transform: uppercase; letter-spacing: .12em; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #263247; padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ color: #93c5fd; letter-spacing: .08em; text-transform: uppercase; font-size: 11px; }}
    section {{ margin-top: 20px; }}
    a {{ color: #7dd3fc; }}
    .pass {{ color: #5eead4; }}
    .fail {{ color: #fca5a5; }}
  </style>
</head>
<body>
<main>
  <p class="label">HumanoidSim Standalone</p>
  <h1>Validation Lab <span class="{status.lower()}">{status}</span></h1>
  <section class="grid">
    <div class="card"><div class="label">Tasks</div><div class="value">{summary['catalog']['task_count']}</div></div>
    <div class="card"><div class="label">Primitives</div><div class="value">{summary['catalog']['primitive_count']}</div></div>
    <div class="card"><div class="label">Incidents</div><div class="value">{summary['catalog']['incident_count']}</div></div>
    <div class="card"><div class="label">Issues</div><div class="value">{sum(summary['issue_counts'].values())}</div></div>
  </section>
  <section class="panel"><h2>Standalone Viewer</h2><p>{viewer_link}</p></section>
  <section class="panel"><h2>State Transition Coverage</h2><table><thead><tr><th>Axis</th><th>Covered</th><th>Defined</th><th>Ratio</th></tr></thead><tbody>{coverage_rows}</tbody></table></section>
  <section class="panel"><h2>Task Execution Traces</h2><table><thead><tr><th>Task</th><th>Status</th><th>Steps</th><th>Failures</th></tr></thead><tbody>{task_rows}</tbody></table></section>
  <section class="panel"><h2>Incident Recovery Traces</h2><table><thead><tr><th>Incident</th><th>Category</th><th>Default Availability</th><th>Status</th><th>Recovery Steps</th></tr></thead><tbody>{incident_rows}</tbody></table></section>
  <section class="panel"><h2>Fuzz</h2><p>Seed {fuzz_report['summary']['seed']}, cases {fuzz_report['summary']['case_count']}, failures {fuzz_report['summary']['failure_count']}.</p></section>
  <section class="panel"><h2>Issues</h2><table><thead><tr><th>Severity</th><th>Code</th><th>Subject</th><th>Message</th></tr></thead><tbody>{issue_rows}</tbody></table></section>
</main>
</body>
</html>"""


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


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _resolve_output_dir(project_root: Path, out_dir: Path | str | None) -> Path:
    if out_dir is not None:
        return Path(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return project_root / "outputs" / "validation" / stamp


def _issue_counts(issues: Iterable[LabIssue]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return counts


def _jsonable(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


__all__ = [
    "LabIssue",
    "ValidationLabConfig",
    "ValidationLabResult",
    "run_validation_lab",
]
