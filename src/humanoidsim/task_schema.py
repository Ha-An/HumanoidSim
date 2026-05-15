"""
Humanoid Manufacturing Task Schema
==================================

This module defines a common Python schema for representing humanoid-robot
manufacturing work as three levels:

1. Primitive Skill
   - The smallest semantic execution unit exposed to the task planner.
   - Example: NAVIGATE_TO, LOCALIZE_OBJECT, REACH_TO, GRASP, LIFT, PLACE.
   - A primitive has no child steps in this schema.

2. Atomic Task
   - A reusable task composed only of Primitive Skills.
   - Example: TRANSFER, FASTEN_SCREW, LOAD_MACHINE.

3. Composite Task
   - A workflow composed of Primitive Skills, Atomic Tasks, and/or other
     Composite Tasks.
   - Example: LINE_SIDE_REPLENISHMENT, CNC_TENDING_JOB.

The schema explicitly supports tasks that use tools and vehicles, such as
power tools, scanners, torque drivers, pallet jacks, carts, forklifts, tuggers,
and elevators.

The code is intentionally dependency-free and uses only Python standard library
features so it can be copied into another AI coding platform or production code
base easily.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, Iterable


# =============================================================================
# Enums
# =============================================================================

class TaskLevel(str, Enum):
    PRIMITIVE_SKILL = "PRIMITIVE_SKILL"
    ATOMIC_TASK = "ATOMIC_TASK"
    COMPOSITE_TASK = "COMPOSITE_TASK"


class ResourceControlMode(str, Enum):
    """Who or what controls the resource during the task."""
    ROBOT_OPERATED = "ROBOT_OPERATED"
    HUMAN_OPERATED = "HUMAN_OPERATED"
    AUTONOMOUS = "AUTONOMOUS"
    PASSIVE = "PASSIVE"


class AcquirePolicy(str, Enum):
    """How the robot obtains access to a resource."""
    ALREADY_AVAILABLE = "ALREADY_AVAILABLE"
    PICK_FROM_LOCATION = "PICK_FROM_LOCATION"
    RESERVED_RESOURCE = "RESERVED_RESOURCE"
    HUMAN_HANDOVER = "HUMAN_HANDOVER"
    USE_IN_PLACE = "USE_IN_PLACE"


class ToolUseMode(str, Enum):
    GENERAL = "GENERAL"
    FASTENING = "FASTENING"
    CUTTING = "CUTTING"
    MEASURING = "MEASURING"
    SCANNING = "SCANNING"
    DISPENSING = "DISPENSING"
    CLEANING = "CLEANING"
    GRIPPING = "GRIPPING"
    INSPECTION = "INSPECTION"


class VehicleUseMode(str, Enum):
    RIDE = "RIDE"
    OPERATE = "OPERATE"
    TOW = "TOW"
    PUSH_PULL = "PUSH_PULL"
    LIFT_AND_TRANSPORT = "LIFT_AND_TRANSPORT"


class EquipmentUseMode(str, Enum):
    MACHINE_INTERFACE = "MACHINE_INTERFACE"
    FIXTURE = "FIXTURE"
    TESTER = "TESTER"
    WORKSTATION = "WORKSTATION"
    CONTAINER = "CONTAINER"
    STORAGE = "STORAGE"
    OTHER = "OTHER"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    TIMEOUT = "TIMEOUT"
    UNSAFE = "UNSAFE"
    SKIPPED = "SKIPPED"


# =============================================================================
# Common references
# =============================================================================

@dataclass
class LocationRef:
    """A physical or logical location in the factory."""
    location_id: str
    pose_id: str | None = None
    frame_id: str | None = None
    zone_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityRef:
    """
    Generic reference to an item, product, material, machine, fixture, container,
    pallet, tote, tool, or other manufacturing entity.
    """
    entity_type: str
    entity_id: str | None = None
    quantity: float | int | None = None
    unit: str | None = None
    lot_id: str | None = None
    serial_id: str | None = None
    weight_kg: float | None = None
    dimensions_mm: tuple[float, float, float] | None = None
    handling_class: str | None = None  # rigid, fragile, sharp, hot, hazardous, flexible, etc.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterSpec:
    """Input or output parameter definition for a task template."""
    name: str
    type_hint: str
    required: bool = True
    description: str = ""
    default: Any | None = None
    unit: str | None = None
    allowed_values: list[Any] = field(default_factory=list)


@dataclass
class Condition:
    """
    A precondition or postcondition expressed as a string.

    Recommended binding syntax:
    - $inputs.item
    - $inputs.source
    - $tools.torque_driver
    - $vehicles.forklift
    - $steps.s2_localize_item.outputs.pose
    """
    expression: str
    description: str = ""


@dataclass
class SuccessCriterion:
    metric: str
    operator: str  # "<", "<=", "==", ">=", ">", "in", "not_in"
    value: Any
    unit: str | None = None
    description: str = ""


@dataclass
class SafetyConstraint:
    risk_level: RiskLevel = RiskLevel.LOW
    human_clearance_required: bool = False
    lockout_tagout_required: bool = False
    ppe_required: list[str] = field(default_factory=list)
    allowed_zones: list[str] = field(default_factory=list)
    forbidden_zones: list[str] = field(default_factory=list)
    max_payload_kg: float | None = None
    max_speed_mps: float | None = None
    max_force_n: float | None = None
    max_torque_nm: float | None = None
    required_authorizations: list[str] = field(default_factory=list)
    notes: str = ""


# =============================================================================
# Tool / vehicle / equipment requirements
# =============================================================================

@dataclass
class ToolRequirement:
    """
    Tool required by the task.

    Examples:
    - torque_driver
    - barcode_scanner
    - cutter
    - grease_gun
    - inspection_camera
    - suction_gripper
    - screwdriver_bit
    """
    alias: str
    tool_type: str
    tool_id: str | None = None
    use_mode: ToolUseMode = ToolUseMode.GENERAL
    control_mode: ResourceControlMode = ResourceControlMode.ROBOT_OPERATED
    acquire_policy: AcquirePolicy = AcquirePolicy.PICK_FROM_LOCATION
    pickup_location: LocationRef | None = None
    return_location: LocationRef | None = None
    calibration_required: bool = False
    settings: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    required_authorizations: list[str] = field(default_factory=list)
    required_for_steps: list[str] = field(default_factory=list)
    safety_notes: str = ""


@dataclass
class VehicleRequirement:
    """
    Vehicle or transport device required by the task.

    Examples:
    - forklift
    - pallet_jack
    - tugger
    - cart
    - elevator
    - AMR
    """
    alias: str
    vehicle_type: str
    vehicle_id: str | None = None
    use_mode: VehicleUseMode = VehicleUseMode.OPERATE
    control_mode: ResourceControlMode = ResourceControlMode.ROBOT_OPERATED
    interface_type: str | None = None  # manual_controls, api, tow_handle, remote_control, etc.
    acquire_policy: AcquirePolicy = AcquirePolicy.RESERVED_RESOURCE
    pickup_location: LocationRef | None = None
    return_location: LocationRef | None = None
    payload_capacity_kg: float | None = None
    allowed_routes: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    required_authorizations: list[str] = field(default_factory=list)
    required_for_steps: list[str] = field(default_factory=list)
    safety_notes: str = ""


@dataclass
class EquipmentRequirement:
    """
    Non-tool, non-vehicle resource used by a task.

    Examples:
    - CNC machine
    - welding fixture
    - test fixture
    - packaging machine
    - workbench
    - ASRS port
    """
    alias: str
    equipment_type: str
    equipment_id: str | None = None
    use_mode: EquipmentUseMode = EquipmentUseMode.OTHER
    control_mode: ResourceControlMode = ResourceControlMode.PASSIVE
    interface_type: str | None = None  # HMI, PLC, buttons, API, manual_lever, etc.
    location: LocationRef | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    required_authorizations: list[str] = field(default_factory=list)
    required_for_steps: list[str] = field(default_factory=list)
    safety_notes: str = ""


# =============================================================================
# Step calls
# =============================================================================

@dataclass
class RetryPolicy:
    max_attempts: int = 1
    retry_on: list[str] = field(default_factory=list)
    recovery_step_code: str | None = None


@dataclass
class StepCall:
    """
    One step inside an Atomic or Composite Task.

    Rules:
    - In an Atomic Task, call_code must refer to a Primitive Skill.
    - In a Composite Task, call_code may refer to a Primitive Skill, Atomic Task,
      or Composite Task.
    - uses_tools / uses_vehicles / uses_equipment refer to aliases declared in
      the parent TaskSpec.
    """
    step_id: str
    call_code: str
    args: dict[str, Any] = field(default_factory=dict)
    expected_level: TaskLevel | None = None
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False
    timeout_s: float | None = None
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    uses_tools: list[str] = field(default_factory=list)
    uses_vehicles: list[str] = field(default_factory=list)
    uses_equipment: list[str] = field(default_factory=list)
    preconditions: list[Condition] = field(default_factory=list)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)


# =============================================================================
# Task definitions and instances
# =============================================================================

@dataclass
class TaskSpec:
    """
    Common schema for Primitive Skills, Atomic Tasks, and Composite Tasks.
    """
    code: str
    level: TaskLevel
    version: str = "1.0.0"
    name: str = ""
    description: str = ""
    inputs: list[ParameterSpec] = field(default_factory=list)
    outputs: list[ParameterSpec] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)

    required_tools: list[ToolRequirement] = field(default_factory=list)
    required_vehicles: list[VehicleRequirement] = field(default_factory=list)
    required_equipment: list[EquipmentRequirement] = field(default_factory=list)

    safety: SafetyConstraint = field(default_factory=SafetyConstraint)
    preconditions: list[Condition] = field(default_factory=list)
    postconditions: list[Condition] = field(default_factory=list)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)

    # Primitive Skill: must be empty.
    # Atomic Task: Primitive Skill steps only.
    # Composite Task: Primitive / Atomic / Composite steps allowed.
    steps: list[StepCall] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def required_input_names(self) -> set[str]:
        return {p.name for p in self.inputs if p.required}

    def all_input_names(self) -> set[str]:
        return {p.name for p in self.inputs}

    def validate_basic(self, strict: bool = True) -> None:
        """
        Validate structural consistency that does not require a registry.
        """
        if self.level == TaskLevel.PRIMITIVE_SKILL and self.steps:
            raise ValueError(f"{self.code}: Primitive Skill must not have child steps.")

        if strict and self.level in {TaskLevel.ATOMIC_TASK, TaskLevel.COMPOSITE_TASK} and not self.steps:
            raise ValueError(f"{self.code}: {self.level.value} should have at least one child step.")

        step_ids = [step.step_id for step in self.steps]
        duplicate_step_ids = _duplicates(step_ids)
        if duplicate_step_ids:
            raise ValueError(f"{self.code}: duplicate step_id values: {duplicate_step_ids}")

        step_id_set = set(step_ids)
        for step in self.steps:
            if strict and self.level in {TaskLevel.ATOMIC_TASK, TaskLevel.COMPOSITE_TASK} and step.expected_level is None:
                raise ValueError(
                    f"{self.code}.{step.step_id}: expected_level is required for child step calls."
                )

            missing_dependencies = set(step.depends_on) - step_id_set
            if missing_dependencies:
                raise ValueError(
                    f"{self.code}.{step.step_id}: unknown dependencies: {sorted(missing_dependencies)}"
                )

        tool_aliases = _validate_unique_aliases(self.code, "tool", [t.alias for t in self.required_tools])
        vehicle_aliases = _validate_unique_aliases(self.code, "vehicle", [v.alias for v in self.required_vehicles])
        equipment_aliases = _validate_unique_aliases(self.code, "equipment", [e.alias for e in self.required_equipment])

        for step in self.steps:
            unknown_tools = set(step.uses_tools) - tool_aliases
            unknown_vehicles = set(step.uses_vehicles) - vehicle_aliases
            unknown_equipment = set(step.uses_equipment) - equipment_aliases

            if unknown_tools:
                raise ValueError(
                    f"{self.code}.{step.step_id}: unknown tool aliases: {sorted(unknown_tools)}"
                )
            if unknown_vehicles:
                raise ValueError(
                    f"{self.code}.{step.step_id}: unknown vehicle aliases: {sorted(unknown_vehicles)}"
                )
            if unknown_equipment:
                raise ValueError(
                    f"{self.code}.{step.step_id}: unknown equipment aliases: {sorted(unknown_equipment)}"
                )

        for tool in self.required_tools:
            _validate_required_for_steps(self.code, f"tool:{tool.alias}", tool.required_for_steps, step_id_set)
        for vehicle in self.required_vehicles:
            _validate_required_for_steps(self.code, f"vehicle:{vehicle.alias}", vehicle.required_for_steps, step_id_set)
        for equipment in self.required_equipment:
            _validate_required_for_steps(self.code, f"equipment:{equipment.alias}", equipment.required_for_steps, step_id_set)

    def validate_instance_args(self, args: dict[str, Any]) -> None:
        missing = self.required_input_names() - set(args.keys())
        if missing:
            raise ValueError(f"{self.code}: missing required input args: {sorted(missing)}")


@dataclass
class TaskInstance:
    """
    Concrete execution instance of a TaskSpec.
    """
    instance_id: str
    task_code: str
    args: dict[str, Any] = field(default_factory=dict)
    work_order_id: str | None = None
    assigned_robot_id: str | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepExecutionRecord:
    step_id: str
    call_code: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    attempts: int = 0
    observations: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class TaskExecutionRecord:
    instance_id: str
    task_code: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    step_records: list[StepExecutionRecord] = field(default_factory=list)
    observations: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


# =============================================================================
# Registry and validation
# =============================================================================

class TaskRegistry:
    """
    Registry for validating task hierarchy and retrieving TaskSpecs.

    Hierarchy rules:
    - Primitive Skill: must not have child steps.
    - Atomic Task: can call only Primitive Skills.
    - Composite Task: can call Primitive Skills, Atomic Tasks, and Composite Tasks.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskSpec] = {}

    def register(self, task: TaskSpec, *, validate_basic: bool = True) -> None:
        if validate_basic:
            task.validate_basic(strict=True)
        if task.code in self._tasks:
            raise ValueError(f"Duplicate task code: {task.code}")
        self._tasks[task.code] = task

    def get(self, code: str) -> TaskSpec:
        try:
            return self._tasks[code]
        except KeyError as exc:
            raise KeyError(f"Unknown task code: {code}") from exc

    def has(self, code: str) -> bool:
        return code in self._tasks

    def all_codes(self) -> list[str]:
        return sorted(self._tasks.keys())

    def validate_hierarchy(self, code: str) -> None:
        self._validate_hierarchy_recursive(code, stack=[])

    def validate_instance(self, instance: TaskInstance) -> None:
        task = self.get(instance.task_code)
        task.validate_instance_args(instance.args)

    def _validate_hierarchy_recursive(self, code: str, stack: list[str]) -> None:
        if code in stack:
            raise ValueError(f"Task cycle detected: {' -> '.join(stack + [code])}")

        task = self.get(code)
        task.validate_basic(strict=True)

        if task.level == TaskLevel.PRIMITIVE_SKILL:
            return

        composite_has_child_task = False
        for step in task.steps:
            called = self._tasks.get(step.call_code)
            called_level = called.level if called else step.expected_level

            if called_level is None:
                raise ValueError(
                    f"{task.code}.{step.step_id}: cannot determine level of {step.call_code}. "
                    "Register the called task or set expected_level."
                )

            if step.expected_level is None:
                raise ValueError(
                    f"{task.code}.{step.step_id}: expected_level is required for {step.call_code}."
                )

            if step.expected_level != called_level:
                raise ValueError(
                    f"{task.code}.{step.step_id}: expected_level={step.expected_level.value} "
                    f"does not match {step.call_code} level={called_level.value}."
                )

            if task.level == TaskLevel.ATOMIC_TASK:
                if called_level != TaskLevel.PRIMITIVE_SKILL:
                    raise ValueError(
                        f"{task.code}.{step.step_id}: Atomic Task can call only Primitive Skills, "
                        f"but {step.call_code} is {called_level.value}."
                    )

            elif task.level == TaskLevel.COMPOSITE_TASK:
                if called_level not in {
                    TaskLevel.PRIMITIVE_SKILL,
                    TaskLevel.ATOMIC_TASK,
                    TaskLevel.COMPOSITE_TASK,
                }:
                    raise ValueError(
                        f"{task.code}.{step.step_id}: invalid child level {called_level}"
                    )
                if called_level in {TaskLevel.ATOMIC_TASK, TaskLevel.COMPOSITE_TASK}:
                    composite_has_child_task = True

            if called is not None:
                self._validate_hierarchy_recursive(called.code, stack + [code])

        if task.level == TaskLevel.COMPOSITE_TASK and not composite_has_child_task:
            raise ValueError(
                f"{task.code}: Composite Task must include at least one child task call."
            )


