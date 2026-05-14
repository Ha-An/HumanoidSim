from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from humanoidsim import export_validation_viewer, load_sequence_file, load_task_catalog, validate_task_sequence
from humanoidsim.execution import HumanoidProfile
from humanoidsim.task_schema import TaskInstance


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_task_catalog()

    def test_catalog_has_82_core_tasks(self) -> None:
        self.assertEqual(self.catalog.task_count, 82)
        self.assertEqual(len(set(self.catalog.tasks)), 82)

    def test_all_tasks_validate_hierarchy(self) -> None:
        for code in self.catalog.tasks:
            self.catalog.registry.validate_hierarchy(code)

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
