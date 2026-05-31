from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from humanoidsim import LabUiConfig, LabUiRuntime, run_incident_trace, run_task_trace


class InteractiveLabTests(unittest.TestCase):
    def test_task_trace_contains_motion_and_state_events(self) -> None:
        trace = run_task_trace("TRANSFER", {}, humanoid_id="H1", instance_id="TR-1")
        payload = trace.to_dict()
        self.assertEqual(payload["trace_type"], "task")
        self.assertTrue(payload["events"])
        self.assertTrue(any(row.get("primitive_call_code") == "NAVIGATE_TO" for row in payload["events"]))
        self.assertTrue(any(row.get("motion_hint", {}).get("type") == "translate" for row in payload["events"]))
        self.assertIn("final_state", payload["summary"])

    def test_incident_trace_keeps_recovery_blocked(self) -> None:
        trace = run_incident_trace("ITEM_DROPPED", {}, humanoid_id="H1")
        recovery_events = [row for row in trace.events if row.get("is_recovery") and row.get("primitive_call_code")]
        self.assertTrue(recovery_events)
        self.assertTrue(all(row["state_after"]["availability"] == "BLOCKED" for row in recovery_events))
        self.assertTrue(any("(RECOVERY)" in row.get("display_code", "") for row in recovery_events))

    def test_lab_ui_runtime_returns_catalog_and_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = LabUiRuntime(LabUiConfig(open_browser=False, ros_enabled=True, gazebo_enabled=True, out_dir=Path(tmp)))
            catalog = runtime.catalog_payload()
            self.assertGreater(len(catalog["tasks"]), 0)
            self.assertGreater(len(catalog["incidents"]), 0)
            self.assertTrue(catalog["ros_enabled"])
            self.assertTrue(catalog["gazebo_enabled"])
            session = runtime.run_incident({"incident_code": "GRIP_FAILED", "humanoid_id": "H1", "context": {}})
            self.assertEqual(session["summary"]["incident_code"], "GRIP_FAILED")
            self.assertTrue(Path(session["trace_path"]).exists())
            self.assertIsNotNone(runtime.session(session["session_id"]))


if __name__ == "__main__":
    unittest.main()
