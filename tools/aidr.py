"""Reproduction and verification commands for AIDRBench."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="task", required=True)
    commands.add_parser("doctor", help="Inspect the checkout and optional dependencies.")
    for name, help_text in (
        ("check", "Verify the PDF and figure checkout."),
        ("redraw", "Redraw supplementary figures from included CSV files."),
        ("main-figures", "Rebuild corrected main panels and PowerPoint."),
        ("test", "Run the existing pytest suite."),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--dry-run", action="store_true", help="Print without executing.")
        if name == "check":
            command.add_argument("--hashes", action="store_true")
        elif name == "redraw":
            command.add_argument("--figures", nargs="+", choices=[f"S{i}" for i in range(1, 11)])
            command.add_argument("--tiff", action="store_true")
            command.add_argument("--audit", action="store_true")
        elif name == "main-figures":
            command.add_argument("--export-pdf", action="store_true", help="Requires LibreOffice.")
    return parser


def command_for(args: argparse.Namespace, root: Path) -> list[str]:
    scripts = {
        "check": "scripts/check_v027_checkout.py",
        "redraw": "paper/v0.27/figures/supplement/DRAW_SUPPLEMENT.py",
        "main-figures": "scripts/rebuild_main_figures.py",
    }
    if args.task == "test":
        return [sys.executable, "-m", "pytest", "-q"]
    command = [sys.executable, str(root / scripts[args.task])]
    if args.task == "check" and args.hashes:
        command.append("--hashes")
    elif args.task == "redraw":
        if args.figures:
            command.extend(["--figures", *args.figures])
        if args.tiff:
            command.append("--tiff")
        if args.audit:
            command.append("--audit")
    elif args.task == "main-figures" and not args.export_pdf:
        command.append("--panels-only")
    return command


def doctor(root: Path) -> int:
    print(f"Checkout: {root}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    supported = sys.version_info >= (3, 12)
    print("Python 3.12 is recommended; it is the version used in the CI configuration.")
    essential = (
        "pyproject.toml", "paper/v0.27/latex/main.pdf",
        "paper/v0.27/latex/supplement.pdf",
        "paper/v0.27/figures/supplement/DRAW_SUPPLEMENT.py",
    )
    complete = all((root / path).is_file() for path in essential)
    print(f"Required resource files: {'found' if complete else 'MISSING'}")
    for label, modules in (
        ("Figure reproduction", ("matplotlib", "PIL", "fitz", "numpy", "pandas")),
        ("Optimisation", ("cvxpy", "highspy", "osqp")),
        ("Development", ("pytest", "ruff", "mypy")),
    ):
        missing = [module for module in modules if importlib.util.find_spec(module) is None]
        status = "available" if not missing else "optional packages missing: " + ", ".join(missing)
        print(f"{label}: {status}")
    print("Manuscripts: supplied as PDFs; TeX is not required.")
    if (root / ".git").exists() and shutil.which("git"):
        try:
            probe = subprocess.run(
                ["git", "rev-parse", "--is-shallow-repository"], cwd=root,
                capture_output=True, text=True, timeout=10, check=True,
            )
            print("Git: " + ("shallow clone; history-dependent tests need a full clone"
                              if probe.stdout.strip() == "true" else "full checkout"))
        except (OSError, subprocess.SubprocessError):
            print("Git: history availability could not be determined")
    else:
        print("Git: no usable history; ZIP supports plotting, certificate replay needs a clone")
    print("This inspection does not execute simulations, tests or hash verification.")
    return 0 if supported and complete else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.task == "doctor":
        return doctor(ROOT)
    command = command_for(args, ROOT)
    print("Command:", subprocess.list2cmdline(command), flush=True)
    print("Working directory:", ROOT, flush=True)
    if args.dry_run:
        return 0
    environment = dict(os.environ, PYTHONUTF8="1", MPLBACKEND="Agg")
    try:
        result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    except OSError as error:
        print(f"Could not start the command: {error}", file=sys.stderr)
        return 1
    if result.returncode:
        print("Command failed. Inspect its output and run tools/aidr.py doctor.", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
