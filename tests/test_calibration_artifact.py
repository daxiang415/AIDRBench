from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aidrbench.calibration.artifact import (
    HARDWARE_CALIBRATION_SCHEMA_VERSION,
    calibration_artifact_sha256,
    load_hardware_calibration_artifact,
)
from aidrbench.cli import main
from aidrbench.envs.hourly_config import load_hourly_environment_config

ROOT = Path(__file__).resolve().parents[1]


def _write_artifact(
    path: Path,
    *,
    classes: dict[str, float] | None = None,
) -> None:
    classes = classes or {"training": 450.0, "offline_inference": 350.0}
    document: dict[str, object] = {
        "schema_version": HARDWARE_CALIBRATION_SCHEMA_VERSION,
        "artifact_id": "test-four-gpu-node-v1",
        "hardware": {
            "identifier": "test-gpu",
            "topology_identifier": "single-node-4gpu",
        },
        "measurement": {"method": "pdu_plus_nvidia_smi"},
        "parameters": {
            "idle_power_w_per_gpu": {
                "estimate_w": 80.0,
                "confidence_interval_w": [70.0, 90.0],
            },
            "node_fixed_overhead_w": {
                "estimate_w": 300.0,
                "confidence_interval_w": [260.0, 340.0],
            },
            "active_power_w_per_gpu_by_class": {
                job_class: {
                    "estimate_w": power_w,
                    "confidence_interval_w": [power_w - 20.0, power_w + 20.0],
                }
                for job_class, power_w in classes.items()
            },
        },
        "validation": {"held_out_power_mae_w": 12.0},
        "evidence_class": "measured",
    }
    document["artifact_sha256"] = calibration_artifact_sha256(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_hardware_calibration_artifact_is_hash_verified_and_cli_readable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact_path = tmp_path / "calibration.yaml"
    _write_artifact(artifact_path)

    artifact = load_hardware_calibration_artifact(artifact_path)
    exit_code = main(["calibrate", "validate-artifact", "--artifact", str(artifact_path)])

    assert artifact.active_power_by_class == {
        "offline_inference": 350.0,
        "training": 450.0,
    }
    assert artifact.active_power_intervals_by_class["training"] == (430.0, 470.0)
    assert exit_code == 0
    assert '"evidence_class": "measured"' in capsys.readouterr().out


def test_hardware_calibration_artifact_rejects_tampered_payload(tmp_path: Path) -> None:
    artifact_path = tmp_path / "calibration.yaml"
    _write_artifact(artifact_path)
    document = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    document["parameters"]["idle_power_w_per_gpu"]["estimate_w"] = 85.0
    artifact_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256"):
        load_hardware_calibration_artifact(artifact_path)


def test_hourly_config_consumes_calibration_artifact_and_rejects_missing_flexible_class(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "calibration.yaml"
    _write_artifact(artifact_path)
    document = yaml.safe_load((ROOT / "configs/env/hourly_continuous.yaml").read_text())
    document["hardware"] = {
        "calibration_artifact": str(artifact_path),
        "require_calibration_artifact": True,
    }

    config = load_hourly_environment_config(document)

    assert config.calibration_artifact is not None
    assert config.idle_power_w_per_gpu == pytest.approx(80.0)
    assert config.active_power_w_by_class["training"] == pytest.approx(450.0)
    assert config.make_power_model().flexible_active_power_by_class["offline_inference"] == (
        pytest.approx(350.0)
    )

    document["hardware"]["calibration_power_case"] = "upper_ci"
    upper_case = load_hourly_environment_config(document)
    assert upper_case.idle_power_w_per_gpu == pytest.approx(90.0)
    assert upper_case.active_power_w_by_class["training"] == pytest.approx(470.0)
    assert upper_case.calibration_power_case == "upper_ci"

    _write_artifact(artifact_path, classes={"offline_inference": 350.0})
    with pytest.raises(ValueError, match="no active-power estimate"):
        load_hourly_environment_config(document)


def test_hourly_config_requires_an_artifact_when_declared_formal() -> None:
    document = yaml.safe_load((ROOT / "configs/env/hourly_continuous.yaml").read_text())
    document["hardware"] = {"require_calibration_artifact": True}

    with pytest.raises(ValueError, match="requires calibration_artifact"):
        load_hourly_environment_config(document)


def test_hourly_config_rejects_unknown_and_ambiguous_hardware_fields(
    tmp_path: Path,
) -> None:
    document = yaml.safe_load((ROOT / "configs/env/hourly_continuous.yaml").read_text())
    document["hardware"]["calibration_file"] = "obsolete.csv"
    with pytest.raises(ValueError, match="unknown fields.*calibration_file"):
        load_hourly_environment_config(document)

    artifact_path = tmp_path / "calibration.yaml"
    _write_artifact(artifact_path)
    document["hardware"] = {
        "calibration_artifact": str(artifact_path),
        "fallback_idle_power_w_per_gpu": 80.0,
    }
    with pytest.raises(ValueError, match="cannot be combined with fallback"):
        load_hourly_environment_config(document)


def test_formal_config_fails_closed_when_declared_artifact_is_missing(tmp_path: Path) -> None:
    document = yaml.safe_load(
        (ROOT / "configs/env/hourly_formal_validation.yaml").read_text()
    )
    document["hardware"]["calibration_artifact"] = str(tmp_path / "missing.yaml")
    with pytest.raises(FileNotFoundError, match="missing.yaml"):
        load_hourly_environment_config(document)


def test_repository_formal_config_uses_verified_gpu_measurement_anchor() -> None:
    config = load_hourly_environment_config(
        ROOT / "configs/env/hourly_formal_validation.yaml"
    )

    assert config.calibration_artifact is not None
    assert config.calibration_artifact.artifact_id == "rtx6000pro_4gpu_v1"
    assert config.calibration_artifact.evidence_class.value == (
        "benchmark_anchored_synthetic"
    )
    assert set(config.calibration_artifact.active_power_by_class) == {
        "training",
        "offline_inference",
    }


def test_strict_power_coverage_rejects_uncalibrated_rigid_class(tmp_path: Path) -> None:
    artifact_path = tmp_path / "calibration.yaml"
    _write_artifact(artifact_path)
    document = yaml.safe_load((ROOT / "configs/env/hourly_continuous.yaml").read_text())
    document["hardware"] = {
        "calibration_artifact": str(artifact_path),
        "require_calibration_artifact": True,
        "require_all_workload_class_power": True,
    }

    with pytest.raises(ValueError, match="all configured.*online_inference"):
        load_hourly_environment_config(document)


def test_hourly_config_rejects_subhourly_timestep_until_queue_is_generalized() -> None:
    document = yaml.safe_load((ROOT / "configs/env/hourly_continuous.yaml").read_text())
    document["env"]["timestep_hours"] = 0.25

    with pytest.raises(ValueError, match="timestep_hours == 1.0"):
        load_hourly_environment_config(document)
