from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.evaluation.supplementary_figures import (
    _load_specification,
    plot_nature_supplementary_figures,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_repository_supplementary_preview_manifests_match_pngs() -> None:
    root = Path(__file__).resolve().parents[1] / "docs/figures/nature_supplementary_v1"
    bundle = json.loads((root / "supplementary_figure_manifest.json").read_text())

    assert bundle["locked_sets_used"] is False
    assert bundle["figure_count"] == 4
    for figure in bundle["figures"]:
        per_figure = json.loads((root / figure["manifest"]).read_text())
        assert figure["outputs"] == per_figure["outputs"]
        png = next(output for output in figure["outputs"] if output["format"] == "png")
        png_path = root / png["path"]
        assert png_path.stat().st_size == png["bytes"]
        assert _sha256(png_path) == png["sha256"]


def test_supplementary_specification_fails_closed_on_locked_scenarios(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "configs/paper/nature_supplementary_figures_v1.yaml"
    document = yaml.safe_load(source.read_text())
    document["observation_and_trajectory"]["scenario_set"] = (
        "data/frozen/nature_mainline_locked_id"
    )
    altered = tmp_path / "supplementary_locked.yaml"
    altered.write_text(yaml.safe_dump(document, sort_keys=False))

    with pytest.raises(ValueError, match="non-locked validation set"):
        _load_specification(altered)


def test_supplementary_s5_is_declared_as_non_locked_web_gpt_artwork(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "configs/paper/nature_supplementary_figures_v1.yaml"
    document = yaml.safe_load(source.read_text())
    document["external_artwork"]["S5"]["renderer"] = "python_matplotlib"
    altered = tmp_path / "supplementary_local_s5.yaml"
    altered.write_text(yaml.safe_dump(document, sort_keys=False))

    with pytest.raises(ValueError, match="Web-GPT route"):
        _load_specification(altered)


def test_local_supplementary_renderer_rejects_external_s5(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="S5 uses Web-GPT"):
        plot_nature_supplementary_figures(
            "configs/paper/nature_supplementary_figures_v1.yaml",
            tmp_path,
            figures=(5,),
            formats=("svg",),
        )


def test_all_supplementary_figures_render_from_tracked_non_locked_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    summary = plot_nature_supplementary_figures(
        "configs/paper/nature_supplementary_figures_v1.yaml",
        tmp_path,
        figures=(1, 2, 3, 4),
        formats=("svg",),
    )

    assert summary["locked_sets_used"] is False
    assert summary["figure_count"] == 4
    assert (tmp_path / "supplementary_figure_1.svg").is_file()
    assert (tmp_path / "supplementary_figure_2.svg").is_file()
    assert (tmp_path / "supplementary_figure_3.svg").is_file()
    assert (tmp_path / "supplementary_figure_4.svg").is_file()

    trajectory = pd.read_csv(tmp_path / "supplementary_figure_4_trajectory.csv")
    metadata = json.loads(
        (tmp_path / "representative_trajectory_metadata.json").read_text(encoding="utf-8")
    )
    assert trajectory["relative_hour"].tolist() == list(range(-12, 28))
    assert trajectory["hour"].tolist() == list(range(103, 143))
    assert (
        trajectory["relative_hour"]
        == trajectory["hour"] - int(metadata["event_start_hour"])
    ).all()
    assert metadata["plot_window_pre_event_h"] == 12
    assert metadata["plot_window_post_event_h"] == 24
