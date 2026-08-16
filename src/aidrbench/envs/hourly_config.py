"""Configuration parsing for the V0 hourly demand-response environments."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from aidrbench.calibration.artifact import (
    HardwareCalibrationArtifact,
    load_hardware_calibration_artifact,
)
from aidrbench.data.alibaba2026 import AlibabaDeadlinePolicy
from aidrbench.data.hourly import WorkloadMix
from aidrbench.models.power import HourlyDataCenterPowerModel, VirtualDataCenter
from aidrbench.workloads.deadline_buckets import DEFAULT_BUCKET_LABELS_H

ActionMode = Literal["continuous", "discrete"]


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _positive_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _fraction(value: object, name: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0 or result > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    if not allow_zero and result == 0.0:
        raise ValueError(f"{name} must be in (0, 1]")
    return result


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _non_negative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _int_list(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result = tuple(_positive_int(item, f"{name} entry") for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} entries must be unique")
    return result


def _non_negative_int_list(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result = tuple(_non_negative_int(item, f"{name} entry") for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} entries must be unique")
    return result


def _fraction_range(value: object, name: str) -> tuple[float, float] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be [lower, upper] or null")
    lower = _fraction(value[0], f"{name}[0]")
    upper = _fraction(value[1], f"{name}[1]")
    if upper < lower:
        raise ValueError(f"{name} upper bound must be at least its lower bound")
    return lower, upper


def _non_negative_int_range(value: object, name: str) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be [lower, upper] or null")
    lower = _non_negative_int(value[0], f"{name}[0]")
    upper = _non_negative_int(value[1], f"{name}[1]")
    if upper < lower:
        raise ValueError(f"{name} upper bound must be at least its lower bound")
    return lower, upper


def _deadline_bucket_labels(value: object, max_deadline_hours: int) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("workload.deadline_buckets must be a non-empty list")
    labels: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError("workload.deadline_buckets entries must be non-negative integers")
        labels.append(item)
    result = tuple(labels)
    if result[0] != 0 or tuple(sorted(result)) != result or len(set(result)) != len(result):
        raise ValueError("workload.deadline_buckets must be sorted, unique, and begin at zero")
    if result[-1] != max_deadline_hours:
        raise ValueError("workload.deadline_buckets must end at max_deadline_hours")
    return result


def _string_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result = tuple(str(item).strip().lower() for item in value if str(item).strip())
    if not result:
        raise ValueError(f"{name} must include a non-empty value")
    return result


@dataclass(frozen=True, slots=True)
class RewardSpecification:
    """Threshold-normalized scalar adapter over independently reported costs."""

    version: Literal["firm_threshold_v2"]
    min_delivery_ratio: float
    max_deadline_miss_rate: float
    max_rebound_ratio: float
    min_window_peak_relief_fraction: float
    max_terminal_backlog_fraction: float
    delivery_violation_weight: float
    feasibility_violation_weight: float
    deadline_violation_weight: float
    rebound_violation_weight: float
    window_violation_weight: float
    terminal_violation_weight: float
    excess_backlog_weight: float
    switching_weight: float


@dataclass(frozen=True, slots=True)
class HourlyEnvironmentConfig:
    """Parsed V0 configuration, intentionally limited to hourly load shifting."""

    seed: int
    action_mode: ActionMode
    timestep_hours: float
    episode_days: int
    clearance_tail_hours: int
    forecast_horizon_hours: int
    episode_seed_range: tuple[int, int] | None
    max_deadline_hours: int
    deadline_bucket_labels_h: tuple[int, ...]
    community_source: Literal["synthetic", "nrel_eulp"]
    community_path: Path | None
    community_profile_id: str | None
    community_episode_start: str | None
    frozen_scenario_path: Path | None
    frozen_event_ids: tuple[int, ...] | None
    background_community_peak_kw: float
    pcc_capacity_kw: float
    pv_enabled: bool
    gpus_per_node: int
    node_count: int | Literal["auto"]
    target_dc_peak_share_of_pcc: float
    flexible_gpu_fraction: float
    target_total_utilization: float
    workload_mix: WorkloadMix
    workload_source: Literal["synthetic", "alibaba2026_lite"]
    alibaba_summary_path: Path | None
    alibaba_arrivals_path: Path | None
    alibaba_arrival_process: Literal["nhpp", "block"]
    flexible_priorities: tuple[str, ...]
    deadline_policy: AlibabaDeadlinePolicy
    idle_power_w_per_gpu: float
    active_power_w_by_class: dict[str, float]
    node_fixed_overhead_w: float
    calibration_artifact: HardwareCalibrationArtifact | None
    calibration_power_case: Literal["lower_ci", "nominal", "upper_ci"]
    pue: float
    dr_source: Literal["configured", "manifest"]
    dr_manifest_path: Path | None
    event_start_hours: tuple[int, ...]
    event_duration_hours: int
    event_notice_hours: int
    event_reduction_fraction: float
    event_reduction_kw: float | None
    recovery_window_hours: int
    recovery_backlog_tolerance_fraction: float
    event_start_jitter_hours: int
    event_duration_choices: tuple[int, ...] | None
    event_notice_choices: tuple[int, ...] | None
    event_reduction_fraction_range: tuple[float, float] | None
    reward: RewardSpecification

    @property
    def main_hours(self) -> int:
        return int(round(self.episode_days * 24 / self.timestep_hours))

    @property
    def total_hours(self) -> int:
        return self.main_hours + int(round(self.clearance_tail_hours / self.timestep_hours))

    @property
    def community_peak_kw(self) -> float:
        """Legacy alias for the background-community gross-demand peak.

        ``community_peak_kw`` formerly overloaded the background-load scale
        and the PCC base.  New configurations should use
        ``background_community_peak_kw`` and ``pcc_capacity_kw`` explicitly.
        The alias keeps third-party V0 configurations readable while ensuring
        the environment itself no longer treats the two quantities as equal.
        """

        return self.background_community_peak_kw

    @property
    def target_dc_peak_share_of_community(self) -> float:
        """Legacy alias retained for code written against the V0 schema."""

        return self.target_dc_peak_share_of_pcc

    @property
    def target_dc_peak_kw(self) -> float:
        """Requested full-pool data-centre facility peak on the PCC base."""

        return self.pcc_capacity_kw * self.target_dc_peak_share_of_pcc

    def _average_active_power(self, *, flexible: bool) -> float:
        weights: dict[str, float] = {}
        for name, share in self.workload_mix.shares.items():
            fraction = self.workload_mix.flexible_fractions[name]
            weight = share * fraction if flexible else share * (1.0 - fraction)
            if weight > 0.0:
                weights[name] = weight
        if not weights:
            return self.idle_power_w_per_gpu
        total_weight = sum(weights.values())
        return (
            sum(
                weight * self.active_power_w_by_class.get(name, self.idle_power_w_per_gpu)
                for name, weight in weights.items()
            )
            / total_weight
        )

    def _rigid_utilization(self) -> float:
        """Return the fixed rigid-pool utilization used in every node candidate."""

        rigid_physical_share = 1.0 - self.flexible_gpu_fraction
        if rigid_physical_share <= 0.0:
            return 0.0
        return min(
            self.target_total_utilization
            * self.workload_mix.rigid_share
            / rigid_physical_share,
            1.0,
        )

    def _power_model_for_node_count(self, node_count: int) -> HourlyDataCenterPowerModel:
        """Build the final model used to evaluate a particular node count."""

        flexible_active = self._average_active_power(flexible=True)
        rigid_active = self._average_active_power(flexible=False)
        data_center = VirtualDataCenter(
            gpus_per_node=self.gpus_per_node,
            node_count=node_count,
            flexible_gpu_fraction=self.flexible_gpu_fraction,
        )
        return HourlyDataCenterPowerModel(
            data_center=data_center,
            idle_power_w_per_gpu=self.idle_power_w_per_gpu,
            flexible_active_power_w_per_gpu=flexible_active,
            rigid_active_power_w_per_gpu=rigid_active,
            node_fixed_overhead_w=self.node_fixed_overhead_w,
            rigid_gpu_utilization=self._rigid_utilization(),
            pue=self.pue,
            flexible_active_power_w_per_gpu_by_class=tuple(
                sorted(self.active_power_w_by_class.items())
            ),
        )

    def make_power_model(self) -> HourlyDataCenterPowerModel:
        """Derive a virtual cluster whose *final-model* peak meets the target.

        Auto sizing searches the exact discrete node model, including the
        configured workload mix, flexible-pool rounding, rigid utilization,
        idle draw, node overhead and PUE.  It therefore avoids the old
        per-node approximation that could materially undershoot the requested
        DC penetration.
        """

        if self.node_count != "auto":
            return self._power_model_for_node_count(self.node_count)

        target_peak_kw = self.target_dc_peak_kw

        def full_pool_peak(node_count: int) -> float:
            model = self._power_model_for_node_count(node_count)
            return model.predict(model.flexible_capacity_gpu_h).dc_power_kw

        lower = 1
        if full_pool_peak(lower) >= target_peak_kw:
            return self._power_model_for_node_count(lower)
        upper = lower
        # A monotone bracket plus binary search gives the smallest feasible
        # node count without relying on an approximate watts-per-node formula.
        for _ in range(64):
            upper *= 2
            if full_pool_peak(upper) >= target_peak_kw:
                break
        else:
            raise ValueError("could not bracket automatic virtual data-center sizing")
        while lower + 1 < upper:
            midpoint = (lower + upper) // 2
            if full_pool_peak(midpoint) >= target_peak_kw:
                upper = midpoint
            else:
                lower = midpoint
        return self._power_model_for_node_count(upper)


def load_hourly_environment_config(
    config: str | Path | Mapping[str, Any],
    *,
    action_mode_override: ActionMode | None = None,
) -> HourlyEnvironmentConfig:
    """Load one V0 hourly environment YAML or an already-parsed mapping."""

    if isinstance(config, str | Path):
        with Path(config).open(encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    else:
        document = config
    root = _mapping(document, "hourly environment config")
    env = _mapping(root.get("env"), "env")
    community = _mapping(root.get("community"), "community")
    scenario = _mapping(root.get("scenario", {}), "scenario")
    virtual_dc = _mapping(root.get("virtual_datacenter"), "virtual_datacenter")
    workload = _mapping(root.get("workload"), "workload")
    hardware = _mapping(root.get("hardware"), "hardware")
    dr = _mapping(root.get("dr"), "dr")
    reward = _mapping(root.get("reward"), "reward")
    configured_mode = str(env.get("action_mode", "continuous"))
    mode = action_mode_override or configured_mode
    if mode not in {"continuous", "discrete"}:
        raise ValueError("env.action_mode must be 'continuous' or 'discrete'")
    action_mode = cast(ActionMode, mode)
    raw_node_count = virtual_dc.get("node_count", "auto")
    if raw_node_count != "auto":
        raw_node_count = _positive_int(raw_node_count, "virtual_datacenter.node_count")
    require_calibration_artifact = hardware.get("require_calibration_artifact", False)
    if not isinstance(require_calibration_artifact, bool):
        raise ValueError("hardware.require_calibration_artifact must be boolean")
    raw_calibration_artifact = hardware.get("calibration_artifact")
    calibration_power_case = str(hardware.get("calibration_power_case", "nominal")).strip()
    if calibration_power_case not in {"lower_ci", "nominal", "upper_ci"}:
        raise ValueError(
            "hardware.calibration_power_case must be 'lower_ci', 'nominal', or 'upper_ci'"
        )
    if raw_calibration_artifact is None:
        calibration_artifact = None
        if require_calibration_artifact:
            raise ValueError("formal hardware configuration requires calibration_artifact")
    elif isinstance(raw_calibration_artifact, str) and raw_calibration_artifact.strip():
        calibration_artifact = load_hardware_calibration_artifact(raw_calibration_artifact)
    else:
        raise ValueError("hardware.calibration_artifact must be a non-empty path when supplied")
    if calibration_artifact is None and calibration_power_case != "nominal":
        raise ValueError("hardware.calibration_power_case requires calibration_artifact")
    power_by_class: Mapping[str, object]
    if calibration_artifact is not None:
        if calibration_power_case == "nominal":
            power_by_class = calibration_artifact.active_power_by_class
            idle_power_w_per_gpu = calibration_artifact.idle_power_w_per_gpu
            node_fixed_overhead_w = calibration_artifact.node_fixed_overhead_w
        else:
            interval_index = 0 if calibration_power_case == "lower_ci" else 1
            power_by_class = {
                name: interval[interval_index]
                for name, interval in calibration_artifact.active_power_intervals_by_class.items()
            }
            idle_power_w_per_gpu = calibration_artifact.idle_power_confidence_interval_w[
                interval_index
            ]
            node_fixed_overhead_w = (
                calibration_artifact.node_fixed_overhead_confidence_interval_w[interval_index]
            )
    else:
        power_by_class = _mapping(
            hardware.get(
                "active_power_w_per_gpu_by_class",
                {
                    "training": 450.0,
                    "offline_inference": 350.0,
                    "online_inference": 400.0,
                },
            ),
            "hardware.active_power_w_per_gpu_by_class",
        )
        idle_power_w_per_gpu = _positive_float(
            hardware.get("fallback_idle_power_w_per_gpu", 80.0),
            "hardware.fallback_idle_power_w_per_gpu",
        )
        node_fixed_overhead_w = _positive_float(
            hardware.get("fallback_node_overhead_w", 300.0),
            "hardware.fallback_node_overhead_w",
        )
    max_deadline_hours = _positive_int(
        workload.get("max_deadline_hours", 48), "workload.max_deadline_hours"
    )
    configured_source = str(workload.get("source", "synthetic")).strip().lower()
    source_aliases = {
        "synthetic": "synthetic",
        "alibaba2026_lite": "alibaba2026_lite",
        "alibaba2026_summary": "alibaba2026_lite",
    }
    workload_source = source_aliases.get(configured_source)
    if workload_source is None:
        raise ValueError("workload.source must be 'synthetic' or 'alibaba2026_lite'")
    raw_summary_path = workload.get("summary_path")
    raw_arrivals_path = workload.get("arrivals_path")
    if workload_source == "alibaba2026_lite":
        if raw_summary_path is None:
            summary_path = None
        elif isinstance(raw_summary_path, str) and raw_summary_path.strip():
            summary_path = Path(raw_summary_path)
        else:
            raise ValueError("workload.summary_path must be a non-empty path when supplied")
        if raw_arrivals_path is None:
            arrivals_path = None
        elif isinstance(raw_arrivals_path, str) and raw_arrivals_path.strip():
            arrivals_path = Path(raw_arrivals_path)
        else:
            raise ValueError("workload.arrivals_path must be a non-empty path when supplied")
        if summary_path is None and arrivals_path is None:
            raise ValueError(
                "Alibaba Lite requires workload.summary_path or workload.arrivals_path"
            )
    else:
        summary_path = None
        arrivals_path = None
    arrival_process = str(workload.get("arrival_process", "nhpp")).strip().lower()
    if arrival_process not in {"nhpp", "block"}:
        raise ValueError("workload.arrival_process must be 'nhpp' or 'block'")
    configured_community_source = str(community.get("source", "synthetic")).strip()
    community_source_aliases = {
        "synthetic": "synthetic",
        "nrel_eulp": "nrel_eulp",
        "eulp": "nrel_eulp",
        "parquet": "nrel_eulp",
    }
    community_source = community_source_aliases.get(configured_community_source.lower())
    raw_community_path = community.get("path")
    if community_source is None and configured_community_source.lower().endswith(".parquet"):
        community_source = "nrel_eulp"
        raw_community_path = configured_community_source
    if community_source is None:
        raise ValueError("community.source must be 'synthetic' or 'nrel_eulp'")
    if community_source == "nrel_eulp":
        if not isinstance(raw_community_path, str) or not raw_community_path.strip():
            raise ValueError("NREL EULP community source requires community.path")
        community_path = Path(raw_community_path)
    else:
        community_path = None
    raw_profile_id = community.get("profile_id")
    if raw_profile_id is not None and (
        not isinstance(raw_profile_id, str) or not raw_profile_id.strip()
    ):
        raise ValueError("community.profile_id must be a non-empty string when supplied")
    raw_episode_start = community.get("episode_start")
    if raw_episode_start is not None and (
        not isinstance(raw_episode_start, str) or not raw_episode_start.strip()
    ):
        raise ValueError("community.episode_start must be a timestamp string when supplied")
    raw_frozen_scenario_path = scenario.get("frozen_path")
    if raw_frozen_scenario_path is None:
        frozen_scenario_path = None
    elif isinstance(raw_frozen_scenario_path, str) and raw_frozen_scenario_path.strip():
        frozen_scenario_path = Path(raw_frozen_scenario_path)
    else:
        raise ValueError("scenario.frozen_path must be a non-empty path when supplied")
    frozen_event_ids = (
        _non_negative_int_list(scenario["frozen_event_ids"], "scenario.frozen_event_ids")
        if scenario.get("frozen_event_ids") is not None
        else None
    )
    if frozen_event_ids is not None and frozen_scenario_path is None:
        raise ValueError("scenario.frozen_event_ids requires scenario.frozen_path")

    # ``target_peak_kw`` and ``target_dc_peak_share_of_community`` were the
    # original V0 schema.  Keep them as strict aliases so external smoke
    # configurations remain usable, but reject ambiguity when both names are
    # supplied with different values.
    if "background_peak_kw" in community and "target_peak_kw" in community:
        explicit_background_peak_kw = _positive_float(
            community["background_peak_kw"], "community.background_peak_kw"
        )
        legacy_background_peak_kw = _positive_float(
            community["target_peak_kw"], "community.target_peak_kw"
        )
        if not math.isclose(
            explicit_background_peak_kw,
            legacy_background_peak_kw,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "community.background_peak_kw and community.target_peak_kw disagree"
            )
    background_community_peak_kw = _positive_float(
        community.get("background_peak_kw", community.get("target_peak_kw", 1_000.0)),
        "community.background_peak_kw",
    )
    pcc_capacity_kw = _positive_float(
        community.get("pcc_capacity_kw", background_community_peak_kw),
        "community.pcc_capacity_kw",
    )
    if (
        "target_dc_peak_share_of_pcc" in virtual_dc
        and "target_dc_peak_share_of_community" in virtual_dc
    ):
        explicit_dc_share = _fraction(
            virtual_dc["target_dc_peak_share_of_pcc"],
            "virtual_datacenter.target_dc_peak_share_of_pcc",
            allow_zero=False,
        )
        legacy_dc_share = _fraction(
            virtual_dc["target_dc_peak_share_of_community"],
            "virtual_datacenter.target_dc_peak_share_of_community",
            allow_zero=False,
        )
        if not math.isclose(explicit_dc_share, legacy_dc_share, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                "virtual_datacenter.target_dc_peak_share_of_pcc and "
                "virtual_datacenter.target_dc_peak_share_of_community disagree"
            )
    target_dc_peak_share_of_pcc = _fraction(
        virtual_dc.get(
            "target_dc_peak_share_of_pcc",
            virtual_dc.get("target_dc_peak_share_of_community", 0.20),
        ),
        "virtual_datacenter.target_dc_peak_share_of_pcc",
        allow_zero=False,
    )
    configured_dr_source = str(dr.get("source", "configured")).strip().lower()
    if configured_dr_source not in {"configured", "manifest"}:
        raise ValueError("dr.source must be 'configured' or 'manifest'")
    raw_dr_manifest_path = dr.get("events_path")
    if configured_dr_source == "manifest":
        if community_source != "nrel_eulp":
            raise ValueError("absolute-time DR manifests require an nrel_eulp community source")
        if not isinstance(raw_dr_manifest_path, str) or not raw_dr_manifest_path.strip():
            raise ValueError("DR manifest source requires dr.events_path")
        dr_manifest_path = Path(raw_dr_manifest_path)
    else:
        dr_manifest_path = None
    workload_mix = WorkloadMix.from_mapping(workload.get("workload_mix", {}))
    if calibration_artifact is not None:
        flexible_classes = {
            name
            for name, fraction in workload_mix.flexible_fractions.items()
            if fraction > 0.0
        }
        missing_classes = sorted(flexible_classes - set(power_by_class))
        if missing_classes:
            raise ValueError(
                "hardware calibration artifact has no active-power estimate for flexible "
                f"workload classes: {missing_classes}"
            )
    return HourlyEnvironmentConfig(
        seed=int(root.get("seed", 2026)),
        action_mode=action_mode,
        timestep_hours=_positive_float(env.get("timestep_hours", 1.0), "env.timestep_hours"),
        episode_days=_positive_int(env.get("episode_days", 7), "env.episode_days"),
        clearance_tail_hours=_positive_int(
            env.get("clearance_tail_hours", 24), "env.clearance_tail_hours"
        ),
        forecast_horizon_hours=_positive_int(
            env.get("forecast_horizon_hours", 6), "env.forecast_horizon_hours"
        ),
        episode_seed_range=_non_negative_int_range(
            env.get("episode_seed_range"), "env.episode_seed_range"
        ),
        max_deadline_hours=max_deadline_hours,
        deadline_bucket_labels_h=_deadline_bucket_labels(
            workload.get("deadline_buckets", list(DEFAULT_BUCKET_LABELS_H)),
            max_deadline_hours,
        ),
        community_source=cast(Literal["synthetic", "nrel_eulp"], community_source),
        community_path=community_path,
        community_profile_id=(raw_profile_id.strip() if isinstance(raw_profile_id, str) else None),
        community_episode_start=(
            raw_episode_start.strip() if isinstance(raw_episode_start, str) else None
        ),
        frozen_scenario_path=frozen_scenario_path,
        frozen_event_ids=frozen_event_ids,
        background_community_peak_kw=background_community_peak_kw,
        pcc_capacity_kw=pcc_capacity_kw,
        pv_enabled=bool(community.get("pv_enabled", False)),
        gpus_per_node=_positive_int(
            virtual_dc.get("gpus_per_node", 4), "virtual_datacenter.gpus_per_node"
        ),
        node_count=raw_node_count,
        target_dc_peak_share_of_pcc=target_dc_peak_share_of_pcc,
        flexible_gpu_fraction=_fraction(
            virtual_dc.get("flexible_gpu_fraction", 0.50),
            "virtual_datacenter.flexible_gpu_fraction",
            allow_zero=False,
        ),
        target_total_utilization=_fraction(
            workload.get(
                "target_total_utilization",
                virtual_dc.get(
                    "target_total_utilization",
                    virtual_dc.get("target_flexible_utilization", 0.65),
                ),
            ),
            "workload.target_total_utilization",
            allow_zero=False,
        ),
        workload_mix=workload_mix,
        workload_source=cast(Literal["synthetic", "alibaba2026_lite"], workload_source),
        alibaba_summary_path=summary_path,
        alibaba_arrivals_path=arrivals_path,
        alibaba_arrival_process=cast(Literal["nhpp", "block"], arrival_process),
        flexible_priorities=_string_list(
            workload.get("flexible_priorities", ["LP"]), "workload.flexible_priorities"
        ),
        deadline_policy=AlibabaDeadlinePolicy.from_mapping(workload.get("deadline_policy")),
        idle_power_w_per_gpu=idle_power_w_per_gpu,
        active_power_w_by_class={
            name: _positive_float(value, f"active power for {name}")
            for name, value in power_by_class.items()
        },
        node_fixed_overhead_w=node_fixed_overhead_w,
        calibration_artifact=calibration_artifact,
        calibration_power_case=cast(
            Literal["lower_ci", "nominal", "upper_ci"], calibration_power_case
        ),
        pue=_positive_float(virtual_dc.get("pue", 1.20), "virtual_datacenter.pue"),
        dr_source=cast(Literal["configured", "manifest"], configured_dr_source),
        dr_manifest_path=dr_manifest_path,
        event_start_hours=_int_list(
            dr.get("event_start_hours", [17, 65, 113]), "dr.event_start_hours"
        ),
        event_duration_hours=_positive_int(
            dr.get("event_duration_hours", 3), "dr.event_duration_hours"
        ),
        event_notice_hours=_non_negative_int(
            dr.get("event_notice_hours", dr.get("notice_hours", 0)),
            "dr.event_notice_hours",
        ),
        event_reduction_fraction=_fraction(
            dr.get("event_reduction_fraction", dr.get("reduction_fraction", 0.20)),
            "dr.event_reduction_fraction",
            allow_zero=False,
        ),
        event_reduction_kw=(
            _non_negative_float(dr["event_reduction_kw"], "dr.event_reduction_kw")
            if dr.get("event_reduction_kw") is not None
            else None
        ),
        recovery_window_hours=_positive_int(
            dr.get("recovery_window_hours", 12), "dr.recovery_window_hours"
        ),
        recovery_backlog_tolerance_fraction=_fraction(
            dr.get("recovery_backlog_tolerance_fraction", 0.02),
            "dr.recovery_backlog_tolerance_fraction",
        ),
        event_start_jitter_hours=_non_negative_int(
            dr.get("event_start_jitter_hours", 0), "dr.event_start_jitter_hours"
        ),
        event_duration_choices=(
            _int_list(dr["event_duration_choices"], "dr.event_duration_choices")
            if dr.get("event_duration_choices") is not None
            else None
        ),
        event_notice_choices=(
            _non_negative_int_list(dr["event_notice_choices"], "dr.event_notice_choices")
            if dr.get("event_notice_choices") is not None
            else None
        ),
        event_reduction_fraction_range=_fraction_range(
            dr.get("event_reduction_fraction_range"), "dr.event_reduction_fraction_range"
        ),
        reward=_parse_reward_specification(reward),
    )


def _parse_reward_specification(reward: Mapping[str, Any]) -> RewardSpecification:
    version = str(reward.get("version", "")).strip()
    if version != "firm_threshold_v2":
        raise ValueError("reward.version must be 'firm_threshold_v2'")
    return RewardSpecification(
        version="firm_threshold_v2",
        min_delivery_ratio=_fraction(
            reward.get("min_delivery_ratio", 0.95),
            "reward.min_delivery_ratio",
        ),
        max_deadline_miss_rate=_fraction(
            reward.get("max_deadline_miss_rate", 0.01),
            "reward.max_deadline_miss_rate",
            allow_zero=False,
        ),
        max_rebound_ratio=_positive_float(
            reward.get("max_rebound_ratio", 0.25),
            "reward.max_rebound_ratio",
        ),
        min_window_peak_relief_fraction=_fraction(
            reward.get("min_window_peak_relief_fraction", 0.50),
            "reward.min_window_peak_relief_fraction",
            allow_zero=False,
        ),
        max_terminal_backlog_fraction=_fraction(
            reward.get("max_terminal_backlog_fraction", 0.02),
            "reward.max_terminal_backlog_fraction",
            allow_zero=False,
        ),
        delivery_violation_weight=_non_negative_float(
            reward.get("delivery_violation_weight", 1.0),
            "reward.delivery_violation_weight",
        ),
        feasibility_violation_weight=_non_negative_float(
            reward.get("feasibility_violation_weight", 1.0),
            "reward.feasibility_violation_weight",
        ),
        deadline_violation_weight=_non_negative_float(
            reward.get("deadline_violation_weight", 1.0),
            "reward.deadline_violation_weight",
        ),
        rebound_violation_weight=_non_negative_float(
            reward.get("rebound_violation_weight", 1.0),
            "reward.rebound_violation_weight",
        ),
        window_violation_weight=_non_negative_float(
            reward.get("window_violation_weight", 1.0),
            "reward.window_violation_weight",
        ),
        terminal_violation_weight=_non_negative_float(
            reward.get("terminal_violation_weight", 1.0),
            "reward.terminal_violation_weight",
        ),
        excess_backlog_weight=_non_negative_float(
            reward.get("excess_backlog_weight", 0.05),
            "reward.excess_backlog_weight",
        ),
        switching_weight=_non_negative_float(
            reward.get("switching_weight", 0.001),
            "reward.switching_weight",
        ),
    )
