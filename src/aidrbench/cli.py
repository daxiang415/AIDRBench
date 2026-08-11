"""Dependency-free bootstrap CLI.

The full Typer command tree described in README.md is implemented in later
phases.  Keeping the P0 commands in the standard library lets a fresh clone
validate its structure before third-party packages are installed.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from aidrbench._version import __version__
from aidrbench.envs.actions import all_actions
from aidrbench.project_check import check_project, format_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aidrbench", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("project-check", help="validate the offline P0 skeleton")
    check.add_argument("--root", default=".", help="repository root (default: current directory)")

    subparsers.add_parser("show-actions", help="print the 27 discrete V0 actions")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "project-check":
        report = check_project(args.root)
        print(format_report(report))
        return 0 if report.ok else 1

    if args.command == "show-actions":
        for action_id, components in enumerate(all_actions()):
            print(f"{action_id:2d}: {components}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
