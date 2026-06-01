from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from humanoidsim import ValidationLabConfig, run_validation_lab


class ValidationLabTests(unittest.TestCase):
    def test_validation_lab_generates_standalone_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_validation_lab(
                out_dir=Path(tmp),
                config=ValidationLabConfig(seed=7, fuzz_cases=3, max_steps=80),
            )
            self.assertTrue(result.ok, result.to_dict())
            expected = [
                "validation_summary.json",
                "task_execution_traces.jsonl",
                "incident_recovery_traces.jsonl",
                "state_transition_coverage.json",
                "fuzz_report.json",
                "validation_dashboard.html",
            ]
            for name in expected:
                self.assertTrue((Path(tmp) / name).exists(), name)
                self.assertGreater((Path(tmp) / name).stat().st_size, 0, name)

            summary = json.loads((Path(tmp) / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["catalog"]["task_count"], 86)
            self.assertEqual(summary["catalog"]["incident_count"], 35)

            dashboard = (Path(tmp) / "validation_dashboard.html").read_text(encoding="utf-8")
            self.assertIn("HumanoidSim Validation Lab", dashboard)
            self.assertIn("Incident Recovery Traces", dashboard)

    def test_validation_lab_records_expected_negative_transition_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_validation_lab(
                out_dir=Path(tmp),
                config=ValidationLabConfig(seed=3, fuzz_cases=1, max_steps=20),
            )
            self.assertTrue(result.ok, result.to_dict())
            fuzz_report = json.loads((Path(tmp) / "fuzz_report.json").read_text(encoding="utf-8"))
            checks = fuzz_report["negative_checks"]
            self.assertTrue(any(row["name"] == "unknown_primitive_rejected" and row["ok"] for row in checks))


if __name__ == "__main__":
    unittest.main()
