from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.calibration.artifact import calibration_artifact_sha256
from aidrbench.evaluation.economic_reserve_mapping import (
    export_reserve_mapping_sensitivity,
    load_reserve_mapping_specification,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_calibration(path: Path) -> tuple[str, str]:
    parameter_common = {
        "uncertainty_method": "test_interval",
        "statistical_unit": "test_unit",
        "independent_unit_count": 2,
        "confidence_level": 0.95,
    }
    document = {
        "schema_version": "aidrbench.hardware_calibration.v2",
        "artifact_id": "test_4gpu_v1",
        "hardware": {
            "identifier": "test GPU",
            "topology_identifier": "4x_gpu_test_node",
        },
        "measurement": {"method": "test board-power telemetry"},
        "parameters": {
            "idle_power_w_per_gpu": {
                "estimate_w": 20.0,
                "uncertainty_interval_w": [15.0, 25.0],
                **parameter_common,
            },
            "node_fixed_overhead_w": {
                "estimate_w": 100.0,
                "uncertainty_interval_w": [50.0, 150.0],
                "uncertainty_method": "engineering_assumption_range_no_node_meter",
                "statistical_unit": "engineering_assumption",
                "independent_unit_count": 0,
            },
            "active_power_w_per_gpu_by_class": {
                "training": {
                    "estimate_w": 200.0,
                    "uncertainty_interval_w": [180.0, 220.0],
                    **parameter_common,
                },
                "offline_inference": {
                    "estimate_w": 300.0,
                    "uncertainty_interval_w": [280.0, 320.0],
                    **parameter_common,
                },
            },
        },
        "validation": {"held_out_power_mae_w": 2.0},
        "evidence_class": "benchmark_anchored_synthetic",
    }
    artifact_sha256 = calibration_artifact_sha256(document)
    document["artifact_sha256"] = artifact_sha256
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return _sha256(path), artifact_sha256


def _write_ledgers(directory: Path, *, calibration_artifact_sha256: str) -> dict[str, str]:
    directory.mkdir()
    event_rows: list[dict[str, object]] = []
    interval_rows: list[dict[str, object]] = []
    debts = (1.0, 2.0, 3.0, 10.0)
    for duration in (2, 4, 8):
        candidate = 50.0 - duration
        for scenario_index, debt in enumerate(debts):
            start = 20
            stop = start + duration
            common = {
                "scenario_id": f"scenario_{scenario_index}",
                "scenario_hash": f"{scenario_index + 1:064x}",
                "episode_seed": 100 + scenario_index,
                "event_id": 0,
                "duration_h": duration,
                "notice_h": 0,
            }
            event_rows.append(
                {
                    **common,
                    "event_start_hour": start,
                    "event_stop_hour": stop,
                    "technical_capacity_ceiling_kw": candidate,
                    "offer_fraction_of_technical_ceiling": 1.0,
                    "candidate_reduction_kw": candidate,
                    "technical_success": scenario_index != 3,
                }
            )
            interval_rows.append(
                {
                    **common,
                    "candidate_reduction_kw": candidate,
                    "hour": stop - 1,
                    "relative_hour": duration - 1,
                    "event_active": True,
                    "backlog_delta_gpu_h": debt,
                }
            )
    event_path = directory / "episode_ledger.parquet"
    interval_path = directory / "interval_ledger.parquet"
    pd.DataFrame(event_rows).to_parquet(event_path, index=False)
    pd.DataFrame(interval_rows).to_parquet(interval_path, index=False)
    hashes = {"event": _sha256(event_path), "interval": _sha256(interval_path)}
    manifest = {
        "schema_version": 2,
        "analysis_id": "test_economic_ledger",
        "analysis_role": "development_parameterized_screening",
        "event_ledger_sha256": hashes["event"],
        "interval_ledger_sha256": hashes["interval"],
        "event_row_count": len(event_rows),
        "interval_row_count": len(interval_rows),
        "technical_provenance": {
            "calibration_artifact_sha256": calibration_artifact_sha256
        },
    }
    manifest_path = directory / "ledger_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    hashes["manifest"] = _sha256(manifest_path)
    return hashes


def _write_specification(path: Path, ledger: Path, calibration: Path) -> None:
    artifact = yaml.safe_load(calibration.read_text(encoding="utf-8"))
    hashes = {
        "manifest": _sha256(ledger / "ledger_manifest.json"),
        "event": _sha256(ledger / "episode_ledger.parquet"),
        "interval": _sha256(ledger / "interval_ledger.parquet"),
    }
    document = {
        "schema_version": "aidrbench.economic_reserve_mapping.v1",
        "analysis_id": "test_reserve_mapping",
        "analysis_role": "supplementary_diagnostic_physical_mapping",
        "inputs": {
            "ledger_directory": str(ledger),
            "ledger_manifest_sha256": hashes["manifest"],
            "episode_ledger_sha256": hashes["event"],
            "interval_ledger_sha256": hashes["interval"],
            "calibration_artifact": str(calibration),
            "calibration_file_sha256": _sha256(calibration),
            "calibration_artifact_sha256": artifact["artifact_sha256"],
            "expected_ledger_analysis_id": "test_economic_ledger",
            "expected_ledger_analysis_role": "development_parameterized_screening",
        },
        "selection": {
            "duration_hours": [2, 4, 8],
            "notice_hours": 0,
            "offer_fraction_of_technical_ceiling": 1.0,
            "event_id": 0,
            "expected_scenarios_per_duration": 4,
        },
        "mapping": {
            "debt_quantiles": [0.5, 0.95],
            "quantile_method": "linear",
            "recovery_target_hours": [2, 4, 8, 12, 24],
            "recovery_execution_efficiencies": [0.7, 0.85, 1.0],
            "gpus_per_node": 4,
            "pue": 1.2,
            "pue_parameter_status": "engineering_assumption_from_model_a",
            "node_overhead_cases": [
                {
                    "case_id": statistic,
                    "artifact_statistic": statistic,
                    "parameter_status": "engineering_assumption_range_no_node_meter",
                }
                for statistic in ("lower_bound", "nominal", "upper_bound")
            ],
            "active_power_cases": [
                {
                    "case_id": "training",
                    "class_weights": {"training": 1.0},
                    "parameter_status": "measured_board_power_estimate",
                },
                {
                    "case_id": "declared_flexible_mix",
                    "class_weights": {
                        "training": 2.0 / 3.0,
                        "offline_inference": 1.0 / 3.0,
                    },
                    "parameter_status": "model_weighted_measured_board_power_estimate",
                },
                {
                    "case_id": "offline_inference",
                    "class_weights": {"offline_inference": 1.0},
                    "parameter_status": "measured_board_power_estimate",
                },
            ],
        },
        "interpretation": {
            "gpu_count_term": "recovery-throughput-equivalent reserved GPU count",
            "capital_cost_evaluation": "disabled",
            "prohibited_claims": [
                "firm_gpu_count",
                "required_gpu_count",
                "hardware_purchase_requirement",
            ],
        },
    }
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


@pytest.fixture
def mapping_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    calibration = tmp_path / "calibration.yaml"
    _, artifact_sha256 = _write_calibration(calibration)
    ledger = tmp_path / "ledger"
    _write_ledgers(ledger, calibration_artifact_sha256=artifact_sha256)
    specification = tmp_path / "mapping.yaml"
    _write_specification(specification, ledger, calibration)
    return specification, ledger, calibration


def test_reserve_mapping_uses_event_end_debt_and_explicit_power_layers(
    mapping_inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    specification, _, _ = mapping_inputs
    output = tmp_path / "mapping_output"
    result = export_reserve_mapping_sensitivity(specification, output)

    assert result["final_publish"] == "atomic_directory_rename"
    frame = pd.read_csv(output / "reserve_mapping_summary.csv")
    assert len(frame) == 3 * 2 * 5 * 3 * 3 * 3
    selected = frame[
        (frame["duration_h"] == 2)
        & (frame["event_debt_quantile_label"] == "q50")
        & (frame["recovery_target_h"] == 2)
        & (frame["recovery_execution_efficiency"] == 1.0)
        & (frame["active_power_case"] == "training")
        & (frame["node_overhead_case"] == "nominal")
    ].iloc[0]
    assert selected["event_end_paired_backlog_debt_gpu_h"] == pytest.approx(2.5)
    assert selected["continuous_recovery_throughput_equivalent_gpu_count"] == pytest.approx(
        1.25
    )
    assert selected["recovery_throughput_equivalent_gpu_count_node_rounded"] == 4
    assert selected["recovery_throughput_equivalent_node_count"] == 1
    assert selected["installed_it_power_kw"] == pytest.approx(0.9)
    assert selected["installed_facility_power_kw"] == pytest.approx(1.08)
    assert selected["recovery_dynamic_facility_power_kw"] == pytest.approx(0.864)
    assert selected["capital_cost_evaluation"] == "disabled"
    assert pd.isna(selected["capital_cost"])

    manifest = json.loads((output / "reserve_mapping_manifest.json").read_text())
    assert manifest["output"]["row_count"] == len(frame)
    assert manifest["output"]["sha256"] == _sha256(
        output / "reserve_mapping_summary.csv"
    )
    assert manifest["parameter_evidence"]["capital_cost"] == "not evaluated; null by design"
    assert manifest["final_publish"] == "atomic_directory_rename"
    with pytest.raises(FileExistsError, match="already exists"):
        export_reserve_mapping_sensitivity(specification, output)


def test_reserve_mapping_fails_closed_on_tampered_interval_ledger(
    mapping_inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    specification, ledger, _ = mapping_inputs
    interval = ledger / "interval_ledger.parquet"
    interval.write_bytes(interval.read_bytes() + b"tampered")
    output = tmp_path / "must_not_publish"
    with pytest.raises(ValueError, match="interval ledger SHA-256 mismatch"):
        export_reserve_mapping_sensitivity(specification, output)
    assert not output.exists()


def test_reserve_mapping_rejects_unknown_configuration_fields(
    mapping_inputs: tuple[Path, Path, Path]
) -> None:
    specification, _, _ = mapping_inputs
    document = yaml.safe_load(specification.read_text(encoding="utf-8"))
    document["mapping"]["implicit_capex"] = 1.0
    specification.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="mapping fields mismatch"):
        load_reserve_mapping_specification(specification)


def test_repository_reserve_mapping_contract_is_parseable() -> None:
    root = Path(__file__).resolve().parents[1]
    specification = load_reserve_mapping_specification(
        root / "configs/economics/reserve_mapping_sensitivity_v1.yaml"
    )
    assert specification.mapping.recovery_target_hours == (2, 4, 8, 12, 24)
    assert specification.mapping.recovery_execution_efficiencies == (0.7, 0.85, 1.0)
    assert specification.mapping.gpus_per_node == 4
    assert specification.normalized_sha256
