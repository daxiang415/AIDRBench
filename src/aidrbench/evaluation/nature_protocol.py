"""Fail-closed validation for the Nature Communications mechanism mainline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import yaml

from aidrbench.calibration.artifact import load_hardware_calibration_artifact
from aidrbench.data.splits import sha256_file
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.firm_flexibility import (
    lower_tolerance_order_statistic_rank,
    minimum_successes_for_wilson,
)

_SCENARIO_SET_NAMES = ("development", "validation", "locked_ood")
_CORE_DURATIONS = [1, 2, 3, 4, 6, 8]
_CORE_NOTICES = [0, 2, 6]
_CORE_RELIABILITIES = [0.90, 0.95, 0.99]


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _seed_set(value: object, name: str) -> set[int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be an inclusive [first, last] range")
    first, last = value
    if (
        isinstance(first, bool)
        or isinstance(last, bool)
        or not isinstance(first, int)
        or not isinstance(last, int)
        or first < 0
        or last < first
    ):
        raise ValueError(f"{name} must be a non-negative increasing integer range")
    return set(range(first, last + 1))


def _same_numeric_list(value: object, expected: Sequence[int | float]) -> bool:
    return isinstance(value, list) and [float(item) for item in value] == [
        float(item) for item in expected
    ]


def validate_nature_mainline_protocol(path: str | Path) -> dict[str, object]:
    """Validate that the declared experiment measures the NC estimands.

    This check deliberately rejects controller/RL-centric protocol fields and
    randomized multi-event primary configs. It does not generate scenarios or
    inspect the locked OOD set.
    """

    protocol_path = Path(path)
    if not protocol_path.is_file():
        raise FileNotFoundError(f"Nature mainline protocol does not exist: {protocol_path}")
    document = _mapping(
        yaml.safe_load(protocol_path.read_text(encoding="utf-8")),
        "Nature mainline protocol",
    )
    if document.get("schema_version") != 1:
        raise ValueError("Nature mainline protocol schema_version must be 1")
    if document.get("study_type") != "nature_communications_mechanism_mainline":
        raise ValueError("protocol is not a Nature Communications mechanism mainline")

    checks: dict[str, bool] = {}
    execution_checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    prohibited = {"rl_training_seeds", "controller_selection", "reward_search"}
    checks["no_controller_training_mainline"] = not bool(prohibited & set(document))
    estimand = _mapping(document.get("scientific_estimand"), "scientific_estimand")
    checks["three_capacity_layers"] = estimand.get("capacity_layers") == [
        "nominal",
        "perfect_information",
        "non_anticipative",
    ]
    checks["controller_training_not_required"] = (
        estimand.get("controller_training_required") is False
    )

    data = _mapping(document.get("data"), "data")
    data_rows: dict[str, object] = {}
    hashes_valid = True
    for name in ("community", "workload_sampler", "hardware_calibration"):
        entry = _mapping(data.get(name), f"data.{name}")
        data_path = Path(str(entry.get("path", "")))
        expected = str(entry.get("sha256", ""))
        exists = data_path.is_file()
        actual = sha256_file(data_path) if exists else None
        matches = exists and len(expected) == 64 and actual == expected
        hashes_valid = hashes_valid and matches
        data_rows[name] = {
            "path": str(data_path),
            "exists": exists,
            "hash_matches": matches,
            "sha256": actual,
        }
    execution_checks["input_hashes"] = hashes_valid
    details["data"] = data_rows

    calibration_entry = _mapping(
        data.get("hardware_calibration"), "data.hardware_calibration"
    )
    calibration_path = Path(str(calibration_entry.get("path", "")))
    calibration_manifest_matches = False
    calibration_details: dict[str, object] = {"path": str(calibration_path)}
    if calibration_path.is_file():
        try:
            calibration = load_hardware_calibration_artifact(calibration_path)
        except (KeyError, TypeError, ValueError) as exc:
            calibration_details["error"] = str(exc)
        else:
            sha_matches = (
                calibration.artifact_sha256
                == str(calibration_entry.get("artifact_sha256", ""))
            )
            evidence_matches = (
                calibration.evidence_class.value
                == str(calibration_entry.get("evidence_class", ""))
            )
            calibration_manifest_matches = sha_matches and evidence_matches
            calibration_details.update(
                {
                    "parsed_artifact_sha256": calibration.artifact_sha256,
                    "artifact_sha256_matches": sha_matches,
                    "parsed_evidence_class": calibration.evidence_class.value,
                    "evidence_class_matches": evidence_matches,
                }
            )
    checks["calibration_manifest_matches_artifact"] = calibration_manifest_matches
    details["hardware_calibration"] = calibration_details

    primary = _mapping(document.get("primary_single_event"), "primary_single_event")
    checks["core_duration_grid"] = _same_numeric_list(
        primary.get("duration_hours"), _CORE_DURATIONS
    )
    checks["core_notice_grid"] = _same_numeric_list(
        primary.get("notice_hours"), _CORE_NOTICES
    )
    checks["core_reliability_grid"] = _same_numeric_list(
        primary.get("reliability_targets"), _CORE_RELIABILITIES
    )
    checks["single_event_independent_trials"] = (
        primary.get("events_per_episode") == 1
        and primary.get("statistical_unit") == "independent_episode"
    )
    confidence_level = float(primary.get("confidence_level", 0.0))
    checks["declared_statistical_methods"] = (
        primary.get("pi_confidence_method")
        == "exact_binomial_nonparametric_lower_tolerance_bound"
        and primary.get("fixed_candidate_confidence_method")
        == "one_sided_wilson_lower_bound"
        and primary.get("non_anticipative_interpretation")
        == "restricted_scenario_based_causal_bound"
        and 0.0 < confidence_level < 1.0
    )

    criteria = _mapping(primary.get("success_criteria"), "primary_single_event.success_criteria")
    expected_criteria = {
        "min_delivery_ratio": 0.95,
        "min_interval_delivery_ratio": 0.95,
        "max_deadline_miss_rate": 0.01,
        "max_rebound_ratio": 0.25,
        "min_window_peak_relief_fraction": 0.50,
        "max_terminal_backlog_fraction": 0.02,
    }
    checks["success_criteria_schema"] = all(
        key in criteria and float(criteria[key]) == value
        for key, value in expected_criteria.items()
    ) and set(criteria) == set(expected_criteria)

    profile_split_path = Path(str(document.get("community_profile_split", "")))
    profile_split_valid = profile_split_path.is_file()
    profile_memberships: dict[str, set[str]] = {}
    if profile_split_valid:
        raw_profile_split = _mapping(
            yaml.safe_load(profile_split_path.read_text(encoding="utf-8")),
            "community profile split",
        )
        for set_name, split_name in (
            ("development", "train"),
            ("validation", "validation"),
            ("locked_ood", "test_ood"),
        ):
            raw_profiles = raw_profile_split.get(split_name)
            if not isinstance(raw_profiles, list) or not raw_profiles:
                profile_split_valid = False
                profile_memberships[set_name] = set()
            else:
                profile_memberships[set_name] = {str(value) for value in raw_profiles}
    checks["community_profile_split_manifest"] = profile_split_valid

    scenario_sets = _mapping(document.get("scenario_sets"), "scenario_sets")
    seed_sets: dict[str, set[int]] = {}
    scenario_rows: dict[str, object] = {}
    configs_valid = True
    single_event_configs = True
    calibration_coverage = True
    fixed_infrastructure = True
    node_counts: set[int] = set()
    criteria_match = True
    profiles_match = True
    configured_profiles: dict[str, str] = {}
    arrival_processes_match = True
    expected_arrival_processes = {
        "development": "nhpp",
        "validation": "nhpp",
        "locked_ood": "block",
    }
    for name in _SCENARIO_SET_NAMES:
        entry = _mapping(scenario_sets.get(name), f"scenario_sets.{name}")
        seeds = _seed_set(entry.get("episode_seed_range"), f"scenario_sets.{name}.seeds")
        seed_sets[name] = seeds
        expected_count = int(entry.get("independent_episode_count", -1))
        config_path = Path(str(entry.get("config", "")))
        row: dict[str, object] = {
            "config": str(config_path),
            "seed_count": len(seeds),
            "declared_episode_count": expected_count,
            "locked": entry.get("locked"),
        }
        try:
            config = load_hourly_environment_config(config_path)
        except (FileNotFoundError, ValueError) as exc:
            configs_valid = False
            single_event_configs = False
            calibration_coverage = False
            fixed_infrastructure = False
            criteria_match = False
            profiles_match = False
            arrival_processes_match = False
            row["loadable"] = False
            row["config_error"] = str(exc)
        else:
            seed_matches = config.episode_seed_range == (min(seeds), max(seeds))
            count_matches = expected_count == len(seeds)
            one_event = (
                len(config.event_start_hours) == 1
                and config.event_start_hours[0] == int(primary.get("event_start_hour", -1))
                and config.event_start_jitter_hours == 0
                and config.event_duration_choices is None
                and config.event_notice_choices is None
                and config.event_reduction_fraction_range is None
            )
            artifact_classes = (
                set(config.calibration_artifact.active_power_by_class)
                if config.calibration_artifact is not None
                else set()
            )
            used_classes = {
                job_class
                for job_class, share in config.workload_mix.shares.items()
                if share > 0.0
            }
            covered = (
                config.calibration_artifact is not None
                and used_classes.issubset(artifact_classes)
                and config.calibration_power_case == "nominal"
            )
            configs_valid = configs_valid and seed_matches and count_matches
            single_event_configs = single_event_configs and one_event
            calibration_coverage = calibration_coverage and covered
            infrastructure_fixed = isinstance(config.node_count, int)
            fixed_infrastructure = fixed_infrastructure and infrastructure_fixed
            if isinstance(config.node_count, int):
                node_counts.add(config.node_count)
            reward = config.reward
            thresholds_match = (
                reward.min_delivery_ratio
                == float(criteria.get("min_delivery_ratio", float("nan")))
                and reward.min_delivery_ratio
                == float(criteria.get("min_interval_delivery_ratio", float("nan")))
                and reward.max_deadline_miss_rate
                == float(criteria.get("max_deadline_miss_rate", float("nan")))
                and reward.max_rebound_ratio
                == float(criteria.get("max_rebound_ratio", float("nan")))
                and reward.min_window_peak_relief_fraction
                == float(
                    criteria.get("min_window_peak_relief_fraction", float("nan"))
                )
                and reward.max_terminal_backlog_fraction
                == float(criteria.get("max_terminal_backlog_fraction", float("nan")))
            )
            criteria_match = criteria_match and thresholds_match
            profile_id = config.community_profile_id or ""
            configured_profiles[name] = profile_id
            profile_matches = profile_id in profile_memberships.get(name, set())
            profiles_match = profiles_match and profile_matches
            arrival_matches = (
                config.alibaba_arrival_process == expected_arrival_processes[name]
            )
            arrival_processes_match = arrival_processes_match and arrival_matches
            row.update(
                {
                    "loadable": True,
                    "seed_range_matches": seed_matches,
                    "episode_count_matches": count_matches,
                    "single_event_primary": one_event,
                    "workload_classes": sorted(used_classes),
                    "all_workload_classes_calibrated": covered,
                    "fixed_node_count": config.node_count,
                    "success_criteria_match": thresholds_match,
                    "community_profile_id": profile_id,
                    "profile_matches_declared_split": profile_matches,
                    "arrival_process": config.alibaba_arrival_process,
                    "arrival_process_matches": arrival_matches,
                    "reference_mix_operating_peak_kw": (
                        config.make_power_model().reference_mix_operating_peak_kw
                    ),
                    "worst_class_peak_kw": config.make_power_model().worst_class_peak_kw,
                }
            )
        scenario_rows[name] = row
    checks["scenario_configs"] = configs_valid
    checks["single_event_primary_configs"] = single_event_configs
    checks["all_workload_classes_calibrated"] = calibration_coverage
    checks["infrastructure_fixed_across_power_cases"] = (
        fixed_infrastructure and len(node_counts) == 1
    )
    checks["success_criteria_match_configs"] = criteria_match
    checks["profiles_match_disjoint_split"] = (
        profiles_match and len(set(configured_profiles.values())) == len(_SCENARIO_SET_NAMES)
    )
    checks["arrival_processes_match_protocol"] = arrival_processes_match
    checks["scenario_seed_sets_disjoint"] = all(
        seed_sets[left].isdisjoint(seed_sets[right])
        for index, left in enumerate(_SCENARIO_SET_NAMES)
        for right in _SCENARIO_SET_NAMES[index + 1 :]
    )
    checks["locked_ood_declared_and_unconsumed"] = (
        scenario_sets["locked_ood"].get("locked") is True
        and document.get("locked_ood_status")
        in {"not_run", "approved_for_one_time_run"}
    )
    details["scenario_sets"] = scenario_rows

    sample_size_rows: list[dict[str, object]] = []
    locked_supports_all = True
    for set_name, seeds in seed_sets.items():
        for reliability in _CORE_RELIABILITIES:
            fixed_candidate_required = minimum_successes_for_wilson(
                len(seeds), reliability, confidence_level
            )
            pi_tolerance = lower_tolerance_order_statistic_rank(
                len(seeds), reliability, confidence_level
            )
            sufficient = fixed_candidate_required is not None and pi_tolerance is not None
            if set_name == "locked_ood":
                locked_supports_all = locked_supports_all and sufficient
            sample_size_rows.append(
                {
                    "scenario_set": set_name,
                    "trials": len(seeds),
                    "reliability_target": reliability,
                    "fixed_candidate_minimum_successes": fixed_candidate_required,
                    "pi_tolerance_order_statistic_rank": (
                        pi_tolerance[0] if pi_tolerance is not None else None
                    ),
                    "pi_achieved_tolerance_confidence": (
                        pi_tolerance[1] if pi_tolerance is not None else None
                    ),
                    "sample_size_sufficient": sufficient,
                }
            )
    checks["locked_sample_supports_reliability_grid"] = locked_supports_all
    details["statistical_power"] = sample_size_rows

    repeated = _mapping(
        document.get("repeated_event_exhaustion"), "repeated_event_exhaustion"
    )
    checks["repeated_events_are_separate"] = (
        repeated.get("separate_from_primary_surface") is True
        and repeated.get("statistical_unit") == "joint_episode"
    )
    hosting = _mapping(document.get("hosting_capacity"), "hosting_capacity")
    matrix = _mapping(hosting.get("portfolio_matrix"), "hosting_capacity.portfolio_matrix")
    checks["hosting_2x2x2_declared"] = all(
        isinstance(matrix.get(axis), list) and len(matrix[axis]) == 2
        for axis in ("dc_operation", "pv", "bess")
    )
    checks["hosting_is_planning_bound"] = (
        hosting.get("optimization_layer") == "perfect_information_planning_bound"
    )

    execution_checks["optimization_runtime_dependencies"] = all(
        find_spec(module) is not None for module in ("cvxpy", "highspy", "pyarrow", "scipy")
    )
    structure_valid = all(checks.values())
    execution_ready = structure_valid and all(execution_checks.values())
    combined_checks = {**checks, **execution_checks}

    return {
        # ``valid`` remains a compatibility alias for clean-checkout CI. New
        # callers should use the explicit two-level fields below.
        "valid": structure_valid,
        "structure_valid": structure_valid,
        "execution_ready": execution_ready,
        "protocol": str(protocol_path),
        "checks": combined_checks,
        "structure_checks": checks,
        "execution_checks": execution_checks,
        "details": details,
    }
