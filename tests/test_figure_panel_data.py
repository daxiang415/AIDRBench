from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.evaluation.figure_panel_data import (
    export_main_figure_panel_plot_data,
    export_supplementary_panel_plot_data,
)


def _declared_plot_data(document: dict[str, object]) -> set[str]:
    outputs: set[str] = set()
    for collection_name in ("figures", "supplementary_figures"):
        collection = document[collection_name]
        assert isinstance(collection, dict)
        for figure in collection.values():
            assert isinstance(figure, dict)
            panels = figure["panels"]
            assert isinstance(panels, dict)
            for panel in panels.values():
                assert isinstance(panel, dict)
                output = panel["plot_data"]
                if output is not None:
                    assert isinstance(output, str)
                    outputs.add(output)
    return outputs


def test_panel_map_and_exact_plot_data_are_one_to_one(tmp_path: Path) -> None:
    main_output = tmp_path / "main"
    supplementary_output = tmp_path / "supplementary"
    main_manifest = export_main_figure_panel_plot_data(
        "manuscript/source_data/nature_mainline_v1",
        main_output,
    )
    supplementary_manifest = export_supplementary_panel_plot_data(
        "manuscript/source_data/nature_supplementary_v1",
        "configs/paper/nature_supplementary_figures_v1.yaml",
        supplementary_output,
        repository_root=".",
    )

    assert main_manifest["panel_table_count"] == 15
    assert supplementary_manifest["panel_table_count"] == 8
    produced = {
        str(record["output"])
        for manifest in (main_manifest, supplementary_manifest)
        for record in manifest["panels"]
    }
    guide = yaml.safe_load(
        Path("configs/paper/nature_figure_panel_map_v1.yaml").read_text(encoding="utf-8")
    )
    assert produced == _declared_plot_data(guide)
    s5_records = [
        record
        for record in supplementary_manifest["panels"]
        if record["figure"] == "S5"
    ]
    assert [(record["panel"], record["output"]) for record in s5_records] == [
        ("a", "figure_s5_panel_a.csv"),
        ("b", "figure_s5_panel_b.csv"),
        ("c", "figure_s5_panel_c.csv"),
        ("d", "figure_s5_panel_d.csv"),
    ]
    assert all(len(record["source_tables"]) == 1 for record in s5_records)

    figure1c = pd.read_csv(main_output / "figure_1_panel_c.csv")
    assert len(figure1c) == 30
    assert set(figure1c["calibration_role"]) == {"fit", "held_out"}
    assert figure1c.groupby(["mode", "gpu_count", "repeat"]).size().to_dict() == {
        ("offline_inference", 1, 1): 1,
        ("offline_inference", 1, 2): 1,
        ("offline_inference", 1, 3): 1,
        ("offline_inference", 4, 1): 4,
        ("offline_inference", 4, 2): 4,
        ("offline_inference", 4, 3): 4,
        ("training", 1, 1): 1,
        ("training", 1, 2): 1,
        ("training", 1, 3): 1,
        ("training", 4, 1): 4,
        ("training", 4, 2): 4,
        ("training", 4, 3): 4,
    }

    for filename, group_column, expected_rows in (
        ("figure_1_panel_b.csv", None, 8),
        ("figure_2_panel_a.csv", None, 8),
        ("figure_2_panel_b.csv", "reliability_target", 24),
        ("figure_5_panel_a.csv", "power_case", 24),
        ("figure_5_panel_c.csv", None, 8),
    ):
        duration_frame = pd.read_csv(main_output / filename)
        assert len(duration_frame) == expected_rows
        assert set(duration_frame["duration_grid_status"]) == {
            "evaluated",
            "not_evaluated",
        }
        groups = [duration_frame] if group_column is None else [
            group for _, group in duration_frame.groupby(group_column)
        ]
        for group in groups:
            assert group["duration_h"].tolist() == list(range(1, 9))
            missing = group[group["duration_grid_status"] == "not_evaluated"]
            assert missing["duration_h"].tolist() == [5, 7]
            assert set(missing["value_origin"]) == {"no_value_no_interpolation"}

    figure_s5b = pd.read_csv(supplementary_output / "figure_s5_panel_b.csv")
    assert len(figure_s5b) == 24
    assert set(figure_s5b["duration_grid_status"]) == {
        "evaluated",
        "not_evaluated",
    }
    for _, group in figure_s5b.groupby("climate_zone"):
        assert group["duration_h"].tolist() == list(range(1, 9))
        missing = group[group["duration_grid_status"] == "not_evaluated"]
        assert missing["duration_h"].tolist() == [5, 7]
        assert set(missing["value_origin"]) == {"no_value_no_interpolation"}

    figure_s5a = pd.read_csv(supplementary_output / "figure_s5_panel_a.csv")
    assert len(figure_s5a) == 504
    assert figure_s5a.groupby("climate_zone").size().to_dict() == {
        "3A": 168,
        "3C": 168,
        "5A": 168,
    }
    figure_s5c = pd.read_csv(supplementary_output / "figure_s5_panel_c.csv")
    assert len(figure_s5c) == 6
    assert figure_s5c.groupby("climate_zone").size().to_dict() == {
        "3A": 2,
        "3C": 2,
        "5A": 2,
    }
    figure_s5d = pd.read_csv(supplementary_output / "figure_s5_panel_d.csv")
    assert len(figure_s5d) == 12
    assert (
        figure_s5d.groupby(["climate_zone", "bess_enabled"])["dc_operation"]
        .nunique()
        .eq(2)
        .all()
    )

    figure_s4 = pd.read_csv(supplementary_output / "figure_s4_panel_a_b_c_d.csv")
    assert len(figure_s4) == 40
    assert figure_s4["relative_hour"].tolist() == list(range(-12, 28))
    assert figure_s4["hour"].tolist() == list(range(103, 143))

    for directory in (main_output, supplementary_output):
        stored = json.loads((directory / "panel_plot_data_manifest.json").read_text())
        for record in stored["panels"]:
            assert (directory / record["output"]).is_file()

    with pytest.raises(FileExistsError, match="must be empty to prevent stale files"):
        export_main_figure_panel_plot_data(
            "manuscript/source_data/nature_mainline_v1",
            main_output,
        )
