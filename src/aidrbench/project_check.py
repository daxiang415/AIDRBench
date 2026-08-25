"""Offline repository checks used before dependency installation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REQUIRED_PATHS = (
    "README.md",
    "MAINLINE_FILES.md",
    "pyproject.toml",
    "configs/env/nature_mainline_development.yaml",
    "configs/env/nature_mainline_validation.yaml",
    "configs/env/nature_mainline_locked_id.yaml",
    "configs/env/nature_mainline_locked_ood.yaml",
    "configs/controller/nature_robust_mpc_v1.yaml",
    "configs/paper/nature_source_data_v1.yaml",
    "configs/paper/nature_supplementary_figures_v1.yaml",
    "configs/sensitivity/nature_renewable_zero_miss_v1.yaml",
    "data/calibration/rtx6000pro_4gpu_v1.yaml",
    "data/examples/nature_supplementary_validation_v1/hourly_seed_20000/metadata.json",
    "data/manifests/renewable_zero_miss_results_v1.yaml",
    "data/manifests/nature_mainline_protocol_v1.yaml",
    "data/manifests/sources.yaml",
    "docs/figures/nature_mainline_v1/nature_mainline_figure_manifest.json",
    "docs/figures/nature_supplementary_v1/supplementary_figure_manifest.json",
    "docs/nature-mainline-figure-preview.md",
    "docs/nature-supplementary-figure-preview.md",
    "docs/reproducibility-environment.md",
    "manuscript/nature_communications_article.md",
    "manuscript/source_data/nature_mainline_v1/source_data_manifest.json",
    "manuscript/source_data/nature_supplementary_v1/supplementary_figure_4_trajectory.csv",
    "manuscript/submission-readiness.md",
    "manuscript/supplementary_information.md",
    "scripts/check_system.sh",
    "src/aidrbench/__init__.py",
    "src/aidrbench/envs/community_ai_dr_env.py",
    "src/aidrbench/evaluation/frozen_causal_certificate.py",
    "src/aidrbench/evaluation/hosting_capacity.py",
    "src/aidrbench/evaluation/supplementary_figures.py",
    "tests/test_nature_protocol.py",
    "tests/test_manuscript_source_data_bundle.py",
    "tests/test_supplementary_figures.py",
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
        return f"Nature mainline project check passed: {report.root}"
    lines = [f"Nature mainline project check failed: {report.root}", "Missing files:"]
    lines.extend(f"  - {path}" for path in report.missing)
    return "\n".join(lines)
