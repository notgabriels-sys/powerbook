"""Run Powerbook declarations locally without treating arithmetic as an electrical decision."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from powerbook.calculate import calculate_plan
from powerbook.config import ConfigError, load_plan
from powerbook.report import STATE_LABEL, write_bundle


def build_parser() -> argparse.ArgumentParser:
    """Create the small explicit command surface for local declaration packets."""

    parser = argparse.ArgumentParser(
        prog="powerbook",
        description="Calculate declared apparent-power worksheet arithmetic locally.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Read a plan and print a non-writing summary.")
    check.add_argument("plan", type=Path, help="Path to a declared Powerbook TOML plan.")
    build = commands.add_parser("build", help="Write a new declared power-budget packet.")
    build.add_argument("plan", type=Path, help="Path to a declared Powerbook TOML plan.")
    build.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New output directory for the packet; it must not already exist.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested calculation or packet write and return a shell-safe exit status."""

    arguments = build_parser().parse_args(argv)
    try:
        worksheet = calculate_plan(load_plan(arguments.plan))
        if arguments.command == "check":
            _write_check_summary(worksheet)
            return 0
        bundle = write_bundle(worksheet, arguments.output)
    except (ConfigError, FileExistsError, OSError, TypeError, ValueError) as error:
        print(f"Powerbook error: {error}", file=sys.stderr)
        return 1
    print(f"Wrote declared power-budget packet: {bundle.output_dir}")
    return 0


def _write_check_summary(worksheet) -> None:
    """Print only declaration counts and arithmetic-warning count; do not write a packet."""

    print(STATE_LABEL)
    print(f"Declared circuit rows: {len(worksheet.circuit_summaries)}")
    print(f"Declared device rows: {len(worksheet.device_entries)}")
    print(f"Arithmetic warning labels: {len(worksheet.warnings)}")
    print("No packet was written.")


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