# =============================================================================
# Serialization helpers
# =============================================================================

def to_jsonable(value: Any) -> Any:
    """Convert dataclasses and Enums into JSON-serializable Python objects."""
    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]

    return value


def dumps_json(value: Any, *, indent: int = 2, ensure_ascii: bool = False) -> str:
    return json.dumps(to_jsonable(value), indent=indent, ensure_ascii=ensure_ascii)


def dump_json_file(value: Any, path: str, *, indent: int = 2, ensure_ascii: bool = False) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_jsonable(value), f, indent=indent, ensure_ascii=ensure_ascii)


# =============================================================================
# Internal validation helpers
# =============================================================================

def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _validate_unique_aliases(task_code: str, alias_type: str, aliases: list[str]) -> set[str]:
    duplicates = _duplicates(aliases)
    if duplicates:
        raise ValueError(f"{task_code}: duplicate {alias_type} aliases: {duplicates}")
    return set(aliases)


def _validate_required_for_steps(
    task_code: str,
    resource_label: str,
    required_for_steps: list[str],
    step_id_set: set[str],
) -> None:
    if not required_for_steps:
        return
    unknown = set(required_for_steps) - step_id_set
    if unknown:
        raise ValueError(
            f"{task_code}: {resource_label} references unknown required_for_steps: {sorted(unknown)}"
        )
