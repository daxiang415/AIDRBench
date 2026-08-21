"""Validation for the locked hourly train/validation/test experiment protocol."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.envs.community_ai_dr_env import OBSERVATION_VERSION
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria

SPLIT_NAMES = ("train", "validation", "test")


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result = [str(item) for item in value]
    if len(set(result)) != len(result):
        raise ValueError(f"{name} entries must be unique")
    return result


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


def _load_yaml_mapping(path: Path, name: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{name} does not exist: {path}")
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _mapping(raw, name)


def validate_hourly_experiment_protocol(path: str | Path) -> dict[str, object]:
    """Validate data hashes, disjoint seeds/profiles, configs, and frozen criteria."""

    protocol_path = Path(path)
    document = _load_yaml_mapping(protocol_path, "experiment protocol")
    if document.get("schema_version") != 1:
        raise ValueError("experiment protocol schema_version must be 1")
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    checks["test_locked"] = document.get("test_locked") is True
    interface = _mapping(document.get("environment_interface"), "environment_interface")
    checks["environment_interface_frozen"] = interface == {
        "observation_version": OBSERVATION_VERSION,
        "reward_version": "firm_threshold_v2",
        "step_order": "arrivals_observation_action",
    }
    details["environment_interface"] = interface
    rl_seeds = _string_list(document.get("rl_training_seeds"), "rl_training_seeds")
    checks["at_least_five_rl_training_seeds"] = len(rl_seeds) >= 5

    raw_data = _mapping(document.get("data"), "data")
    data_details: dict[str, object] = {}
    data_valid = True
    for name, raw_entry in raw_data.items():
        entry = _mapping(raw_entry, f"data.{name}")
        data_path = Path(str(entry.get("path", "")))
        expected_hash = str(entry.get("sha256", ""))
        exists = data_path.is_file()
        actual_hash = sha256_file(data_path) if exists else None
        matches = exists and bool(expected_hash) and actual_hash == expected_hash
        data_valid = data_valid and matches
        data_details[name] = {
            "path": str(data_path),
            "exists": exists,
            "hash_matches": matches,
            "sha256": actual_hash,
        }
    checks["data_hashes"] = data_valid
    details["data"] = data_details
    sampler_entry = _mapping(raw_data.get("workload_sampler"), "data.workload_sampler")
    expected_sampler_path = Path(str(sampler_entry.get("path", ""))).resolve()

    profile_split_path = Path(str(document.get("community_profile_split", "")))
    profile_document = _load_yaml_mapping(profile_split_path, "community profile split")
    profile_memberships = {
        "train": set(_string_list(profile_document.get("train"), "profile split train")),
        "validation": set(
            _string_list(profile_document.get("validation"), "profile split validation")
        ),
        "test": set(_string_list(profile_document.get("test_ood"), "profile split test_ood")),
    }
    checks["community_profiles_disjoint"] = all(
        profile_memberships[left].isdisjoint(profile_memberships[right])
        for index, left in enumerate(SPLIT_NAMES)
        for right in SPLIT_NAMES[index + 1 :]
    )

    raw_splits = _mapping(document.get("splits"), "splits")
    criteria_mapping = _mapping(document.get("frozen_criteria"), "frozen_criteria")
    split_seed_sets: dict[str, set[int]] = {}
    split_details: dict[str, object] = {}
    configs_valid = True
    profiles_valid = True
    independent_arrivals = True
    reward_specs_match = True
    for split_name in SPLIT_NAMES:
        split = _mapping(raw_splits.get(split_name), f"splits.{split_name}")
        seeds = _seed_set(split.get("episode_seed_range"), f"{split_name} episode_seed_range")
        expected_seed_range = (min(seeds), max(seeds))
        split_seed_sets[split_name] = seeds
        configured_profiles = set(
            _string_list(split.get("community_profiles"), f"{split_name} community_profiles")
        )
        profiles_valid = profiles_valid and configured_profiles.issubset(
            profile_memberships[split_name]
        )
        config_paths = [
            Path(value) for value in _string_list(split.get("configs"), f"{split_name} configs")
        ]
        config_rows: list[dict[str, object]] = []
        for config_path in config_paths:
            exists = config_path.is_file()
            if not exists:
                configs_valid = False
                config_rows.append({"path": str(config_path), "exists": False})
                continue
            try:
                config = load_hourly_environment_config(config_path)
            except (FileNotFoundError, ValueError) as exc:
                # Protocol inspection must be usable on a clean checkout, but
                # formal execution remains fail-closed. A missing calibration
                # artifact or malformed config is therefore an explicit failed
                # readiness check rather than an uncaught validator exception.
                configs_valid = False
                config_rows.append(
                    {
                        "path": str(config_path),
                        "exists": True,
                        "loadable": False,
                        "config_error": str(exc),
                    }
                )
                continue
            power_model = config.make_power_model()
            actual_dc_peak_kw = power_model.predict(
                power_model.flexible_capacity_gpu_h
            ).dc_power_kw
            profile_matches = config.community_profile_id in configured_profiles
            seed_range_matches = config.episode_seed_range == expected_seed_range
            uses_trace_sampler = (
                config.workload_source == "alibaba2026_lite"
                and config.alibaba_summary_path is not None
                and config.alibaba_arrivals_path is None
                and config.alibaba_summary_path.resolve() == expected_sampler_path
            )
            reward_matches = (
                config.reward.version == interface.get("reward_version")
                and config.reward.min_delivery_ratio == criteria_mapping["min_delivery_ratio"]
                and config.reward.max_deadline_miss_rate
                == criteria_mapping["max_deadline_miss_rate"]
                and config.reward.max_rebound_ratio == criteria_mapping["max_rebound_ratio"]
                and config.reward.min_window_peak_relief_fraction
                == criteria_mapping["min_window_peak_relief_fraction"]
                and config.reward.max_terminal_backlog_fraction
                == criteria_mapping["max_terminal_backlog_fraction"]
            )
            configs_valid = configs_valid and profile_matches and seed_range_matches
            independent_arrivals = independent_arrivals and uses_trace_sampler
            reward_specs_match = reward_specs_match and reward_matches
            config_rows.append(
                {
                    "path": str(config_path),
                    "exists": True,
                    "loadable": True,
                    "action_mode": config.action_mode,
                    "community_profile_id": config.community_profile_id,
                    "profile_matches": profile_matches,
                    "episode_seed_range": config.episode_seed_range,
                    "seed_range_matches": seed_range_matches,
                    "independent_arrivals": uses_trace_sampler,
                    "reward_version": config.reward.version,
                    "reward_thresholds_match": reward_matches,
                    "background_community_peak_kw": config.background_community_peak_kw,
                    "pcc_capacity_kw": config.pcc_capacity_kw,
                    "target_dc_peak_kw": config.target_dc_peak_kw,
                    "actual_dc_peak_kw": actual_dc_peak_kw,
                    "actual_dc_peak_fraction_of_pcc": (
                        actual_dc_peak_kw / config.pcc_capacity_kw
                    ),
                    "dc_peak_sizing_error_kw": actual_dc_peak_kw - config.target_dc_peak_kw,
                }
            )
        split_details[split_name] = {
            "episode_seed_first": min(seeds),
            "episode_seed_last": max(seeds),
            "episode_seed_count": len(seeds),
            "community_profiles": sorted(configured_profiles),
            "configs": config_rows,
        }
    checks["episode_seeds_disjoint"] = all(
        split_seed_sets[left].isdisjoint(split_seed_sets[right])
        for index, left in enumerate(SPLIT_NAMES)
        for right in SPLIT_NAMES[index + 1 :]
    )
    checks["profiles_match_split_manifest"] = profiles_valid
    checks["environment_configs"] = configs_valid
    checks["independent_trace_calibrated_arrivals"] = independent_arrivals
    checks["reward_thresholds_match_frozen_criteria"] = reward_specs_match
    details["splits"] = split_details

    criteria = FirmFlexibilityCriteria(**criteria_mapping)
    checks["firm_flexibility_criteria_frozen"] = criteria.as_dict() == criteria_mapping
    details["frozen_criteria"] = criteria.as_dict()
    valid = all(checks.values())
    return {
        "valid": valid,
        "protocol": str(protocol_path),
        "checks": checks,
        "details": details,
    }
