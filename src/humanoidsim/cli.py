from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import load_task_catalog
from .execution import load_sequence_file, validate_task_sequence
from .interactive_lab_ui import LabUiConfig, launch_gazebo_validation, run_lab_ui
from .validation_lab import ValidationLabConfig, run_validation_lab
from .viewer import export_validation_viewer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="humanoidsim")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-catalog", help="Validate the generated task catalog.")

    validate_sequence = sub.add_parser("validate-sequence", help="Validate a humanoid task sequence JSON file.")
    validate_sequence.add_argument("sequence")

    export_viewer = sub.add_parser("export-viewer", help="Export static HTML sequence/animation viewer.")
    export_viewer.add_argument("sequence")
    export_viewer.add_argument("--out", required=True)
    export_viewer.add_argument("--report")

    validate_lab = sub.add_parser("validate-lab", help="Run the standalone HumanoidSim validation lab.")
    validate_lab.add_argument("--all", action="store_true", help="Run catalog, mock execution, recovery, coverage, and fuzz checks.")
    validate_lab.add_argument("--out", help="Output directory. Defaults to outputs/validation/<timestamp>.")
    validate_lab.add_argument("--seed", type=int, default=42)
    validate_lab.add_argument("--fuzz-cases", type=int, default=200)
    validate_lab.add_argument("--max-steps", type=int, default=200)

    lab_ui = sub.add_parser("lab-ui", help="Run the standalone interactive validation lab UI.")
    lab_ui.add_argument("--host", default="127.0.0.1")
    lab_ui.add_argument("--port", type=int, default=8765)
    lab_ui.add_argument("--ros", action="store_true", help="Enable RViz launch and trace playback controls.")
    lab_ui.add_argument("--gazebo", action="store_true", help="Enable Gazebo physics validation launch controls.")
    lab_ui.add_argument("--wsl-distro", default="Ubuntu-24.04")
    lab_ui.add_argument("--out", help="Output directory. Defaults to outputs/interactive_lab/<timestamp>.")
    lab_ui.add_argument("--no-open", action="store_true", help="Do not open a browser automatically.")

    physics_validation = sub.add_parser("physics-validation", help="Launch standalone Gazebo physics validation mode.")
    physics_validation.add_argument("--wsl-distro", default="Ubuntu-24.04")
    physics_validation.add_argument("--no-wait", action="store_true", help="Return immediately after requesting Gazebo launch.")

    args = parser.parse_args(argv)
    catalog = load_task_catalog()

    if args.command == "validate-catalog":
        print(
            json.dumps(
                {
                    "ok": True,
                    "task_count": catalog.task_count,
                    "primitive_count": catalog.primitive_count,
                    "catalog_version": catalog.index.get("catalog_version"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "validate-sequence":
        profiles, instances = load_sequence_file(args.sequence)
        result = validate_task_sequence(profiles, instances, catalog=catalog)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0 if result.ok else 1

    if args.command == "export-viewer":
        out = export_validation_viewer(args.sequence, out=Path(args.out), catalog=catalog, report_out=args.report)
        print(str(out.resolve()))
        return 0

    if args.command == "validate-lab":
        result = run_validation_lab(
            out_dir=args.out,
            config=ValidationLabConfig(seed=args.seed, fuzz_cases=args.fuzz_cases, max_steps=args.max_steps),
        )
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0 if result.ok else 1

    if args.command == "lab-ui":
        run_lab_ui(
            LabUiConfig(
                host=args.host,
                port=args.port,
                ros_enabled=args.ros,
                gazebo_enabled=args.gazebo,
                wsl_distro=args.wsl_distro,
                out_dir=Path(args.out) if args.out else None,
                open_browser=not args.no_open,
            )
        )
        return 0

    if args.command == "physics-validation":
        process = launch_gazebo_validation(wsl_distro=args.wsl_distro)
        print("Gazebo physics validation launch requested.")
        if args.no_wait:
            return 0
        return process.wait()

    parser.error(f"Unknown command: {args.command}")
    return 2
