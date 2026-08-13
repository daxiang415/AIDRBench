from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from aidrbench.calibration.plan import PLAN_COLUMNS, make_calibration_plan
from aidrbench.cli import main


def _write_config(path: Path, *, randomize_order: bool = True) -> None:
    document = {
        "power": {
            "infer_cap_ratios": [0.7, 1.0],
            "batch_cap_ratios": [0.6, 1.0],
        },
        "calibration": {
            "batch_gpu_counts": [0, 2],
            "request_rate_levels": ["p25", "p90"],
            "token_mixes": ["short", "long"],
            "repetitions": 2,
            "seed": 17,
            "randomize_order": randomize_order,
            "timing": {
                "warmup_seconds": 30,
                "measurement_seconds": 60,
                "cooldown_seconds": 10,
            },
            "designs": {
                "smoke": {
                    "repetitions": 1,
                    "randomize_order": False,
                    "timing": {
                        "warmup_seconds": 1,
                        "measurement_seconds": 2,
                        "cooldown_seconds": 1,
                    },
                    "configurations": [
                        {
                            "inference_cap_ratio": 1.0,
                            "active_batch_gpus": 2,
                            "batch_cap_ratio": 1.0,
                            "request_rate_level": "p25",
                            "token_mix": "short",
                        },
                        {
                            "inference_cap_ratio": 0.7,
                            "active_batch_gpus": 0,
                            "batch_cap_ratio": 0.6,
                            "request_rate_level": "p90",
                            "token_mix": "long",
                        },
                    ],
                }
            },
        },
    }
    path.write_text(yaml.safe_dump(document), encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_plan_contains_full_factorial_repetitions_and_stable_order(tmp_path: Path) -> None:
    config = tmp_path / "hardware.yaml"
    _write_config(config)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"

    summary = make_calibration_plan(config, first)
    make_calibration_plan(config, second)
    rows = _read_rows(first)

    assert summary.unique_configurations == 2**5
    assert summary.runs == 2**6
    assert summary.estimated_runtime_hours == pytest.approx(64 * 100 / 3600, abs=0.001)
    assert first.read_bytes() == second.read_bytes()
    assert tuple(rows[0]) == PLAN_COLUMNS
    assert [int(row["run_order"]) for row in rows] == list(range(1, 65))
    assert len({row["run_id"] for row in rows}) == 64
    assert {row["repeat"] for row in rows} == {"1", "2"}


def test_plan_can_keep_canonical_order(tmp_path: Path) -> None:
    config = tmp_path / "hardware.yaml"
    _write_config(config, randomize_order=False)
    output = tmp_path / "plan.csv"

    make_calibration_plan(config, output)
    rows = _read_rows(output)

    assert rows[0]["run_id"] == "p2_cfg0001_r01"
    assert rows[1]["run_id"] == "p2_cfg0001_r02"
    assert rows[-1]["run_id"] == "p2_cfg0032_r02"


def test_plan_rejects_unsafe_ratios_and_empty_factors(tmp_path: Path) -> None:
    config = tmp_path / "hardware.yaml"
    _write_config(config)
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    document["power"]["infer_cap_ratios"] = [0.7, 1.1]
    config.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match=r"in \(0, 1\]"):
        make_calibration_plan(config, tmp_path / "plan.csv")

    document["power"]["infer_cap_ratios"] = []
    config.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty list"):
        make_calibration_plan(config, tmp_path / "plan.csv")


def test_cli_make_plan_reports_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "hardware.yaml"
    output = tmp_path / "plan.csv"
    _write_config(config)

    exit_code = main(
        ["calibrate", "make-plan", "--config", str(config), "--output", str(output)]
    )

    assert exit_code == 0
    assert '"unique_configurations": 32' in capsys.readouterr().out
    assert output.is_file()


def test_explicit_smoke_design_uses_short_timing_and_namespaced_ids(tmp_path: Path) -> None:
    config = tmp_path / "hardware.yaml"
    output = tmp_path / "smoke.csv"
    _write_config(config)

    summary = make_calibration_plan(config, output, design="smoke")
    rows = _read_rows(output)

    assert summary.design == "smoke"
    assert summary.unique_configurations == 2
    assert summary.runs == 2
    assert summary.estimated_runtime_hours == pytest.approx(8 / 3600, abs=0.001)
    assert rows[0]["run_id"] == "p2_smoke_cfg0001_r01"
    assert rows[0]["stage"] == "smoke"
    assert rows[1]["run_id"] == "p2_smoke_cfg0002_r01"


def test_explicit_design_rejects_values_outside_factor_levels(tmp_path: Path) -> None:
    config = tmp_path / "hardware.yaml"
    _write_config(config)
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    document["calibration"]["designs"]["smoke"]["configurations"][0][
        "request_rate_level"
    ] = "p99"
    config.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ValueError, match="outside the configured factor levels"):
        make_calibration_plan(config, tmp_path / "smoke.csv", design="smoke")


def test_maximin_screening_design_is_deterministic_and_covers_levels(
    tmp_path: Path,
) -> None:
    config = tmp_path / "hardware.yaml"
    _write_config(config)
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    document["calibration"]["designs"]["screening"] = {
        "selection": "maximin",
        "configuration_count": 12,
        "repetitions": 1,
        "randomize_order": True,
    }
    config.write_text(yaml.safe_dump(document), encoding="utf-8")
    first = tmp_path / "screening-first.csv"
    second = tmp_path / "screening-second.csv"

    summary = make_calibration_plan(config, first, design="screening")
    make_calibration_plan(config, second, design="screening")
    rows = _read_rows(first)

    assert summary.unique_configurations == 12
    assert summary.runs == 12
    assert first.read_bytes() == second.read_bytes()
    assert len({row["config_id"] for row in rows}) == 12
    assert {row["inference_cap_ratio"] for row in rows} == {"0.7", "1.0"}
    assert {row["active_batch_gpus"] for row in rows} == {"0", "2"}
    assert {row["batch_cap_ratio"] for row in rows} == {"0.6", "1.0"}
    assert {row["request_rate_level"] for row in rows} == {"p25", "p90"}
    assert {row["token_mix"] for row in rows} == {"short", "long"}


def test_maximin_rejects_more_points_than_the_factor_space(tmp_path: Path) -> None:
    config = tmp_path / "hardware.yaml"
    _write_config(config)
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    document["calibration"]["designs"]["too_many"] = {
        "selection": "maximin",
        "configuration_count": 33,
    }
    config.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds the 32 available"):
        make_calibration_plan(config, tmp_path / "too-many.csv", design="too-many")
