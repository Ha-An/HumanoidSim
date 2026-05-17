from __future__ import annotations

import unittest

from humanoidsim import (
    AvailabilityState,
    HumanoidStateSnapshot,
    ManipulationState,
    MobilityState,
    PowerState,
    StateReason,
    StateTransitionError,
    StateTransitionEvent,
    TaskContext,
    apply_primitive_state_hint,
    build_state_snapshot_for_task_lifecycle,
    default_humanoid_state,
    derive_availability_state,
    get_primitive_state_profile,
    load_state_schema,
    parse_humanoid_state_snapshot,
    primitive_state_hint,
    transition_humanoid_state,
    validate_primitive_state_profile,
    validate_state_snapshot,
)
from humanoidsim.task_schema import ExecutionStatus


class StateSchemaTests(unittest.TestCase):
    def test_core_enum_values_match_v01_contract(self) -> None:
        self.assertEqual(
            [state.value for state in AvailabilityState],
            ["AVAILABLE", "ASSIGNED", "EXECUTING", "WAITING", "BLOCKED", "OFFLINE", "DISABLED"],
        )
        self.assertEqual([state.value for state in MobilityState], ["STATIONARY", "NAVIGATING", "DOCKING"])
        self.assertEqual(
            [state.value for state in PowerState],
            ["POWER_NORMAL", "POWER_LOW", "POWER_CRITICAL", "DEPLETED", "CHARGING"],
        )
        self.assertEqual([state.value for state in ManipulationState], ["FREE", "REACHING", "HOLDING", "PLACING"])

    def test_default_snapshot_and_round_trip(self) -> None:
        snapshot = default_humanoid_state("H1")
        self.assertEqual(snapshot.availability, AvailabilityState.AVAILABLE)
        self.assertEqual(snapshot.mobility, MobilityState.STATIONARY)
        self.assertEqual(snapshot.power, PowerState.POWER_NORMAL)
        self.assertEqual(snapshot.manipulation, ManipulationState.FREE)

        parsed = parse_humanoid_state_snapshot(snapshot.to_dict())
        self.assertEqual(parsed, snapshot)

    def test_state_schema_validates_core_and_rejects_unknown(self) -> None:
        schema = load_state_schema()
        snapshot = default_humanoid_state("H1")
        self.assertEqual(schema.validate_snapshot(snapshot), [])

        invalid = snapshot.to_dict()
        invalid["mobility"] = "FLYING"
        issues = schema.validate_snapshot(invalid)
        self.assertTrue(any(issue.code == "UNKNOWN_STATE" and issue.field == "mobility" for issue in issues))

    def test_waiting_blocked_and_disabled_need_reason(self) -> None:
        base = default_humanoid_state("H1").to_dict()
        for availability in ["WAITING", "BLOCKED", "DISABLED"]:
            payload = dict(base, availability=availability)
            issues = validate_state_snapshot(payload)
            self.assertTrue(any(issue.code == "MISSING_STATE_REASON" for issue in issues), availability)

        payload = dict(base, availability="BLOCKED", reason={"code": "NO_ROUTE"})
        self.assertEqual(validate_state_snapshot(payload), [])

    def test_primitive_state_hints(self) -> None:
        self.assertEqual(primitive_state_hint("NAVIGATE_TO").mobility, MobilityState.NAVIGATING)
        self.assertEqual(primitive_state_hint("REACH_TO").manipulation, ManipulationState.REACHING)
        self.assertEqual(primitive_state_hint("GRASP").manipulation, ManipulationState.HOLDING)
        self.assertEqual(primitive_state_hint("PLACE").manipulation, ManipulationState.PLACING)
        self.assertEqual(primitive_state_hint("RELEASE", primitive_finished=True).manipulation, ManipulationState.FREE)
        self.assertEqual(
            primitive_state_hint("EXECUTE_SYSTEM_ACTION", task_code="MANAGE_ROBOT_POWER").power,
            PowerState.CHARGING,
        )

    def test_primitive_state_profiles_define_allowed_and_effects(self) -> None:
        schema = load_state_schema()
        for call_code, profile in schema.primitive_state_profiles.items():
            with self.subTest(call_code=call_code):
                self.assertEqual(profile.availability_running, AvailabilityState.EXECUTING)
                self.assertEqual(validate_primitive_state_profile(profile, schema=schema), [])
                self.assertIn("mobility", profile.allowed)
                self.assertIn("manipulation", profile.allowed)

        navigate = get_primitive_state_profile("NAVIGATE_TO", schema=schema)
        self.assertIn("NAVIGATING", navigate.allowed["mobility"])
        self.assertEqual(navigate.effect_for().mobility, MobilityState.NAVIGATING)
        self.assertEqual(navigate.effect_for(finished=True).mobility, MobilityState.STATIONARY)

    def test_apply_primitive_state_hint_updates_context_without_overriding_blocked(self) -> None:
        snapshot = HumanoidStateSnapshot(
            humanoid_id="H1",
            task_context=TaskContext(task_code="TRANSFER", task_instance_id="T1"),
        )
        navigating = apply_primitive_state_hint(snapshot, "NAVIGATE_TO")
        self.assertEqual(navigating.availability, AvailabilityState.EXECUTING)
        self.assertEqual(navigating.mobility, MobilityState.NAVIGATING)
        self.assertEqual(navigating.task_context.primitive_call_code, "NAVIGATE_TO")

        blocked = HumanoidStateSnapshot(
            humanoid_id="H1",
            availability=AvailabilityState.BLOCKED,
            reason=StateReason(code="NO_ROUTE"),
        )
        still_blocked = apply_primitive_state_hint(blocked, "NAVIGATE_TO")
        self.assertEqual(still_blocked.availability, AvailabilityState.BLOCKED)
        self.assertEqual(still_blocked.mobility, MobilityState.NAVIGATING)

    def test_transition_api_drives_task_and_primitive_state(self) -> None:
        snapshot = default_humanoid_state("H1")
        assigned = transition_humanoid_state(
            snapshot,
            StateTransitionEvent(event_type="task_assigned", task_code="TRANSFER", task_instance_id="T1"),
        )
        self.assertEqual(assigned.availability, AvailabilityState.ASSIGNED)

        started = transition_humanoid_state(
            assigned,
            StateTransitionEvent(event_type="task_started", task_code="TRANSFER", task_instance_id="T1"),
        )
        self.assertEqual(started.availability, AvailabilityState.EXECUTING)

        moving = transition_humanoid_state(
            started,
            StateTransitionEvent(
                event_type="primitive_started",
                task_code="TRANSFER",
                task_instance_id="T1",
                step_id="s1",
                primitive_call_code="NAVIGATE_TO",
            ),
        )
        self.assertEqual(moving.availability, AvailabilityState.EXECUTING)
        self.assertEqual(moving.mobility, MobilityState.NAVIGATING)

        stopped = transition_humanoid_state(
            moving,
            StateTransitionEvent(
                event_type="primitive_finished",
                task_code="TRANSFER",
                task_instance_id="T1",
                step_id="s1",
                primitive_call_code="NAVIGATE_TO",
            ),
        )
        self.assertEqual(stopped.mobility, MobilityState.STATIONARY)

        with self.assertRaises(StateTransitionError):
            transition_humanoid_state(
                stopped,
                StateTransitionEvent(event_type="primitive_started", task_code="TRANSFER", primitive_call_code="UNKNOWN"),
            )

    def test_task_lifecycle_availability_mapping(self) -> None:
        self.assertEqual(derive_availability_state(), AvailabilityState.AVAILABLE)
        self.assertEqual(derive_availability_state(has_task=True), AvailabilityState.ASSIGNED)
        self.assertEqual(derive_availability_state(step_running=True), AvailabilityState.EXECUTING)
        self.assertEqual(derive_availability_state(waiting=True), AvailabilityState.WAITING)
        self.assertEqual(derive_availability_state(blocked=True), AvailabilityState.BLOCKED)
        self.assertEqual(derive_availability_state(disabled=True), AvailabilityState.DISABLED)
        self.assertEqual(derive_availability_state(offline=True, disabled=True), AvailabilityState.OFFLINE)

        assigned = build_state_snapshot_for_task_lifecycle("H1", task_code="TRANSFER", task_instance_id="T1")
        self.assertEqual(assigned.availability, AvailabilityState.ASSIGNED)

        executing = build_state_snapshot_for_task_lifecycle(
            "H1",
            task_code="INSPECT_PRODUCT",
            task_instance_id="T2",
            step_id="s3",
            primitive_call_code="REACH_TO",
            execution_status=ExecutionStatus.RUNNING,
        )
        self.assertEqual(executing.availability, AvailabilityState.EXECUTING)
        self.assertEqual(executing.manipulation, ManipulationState.REACHING)
        self.assertEqual(executing.task_context.execution_status, ExecutionStatus.RUNNING)

        blocked = build_state_snapshot_for_task_lifecycle(
            "H1",
            task_code="TRANSFER",
            blocked_reason=StateReason(code="NO_ROUTE"),
            primitive_call_code="NAVIGATE_TO",
        )
        self.assertEqual(blocked.availability, AvailabilityState.BLOCKED)
        self.assertEqual(blocked.mobility, MobilityState.STATIONARY)


if __name__ == "__main__":
    unittest.main()
