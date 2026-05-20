from __future__ import annotations

import unittest

from humanoidsim import (
    AvailabilityState,
    build_incident_transition_event,
    get_incident_profile,
    load_incident_schema,
    load_state_schema,
    load_task_catalog,
    transition_humanoid_state,
    validate_incident_schema,
)
from humanoidsim.state_schema import default_humanoid_state


class IncidentSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_task_catalog()
        cls.schema = load_incident_schema()

    def test_core_incidents_have_category_and_recovery_protocol(self) -> None:
        self.assertGreaterEqual(len(self.schema.incidents), 30)
        self.assertEqual(validate_incident_schema(self.schema, catalog=self.catalog), [])
        for code, profile in self.schema.incidents.items():
            with self.subTest(code=code):
                self.assertIn(profile.category, self.schema.categories)
                self.assertTrue(profile.recovery_protocol)

    def test_required_incidents_exist(self) -> None:
        required = {
            "OBJECT_RECOGNITION_FAILED",
            "GRIP_FAILED",
            "ITEM_DROPPED",
            "RESOURCE_PREEMPTED",
            "UNKNOWN",
        }
        self.assertTrue(required.issubset(set(self.schema.incidents)))

    def test_recovery_protocol_references_catalog(self) -> None:
        task_codes = set(self.catalog.tasks)
        primitive_codes = set(self.catalog.primitives)
        for profile in self.schema.incidents.values():
            for step in profile.recovery_protocol:
                with self.subTest(incident=profile.code, step=step.code):
                    if step.kind == "task":
                        self.assertIn(step.code, task_codes)
                    else:
                        self.assertIn(step.code, primitive_codes)

    def test_incident_transition_event_sets_reason_and_availability(self) -> None:
        snapshot = transition_humanoid_state(
            default_humanoid_state("H1"),
            build_incident_transition_event(
                "GRIP_FAILED",
                task_code="TRANSFER",
                task_instance_id="T1",
                primitive_call_code="GRASP",
                schema=self.schema,
            ),
        )
        self.assertEqual(snapshot.availability, AvailabilityState.BLOCKED)
        self.assertIsNotNone(snapshot.reason)
        self.assertEqual(snapshot.reason.code, "GRIP_FAILED")
        self.assertEqual(snapshot.reason.metadata["incident_category"], "manipulation_payload")

        waiting = transition_humanoid_state(
            default_humanoid_state("H2"),
            build_incident_transition_event("TRAFFIC_WAIT", task_code="TRANSFER", schema=self.schema),
        )
        self.assertEqual(waiting.availability, AvailabilityState.WAITING)

        disabled = transition_humanoid_state(
            default_humanoid_state("H3"),
            build_incident_transition_event("DEPLETED", task_code="MANAGE_ROBOT_POWER", schema=self.schema),
        )
        self.assertEqual(disabled.availability, AvailabilityState.DISABLED)

    def test_state_schema_includes_incident_reason_codes(self) -> None:
        reason_codes = {row["code"] for row in load_state_schema().standard_reason_codes}
        for code in self.schema.incidents:
            self.assertIn(code, reason_codes)

    def test_get_incident_profile(self) -> None:
        profile = get_incident_profile("object_recognition_failed", schema=self.schema)
        self.assertEqual(profile.code, "OBJECT_RECOGNITION_FAILED")
        self.assertEqual(profile.category, "perception_identification")
        self.assertIn("LOCALIZE_OBJECT", profile.trigger_primitives)

    def test_incident_aliases_resolve_to_canonical_codes(self) -> None:
        self.assertEqual(get_incident_profile("material_shelf_slot_empty", schema=self.schema).code, "RESOURCE_PREEMPTED")
        self.assertEqual(get_incident_profile("material_shelf_empty", schema=self.schema).code, "RESOURCE_MISSING")
        self.assertEqual(get_incident_profile("material_supply_dropoff_unreachable", schema=self.schema).code, "PATH_BLOCKED")
        self.assertEqual(get_incident_profile("material_carry_failed", schema=self.schema).code, "GRIP_FAILED")


if __name__ == "__main__":
    unittest.main()


