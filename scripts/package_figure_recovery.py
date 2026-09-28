"""Freeze a standalone local-draft redraw package without changing formal ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError("use a new package filename to preserve reviewed versions")
    files: dict[str, bytes] = {}

    def add(source: str, destination: str | None = None) -> None:
        files[destination or source] = (ROOT / source).read_bytes()

    add("docs/figure_recovery/README.md", "README_FIRST.md")
    add("docs/figure_recovery/contract.md", "DRAWING_CONTRACT.md")
    add("docs/figure_recovery/PROJECT_RECOVERY.md", "PROJECT_RECOVERY.md")
    add("docs/figure_recovery/requirements.txt", "requirements.txt")
    for name in ("draw_review_figures.py", "check_recovery_package.py"):
        add(f"scripts/{name}", f"code/{name}")
    add("tests/test_review_figure_recovery.py", "audit/project_regression_test.py")
    for kind, filename in (
        ("figure6", "AIDRBench_Figure6_WebGPT_v2.zip"),
        ("s5", "AIDRBench_Supplementary_Figure_S5_WebGPT_v1.zip"),
    ):
        add(f"results/exports/{filename}", f"inputs/{filename}")
        with zipfile.ZipFile(io.BytesIO(files[f"inputs/{filename}"])) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                if name.startswith("source_data/") and name.endswith(".csv"):
                    # Exact eight panel tables; other evidence remains in the original ZIP.
                    allowed = (
                        "fig6_fixed_site_overlay_scale_sensitivity.csv",
                        "fig6_mechanism_sensitivity.csv",
                        "fig6_break_even_decomposition.csv",
                        "fig6_duration_break_even.csv",
                    )
                    if kind == "s5" or Path(name).name in allowed:
                        files[f"panel_data/{kind}/{Path(name).name}"] = archive.read(name)
                if name.startswith("protocol/") or name == "README_FIRST_FOR_WEB_GPT.md":
                    files[f"contracts/{kind}/{name}"] = archive.read(name)
    for path in sorted((ROOT / "docs/figures/local_review_v3").iterdir()):
        add(str(path.relative_to(ROOT)), f"previews/{path.name}")
    for name in ("nature_communications_article.md", "supplementary_information.md"):
        add(f"manuscript/{name}")
    for stem in (
        "AIDRBench_Nature_Communications_v0.6_local_figure_review",
        "AIDRBench_Nature_Communications_v0.5_Supplementary_Information_local_figure_review",
    ):
        add(f"manuscript/exports/{stem}.pdf")
    for directory in ("nature_mainline_v1", "nature_supplementary_v1"):
        for path in sorted((ROOT / f"docs/figures/{directory}").glob("*.png")):
            if not path.name.startswith("figure_6_"):
                add(str(path.relative_to(ROOT)))
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    files["RECOVERY_SCOPE.json"] = (
        json.dumps(
            {
                "schema": "aidrbench.figure_recovery.v1",
                "scope": "local_review_drafts_figure6_s5",
                "formal_artwork": "not_generated; web_gpt_required_by_user",
                "project_source_commit": source,
                "project_source_worktree_dirty": dirty,
                "plot_source_sha256": hashlib.sha256(
                    files["code/draw_review_figures.py"]
                ).hexdigest(),
                "builder_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "input_data_changed": False,
                "experiments_recomputed": False,
                "new_environment_installation_tested": False,
                "audit_test_scope": (
                    "project_regression_test.py runs in the full project, "
                    "not this standalone bundle"
                ),
            },
            indent=2,
        )
        + "\n"
    ).encode()
    checksums = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())
    )
    files["CHECKSUMS_SHA256.txt"] = checksums.encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".aidrbench-recovery-", dir=output.parent) as temporary:
        candidate = Path(temporary) / "bundle.zip"
        with zipfile.ZipFile(
            candidate, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 9, 5, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        candidate.rename(output)
    return {
        "output": str(output),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "internal_files": len(files),
        "checksummed_files": len(files) - 1,
        "bytes": output.stat().st_size,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
