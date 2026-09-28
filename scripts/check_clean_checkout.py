"""Run the suite with Git history and no ignored workstation artifacts.

Uses the invoking Python environment; this is a checkout-portability check,
not a new dependency installation. The default tests committed HEAD. Pass
--include-worktree to test a candidate including uncommitted source files.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def overlay_worktree(root: Path, clone: Path) -> None:
    """Replace the clone's tracked files with the current candidate file set.

    Removing HEAD files first also handles staged deletions and rename sources,
    which are absent from the current index. Git history is kept for provenance
    tests. Submodules require separate checkout handling and fail explicitly.
    """
    for repository in (root, clone):
        entries = subprocess.check_output(
            ["git", "ls-files", "--stage", "-z"], cwd=repository, text=True
        )
        if any(entry.startswith("160000 ") for entry in entries.split("\0")):
            raise RuntimeError("checkout overlay does not support submodules")

    head_paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached"], cwd=clone, text=True
    )
    for name in filter(None, head_paths.split("\0")):
        target = clone / name
        target.unlink()
        parent = target.parent
        while parent != clone:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        text=True,
    )
    for name in sorted(set(filter(None, paths.split("\0")))):
        source, target = root / name, clone / name
        if source.is_file() or source.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-worktree", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    def git(*arguments: str) -> str:
        return subprocess.check_output(["git", *arguments], cwd=root, text=True)

    commit = git("rev-parse", "HEAD").strip()
    dirty = bool(git("status", "--porcelain"))
    with tempfile.TemporaryDirectory(prefix="aidrbench-checkout-") as temporary:
        clone = Path(temporary) / "repo"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(root), str(clone)],
            check=True,
        )
        if args.include_worktree:
            overlay_worktree(root, clone)
        excluded = [
            "results/economics/economic_participation_v1/ledger/episode_ledger.parquet",
            "results/nature_mainline/locked_id_certificate_q95/causal_certificate.json",
            "results/nature_mainline/causal_selection_q95/causal_selection.json",
        ]
        for name in excluded:
            if (clone / name).exists():
                raise RuntimeError(f"checkout unexpectedly includes a production artifact: {name}")
        command = [sys.executable, "-m", "pytest", "-q"]
        result = subprocess.run(command, cwd=clone, text=True, capture_output=True, check=False)
        receipt = {
            "base_commit": commit,
            "source_worktree_dirty": dirty,
            "include_worktree": args.include_worktree,
            "environment": "existing_invoking_python_environment; no dependency reinstall",
            "python": sys.executable,
            "excluded_production_paths": excluded,
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
