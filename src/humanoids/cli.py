from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import load_task_catalog
from .execution import load_sequence_file, validate_task_sequence
from .viewer import export_validation_viewer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="humanoids")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-catalog", help="Validate the generated task catalog.")

    validate_sequence = sub.add_parser("validate-sequence", help="Validate a humanoid task sequence JSON file.")
    validate_sequence.add_argument("sequence")

    export_viewer = sub.add_parser("export-viewer", help="Export static HTML sequence/animation viewer.")
    export_viewer.add_argument("sequence")
    export_viewer.add_argument("--out", required=True)
    export_viewer.add_argument("--report")

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

    parser.error(f"Unknown command: {args.command}")
    return 2

