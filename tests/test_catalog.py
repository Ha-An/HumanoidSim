from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from humanoidsim import expand_task_steps, export_validation_viewer, load_sequence_file, load_task_catalog, validate_task_sequence
from humanoidsim.complexity import task_complexity, task_complexity_index
from humanoidsim.catalog import TaskCatalog
from humanoidsim.execution import HumanoidProfile
from humanoidsim.task_schema import ParameterSpec, StepCall, TaskInstance, TaskLevel, TaskRegistry, TaskSpec


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_task_catalog()

    def test_catalog_has_core_tasks(self) -> None:
        self.assertEqual(self.catalog.task_count, 87)
        self.assertEqual(len(set(self.catalog.tasks)), 87)

    def test_all_tasks_validate_hierarchy(self) -> None:
        for code in self.catalog.tasks:
            self.catalog.registry.validate_hierarchy(code)

    def test_all_composite_tasks_include_child_task_call(self) -> None:
        for spec in self.catalog.tasks.values():
            if spec.level != TaskLevel.COMPOSITE_TASK:
                continue
            child_steps = [
                step
                for step in spec.steps
                if self.catalog.registry.get(step.call_code).level in {TaskLevel.ATOMIC_TASK, TaskLevel.COMPOSITE_TASK}
            ]
            self.assertTrue(child_steps, f"{spec.code} has no nested child task")

    def test_replenish_material_uses_nested_transfer(self) -> None:
        spec = self.catalog.tasks["REPLENISH_MATERIAL"]
        transfer_steps = [step for step in spec.steps if step.call_code == "TRANSFER"]
        self.assertEqual(len(transfer_steps), 1)
        self.assertEqual(transfer_steps[0].expected_level, TaskLevel.ATOMIC_TASK)

    def test_robot_handover_uses_robot_collaboration_primitives(self) -> None:
        rows = expand_task_steps(
            "HANDOVER_ITEM_TO_ROBOT",
            {
                "item": {"entity_type": "product", "entity_id": "PRODUCT-1"},
                "recipient": {"entity_type": "robot", "entity_id": "A2"},
                "handover_spec": {"mode": "product_collaboration_join"},
            },
            catalog=self.catalog,
        )
        primitive_codes = [row["call_code"] for row in rows if row["call_level"] == "PRIMITIVE_SKILL"]
        self.assertIn("SYNC_WITH_ROBOT", primitive_codes)
        self.assertIn("EXECUTE_ROBOT_COLLABORATION_ACTION", primitive_codes)
        self.assertNotIn("EXECUTE_HUMAN_COLLABORATION_ACTION", primitive_codes)

    def test_all_primitives_have_otc_difficulty_weight(self) -> None:
        allowed_weights = {round(index / 10, 1) for index in range(11)}
        allowed_groups = {
            "Administrative",
            "Low Operational",
            "Standard Robot Skill",
            "Manipulation & Process",
            "Coordination & Recovery",
            "Critical",
        }
        for spec in self.catalog.primitives.values():
            complexity = spec.metadata.get("operational_complexity", {})
            self.assertIn("difficulty_weight", complexity, spec.code)
            self.assertIn("difficulty_group", complexity, spec.code)
            self.assertIn("rationale", complexity, spec.code)
            self.assertIn(round(float(complexity["difficulty_weight"]), 1), allowed_weights, spec.code)
            self.assertGreaterEqual(float(complexity["difficulty_weight"]), 0.0, spec.code)
            self.assertLessEqual(float(complexity["difficulty_weight"]), 1.0, spec.code)
            self.assertIn(complexity["difficulty_group"], allowed_groups, spec.code)

    def test_task_complexity_uses_primitive_difficulty_weights(self) -> None:
        transfer = task_complexity("TRANSFER", {"item": "ITEM-1", "source": "A", "destination": "B"}, catalog=self.catalog)
        self.assertEqual("TRANSFER", transfer["task_code"])
        self.assertGreater(transfer["complexity"], 0.0)
        self.assertGreater(transfer["primitive_count"], 0)
        self.assertIn("NAVIGATE_TO", transfer["primitive_counts"])
        self.assertIn("GRASP", transfer["primitive_contributions"])
        self.assertEqual([], transfer["missing_weights"])

    def test_all_tasks_have_static_complexity(self) -> None:
        index = task_complexity_index(catalog=self.catalog)
        self.assertEqual(set(index), set(self.catalog.tasks))
        for task_code, payload in index.items():
            self.assertGreaterEqual(payload["complexity"], 0.0, task_code)
            self.assertGreater(payload["primitive_count"], 0, task_code)

    def test_expand_task_steps_preserves_nested_path(self) -> None:
        rows = expand_task_steps(
            "REPLENISH_MATERIAL",
            {
                "item": "MAT-01",
                "source": "warehouse",
                "destination": "station-1",
                "rule": "kanban",
            },
            catalog=self.catalog,
        )
        transfer_row = next(row for row in rows if row["call_code"] == "TRANSFER")
        self.assertEqual(transfer_row["call_level"], TaskLevel.ATOMIC_TASK.value)
        self.assertTrue(transfer_row["path"].startswith("REPLENISH_MATERIAL/"))
        self.assertTrue(any(row["parent_task_code"] == "TRANSFER" and row["call_code"] == "GRASP" for row in rows))

    def test_nested_child_missing_input_fails_validation(self) -> None:
        registry = TaskRegistry()
        primitive = TaskSpec(code="DO_THING", level=TaskLevel.PRIMITIVE_SKILL)
        child = TaskSpec(
            code="CHILD_TASK",
            level=TaskLevel.ATOMIC_TASK,
            inputs=[ParameterSpec(name="child_input", type_hint="Any", required=True)],
            steps=[StepCall(step_id="s01_do_thing", call_code="DO_THING", expected_level=TaskLevel.PRIMITIVE_SKILL)],
        )
        parent = TaskSpec(
            code="PARENT_TASK",
            level=TaskLevel.COMPOSITE_TASK,
            inputs=[ParameterSpec(name="parent_input", type_hint="Any", required=True)],
            steps=[
                StepCall(
                    step_id="s01_child_task",
                    call_code="CHILD_TASK",
                    args={"child_input": "$inputs.child_input"},
                    expected_level=TaskLevel.ATOMIC_TASK,
                )
            ],
        )
        for spec in (primitive, child, parent):
            registry.register(spec)
        catalog = TaskCatalog(root=self.catalog.root, index={}, registry=registry, tasks={"CHILD_TASK": child, "PARENT_TASK": parent}, primitives={"DO_THING": primitive})
        profile = HumanoidProfile(humanoid_id="H1", capabilities=["*"], supported_tools=["*"], supported_vehicles=["*"], supported_equipment=["*"])
        instance = TaskInstance(instance_id="bad-nested", task_code="PARENT_TASK", assigned_robot_id="H1", args={"parent_input": "ok"})
        result = validate_task_sequence(profile, [instance], catalog=catalog)
        self.assertFalse(result.ok)
        self.assertTrue(any(issue.code == "NESTED_MISSING_INPUT" for issue in result.issues), result.to_dict())

    def test_all_tasks_have_two_existing_animation_frames(self) -> None:
        for spec in self.catalog.tasks.values():
            frames = spec.metadata.get("animation", {}).get("frames", [])
            self.assertEqual(len(frames), 2, spec.code)
            for frame in frames:
                self.assertTrue((self.catalog.root / frame).exists(), f"{spec.code}: {frame}")

    def test_sample_sequence_validates(self) -> None:
        profiles, instances = load_sequence_file(self.catalog.root / "examples" / "manufacturing_sequence.json")
        result = validate_task_sequence(profiles, instances, catalog=self.catalog)
        self.assertTrue(result.ok, result.to_dict())

    def test_missing_input_fails_validation(self) -> None:
        profile = HumanoidProfile(humanoid_id="H1", capabilities=["*"], supported_tools=["*"], supported_vehicles=["*"], supported_equipment=["*"])
        instance = TaskInstance(instance_id="bad", task_code="TRANSFER", assigned_robot_id="H1", args={})
        result = validate_task_sequence(profile, [instance], catalog=self.catalog)
        self.assertFalse(result.ok)
        self.assertTrue(any(issue.code == "MISSING_INPUT" for issue in result.issues))

    def test_viewer_export_contains_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "viewer.html"
            export_validation_viewer(self.catalog.root / "examples" / "manufacturing_sequence.json", out=out, catalog=self.catalog)
            text = out.read_text(encoding="utf-8")
            self.assertIn("HumanoidSim Sequence Viewer", text)
            self.assertIn("TASK-0001", text)


if __name__ == "__main__":
    unittest.main()
