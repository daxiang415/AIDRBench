"""Offline repository checks used before dependency installation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REQUIRED_PATHS = (
    "README.md",
    "pyproject.toml",
    "configs/env/v0_discrete.yaml",
    "configs/hardware/four_gpu_node.yaml",
    "configs/hardware/gpu_profiles/h100_sxm_80gb.yaml",
    "configs/hardware/gpu_profiles/h200_sxm_141gb.yaml",
    "scripts/check_system.sh",
    "scripts/restore_gpu_power.py",
    "scripts/restore_gpu_power.sh",
    "src/aidrbench/__init__.py",
    "src/aidrbench/envs/actions.py",
    "src/aidrbench/datacenter/hardware.py",
    "src/aidrbench/datacenter/scaling.py",
    "src/aidrbench/hil/backend.py",
    "tests/test_actions.py",
)


@dataclass(frozen=True, slots=True)
class ProjectCheckReport:
    root: Path
    missing: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing


def check_project(root: str | Path) -> ProjectCheckReport:
    resolved = Path(root).resolve()
    missing = tuple(path for path in REQUIRED_PATHS if not (resolved / path).is_file())
    return ProjectCheckReport(root=resolved, missing=missing)


def format_report(report: ProjectCheckReport) -> str:
    if report.ok:
        return f"P0 project check passed: {report.root}"
    lines = [f"P0 project check failed: {report.root}", "Missing files:"]
    lines.extend(f"  - {path}" for path in report.missing)
    return "\n".join(lines)
