"""Hourly Gymnasium environments for flexible-AI community peak shaving."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

import gymnasium as gym
import numpy as np
import pandas as pd

from aidrbench.data.alibaba2026 import make_alibaba_lite_hourly_arrivals
from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    load_frozen_hourly_scenario,
    power_model_fingerprint,
)
from aidrbench.data.hourly import (
    arrivals_for_hour,
    load_hourly_arrivals,
    load_hourly_community_profile,
    load_hourly_dr_manifest,
    make_synthetic_hourly_arrivals,
    make_synthetic_hourly_community,
    select_dr_aligned_episode_start,
    select_hourly_community_window,
)
from aidrbench.envs.hourly_config import load_hourly_environment_config
from aidrbench.models.power import HourlyDataCenterPowerModel
from aidrbench.workloads.deadline_buckets import HourlyDeadlineBuckets

DISCRETE_ACTION_FRACTIONS = np.asarray((0.0, 0.25, 0.50, 0.75, 1.0), dtype=np.float32)
OBSERVATION_VERSION = "firm_v5"
_MAX_NORMALIZED_LOAD = 4.0


@dataclass(frozen=True, slots=True)
class HourlyDREvent:
    """One demand-response request and its post-event recovery window."""

    event_id: int
    start_hour: int
    stop_hour: int
    recovery_stop_hour: int
    requested_reduction_kw: float
    source_event_id: str
    notice_hours: float


@dataclass(frozen=True, slots=True)
class HourlyPlanningSnapshot:
    """Perfect-future episode data exposed only to offline planning oracles."""

    episode_seed: int
    total_hours: int
    main_hours: int
    capacity_gpu_h: float
    fixed_dc_power_kw: float
    reference_mix_operating_peak_kw: float
    worst_class_peak_kw: float
    dynamic_kw_per_gpu_h: float
    workload_classes: tuple[str, ...]
    dynamic_kw_per_gpu_h_by_class: tuple[tuple[str, float], ...]
    pcc_capacity_kw: float
    community_power_kw: tuple[float, ...]
    released_gpu_h: tuple[float, ...]
    due_gpu_h: tuple[float, ...]
    work_groups: tuple[tuple[int, int, str, float], ...]
    total_arrival_gpu_h: float
    baseline_execution_gpu_h: tuple[float, ...]
    baseline_execution_gpu_h_by_class: tuple[tuple[str, tuple[float, ...]], ...]
    baseline_pcc_power_kw: tuple[float, ...]
    baseline_deadline_miss_gpu_h: float
    baseline_terminal_backlog_gpu_h: float
    events: tuple[HourlyDREvent, ...]


class HourlyCommunityAIDemandResponseEnv(gym.Env[np.ndarray, np.ndarray | int]):
    """V0 hourly fluid-workload environment with continuous or discrete action."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        config: str | Path | Mapping[str, Any],
        *,
        action_mode: Literal["continuous", "discrete"] | None = None,
    ) -> None:
        super().__init__()
        self.config = load_hourly_environment_config(config, action_mode_override=action_mode)
        self.power_model: HourlyDataCenterPowerModel = self.config.make_power_model()
        self._frozen_scenario: FrozenHourlyScenario | None = None
        if self.config.frozen_scenario_path is not None:
            self._frozen_scenario = load_frozen_hourly_scenario(
                self.config.frozen_scenario_path
            )
            self._frozen_scenario.assert_compatible(
                total_hours=self.config.total_hours,
                forecast_horizon_hours=self.config.forecast_horizon_hours,
                pcc_capacity_kw=self.config.pcc_capacity_kw,
                power_model_sha256=power_model_fingerprint(self.power_model),
            )
        self._community_profile = None
        if self._frozen_scenario is None and self.config.community_source == "nrel_eulp":
            if self.config.community_path is None:
                raise RuntimeError("NREL EULP community source has no path")
            self._community_profile = load_hourly_community_profile(
                self.config.community_path,
                profile_id=self.config.community_profile_id,
                target_peak_kw=self.config.background_community_peak_kw,
                pv_enabled=self.config.pv_enabled,
            )
        self._dr_manifest = None
        if self._frozen_scenario is None and self.config.dr_source == "manifest":
            if self.config.dr_manifest_path is None or self._community_profile is None:
                raise RuntimeError("DR manifest source is missing its event or community data")
            selected_profile_id = str(self._community_profile["profile_id"].iloc[0])
            self._dr_manifest = load_hourly_dr_manifest(
                self.config.dr_manifest_path,
                profile_id=selected_profile_id,
            )
        self._capacity_gpu_h = self.power_model.flexible_capacity_gpu_h * self.config.timestep_hours
        self._bucket_count = len(self.config.deadline_bucket_labels_h)
        self._fixed_dc_power_kw = self.power_model.predict(0.0).dc_power_kw
        self._full_dc_power_kw = self.power_model.predict(self._capacity_gpu_h).dc_power_kw
        self._flexible_power_range_kw = max(
            self._full_dc_power_kw - self._fixed_dc_power_kw,
            1e-9,
        )
        configured_durations = self.config.event_duration_choices or (
            self.config.event_duration_hours,
        )
        configured_notices = self.config.event_notice_choices or (self.config.event_notice_hours,)
        self._event_duration_scale_h = float(max(configured_durations))
        self._event_notice_scale_h = float(max(max(configured_notices), 1))
        if self._dr_manifest is not None and not self._dr_manifest.empty:
            manifest_durations_h = (
                self._dr_manifest["end_time"] - self._dr_manifest["start_time"]
            ).dt.total_seconds() / 3_600.0
            self._event_duration_scale_h = max(
                self._event_duration_scale_h,
                float(manifest_durations_h.max()),
            )
            self._event_notice_scale_h = max(
                self._event_notice_scale_h,
                float(self._dr_manifest["notice_minutes"].max()) / 60.0,
            )
        if self.config.action_mode == "continuous":
            self.action_space: gym.spaces.Space[Any] = gym.spaces.Box(
                low=np.asarray((0.0,), dtype=np.float32),
                high=np.asarray((1.0,), dtype=np.float32),
                dtype=np.float32,
            )
        else:
            self.action_space = gym.spaces.Discrete(len(DISCRETE_ACTION_FRACTIONS))
        names, lows, highs = self._observation_spec()
        self._observation_feature_names = names
        self.observation_space = gym.spaces.Box(
            low=np.asarray(lows, dtype=np.float32),
            high=np.asarray(highs, dtype=np.float32),
            dtype=np.float32,
        )
        self._community = make_synthetic_hourly_community(
            hours=1, peak_kw=self.config.community_peak_kw, seed=self.config.seed
        )
        self._arrivals = make_synthetic_hourly_arrivals(
            hours=1,
            total_gpu_count=self.power_model.data_center.total_gpu_count,
            target_total_utilization=self.config.target_total_utilization,
            workload_mix=self.config.workload_mix,
            seed=self.config.seed,
        )
        self._pcc_limit_kw = np.zeros(1, dtype="float64")
        self._event_active = np.zeros(1, dtype=bool)
        self._event_remaining_h = np.zeros(1, dtype="float64")
        self._event_notice_remaining_h = np.zeros(1, dtype="float64")
        self._requested_reduction_kw = np.zeros(1, dtype="float64")
        self._rebound_reference_kw = np.zeros(1, dtype="float64")
        self._event_request_reference_kw = np.zeros(1, dtype="float64")
        self._recovery_remaining_h = np.zeros(1, dtype="float64")
        self._post_event = np.zeros(1, dtype=bool)
        self._event_ids = np.full(1, -1, dtype="int64")
        self._event_source_ids = np.full(1, "", dtype=object)
        self._event_window_active = np.zeros(1, dtype=bool)
        self._events_last_24h = np.zeros(1, dtype="int64")
        self._hours_since_previous_event = np.full(1, -1.0, dtype="float64")
        self._events: tuple[HourlyDREvent, ...] = ()
        self._running_baseline_peak_kw = np.zeros(0, dtype="float64")
        self._running_controlled_peak_kw = np.zeros(0, dtype="float64")
        self._running_rebound_peak_kw = np.zeros(0, dtype="float64")
        self._queue = HourlyDeadlineBuckets(
            max_deadline_hours=self.config.max_deadline_hours,
            bucket_labels_h=self.config.deadline_bucket_labels_h,
        )
        self._baseline_queue = HourlyDeadlineBuckets(
            max_deadline_hours=self.config.max_deadline_hours,
            bucket_labels_h=self.config.deadline_bucket_labels_h,
        )
        self._time_index = 0
        # An episode starts from normal, unconstrained operation.  This avoids
        # charging the controller a fictitious 0 -> 100% switching cost on the
        # first hour.
        self._previous_action_fraction = 1.0
        self._previous_pcc_power_kw = 0.0
        self._current_arrival_gpu_h = 0.0
        self._episode_seed = self.config.seed
        self._random_stream_seeds: dict[str, int] = {}

    @property
    def event_manifest(self) -> tuple[HourlyDREvent, ...]:
        """Immutable event metadata for episode-level firm-flexibility KPIs."""

        return self._events

    @property
    def random_stream_seeds(self) -> dict[str, int]:
        """Independent deterministic seeds for community, workload and events."""

        return dict(self._random_stream_seeds)

    def _scenario_provenance(self) -> dict[str, str]:
        if self._frozen_scenario is None:
            return {
                "scenario_provenance": "generated_in_memory",
                "frozen_scenario_id": "",
                "frozen_scenario_hash": "",
            }
        return {
            "scenario_provenance": "frozen_artifact",
            "frozen_scenario_id": self._frozen_scenario.scenario_id,
            "frozen_scenario_hash": self._frozen_scenario.scenario_hash,
        }

    def _sizing_metadata(self) -> dict[str, float]:
        """Stable scenario bases and the exact realised virtual-DC peak."""

        return {
            "background_community_peak_kw": self.config.background_community_peak_kw,
            "pcc_capacity_kw": self.config.pcc_capacity_kw,
            "target_dc_peak_kw": self.config.target_dc_peak_kw,
            "reference_mix_operating_peak_kw": (
                self.power_model.reference_mix_operating_peak_kw
            ),
            "worst_class_peak_kw": self.power_model.worst_class_peak_kw,
            # Compatibility alias for historical controller outputs. New NC
            # analysis must use one of the two explicit peak definitions.
            "actual_dc_peak_kw": self._full_dc_power_kw,
            "actual_dc_peak_fraction_of_pcc": (
                self._full_dc_power_kw / self.config.pcc_capacity_kw
            ),
            "dc_peak_sizing_error_kw": (
                self._full_dc_power_kw - self.config.target_dc_peak_kw
            ),
        }

    def _hardware_provenance(self) -> dict[str, str]:
        """Return the calibration identity recorded with every rollout row."""

        artifact = self.config.calibration_artifact
        if artifact is None:
            return {
                "calibration_artifact_id": "",
                "calibration_artifact_sha256": "",
                "calibration_power_case": "fallback_parameters",
                "hardware_evidence_class": "fallback_parameters",
            }
        return {
            "calibration_artifact_id": artifact.artifact_id,
            "calibration_artifact_sha256": artifact.artifact_sha256,
            "calibration_power_case": self.config.calibration_power_case,
            "hardware_evidence_class": artifact.evidence_class.value,
        }

    def full_horizon_planning_snapshot(self) -> HourlyPlanningSnapshot:
        """Return immutable perfect-future inputs for an explicitly labelled oracle.

        Online controllers must not call this method. It intentionally reveals
        all arrivals, deadlines, community loads, and DR events in the episode.
        """

        total_hours = self.config.total_hours
        released = np.zeros(total_hours, dtype="float64")
        due = np.zeros(total_hours, dtype="float64")
        grouped_work: dict[tuple[int, int, str], float] = {}
        workload_classes = tuple(
            sorted(str(value) for value in self._arrivals["job_class"].unique())
        )
        for record in self._arrivals.to_dict(orient="records"):
            release = int(record["timestamp_index"])
            if not 0 <= release < total_hours:
                continue
            work = float(record["arrival_gpu_h"])
            job_class = str(record["job_class"])
            released[release] += work
            deadline = release + math.ceil(float(record["slack_hours"])) - 1
            key = (release, deadline, job_class)
            grouped_work[key] = grouped_work.get(key, 0.0) + work
            if deadline < total_hours:
                due[max(deadline, 0)] += work

        baseline_queue = HourlyDeadlineBuckets(
            max_deadline_hours=self.config.max_deadline_hours,
            bucket_labels_h=self.config.deadline_bucket_labels_h,
        )
        baseline_execution = np.zeros(total_hours, dtype="float64")
        baseline_execution_by_class = {
            job_class: np.zeros(total_hours, dtype="float64")
            for job_class in workload_classes
        }
        baseline_pcc = np.zeros(total_hours, dtype="float64")
        community = self._community["net_community_load_kw"].iloc[:total_hours].to_numpy(
            dtype="float64"
        )
        for index in range(total_hours):
            step = baseline_queue.advance(
                arrivals_for_hour(self._arrivals, index),
                requested_gpu_h=self._capacity_gpu_h,
                capacity_gpu_h=self._capacity_gpu_h,
            )
            baseline_execution[index] = step.executed_gpu_h
            for job_class, executed_gpu_h in step.executed_gpu_h_by_class:
                baseline_execution_by_class.setdefault(
                    job_class, np.zeros(total_hours, dtype="float64")
                )[index] = executed_gpu_h
            baseline_pcc[index] = community[index] + self.power_model.predict_by_class(
                dict(step.executed_gpu_h_by_class),
                timestep_hours=self.config.timestep_hours,
            ).dc_power_kw

        return HourlyPlanningSnapshot(
            episode_seed=self._episode_seed,
            total_hours=total_hours,
            main_hours=self.config.main_hours,
            capacity_gpu_h=self._capacity_gpu_h,
            fixed_dc_power_kw=self._fixed_dc_power_kw,
            reference_mix_operating_peak_kw=(
                self.power_model.reference_mix_operating_peak_kw
            ),
            worst_class_peak_kw=self.power_model.worst_class_peak_kw,
            dynamic_kw_per_gpu_h=self._flexible_power_range_kw / self._capacity_gpu_h,
            workload_classes=workload_classes,
            dynamic_kw_per_gpu_h_by_class=tuple(
                (
                    job_class,
                    self.power_model.flexible_dynamic_power_kw_per_gpu_h(
                        job_class,
                        timestep_hours=self.config.timestep_hours,
                    ),
                )
                for job_class in workload_classes
            ),
            pcc_capacity_kw=self.config.pcc_capacity_kw,
            community_power_kw=tuple(float(value) for value in community),
            released_gpu_h=tuple(float(value) for value in released),
            due_gpu_h=tuple(float(value) for value in due),
            work_groups=tuple(
                (release, deadline, job_class, work)
                for (release, deadline, job_class), work in sorted(grouped_work.items())
            ),
            total_arrival_gpu_h=float(released.sum()),
            baseline_execution_gpu_h=tuple(float(value) for value in baseline_execution),
            baseline_execution_gpu_h_by_class=tuple(
                (
                    job_class,
                    tuple(float(value) for value in baseline_execution_by_class[job_class]),
                )
                for job_class in workload_classes
            ),
            baseline_pcc_power_kw=tuple(float(value) for value in baseline_pcc),
            baseline_deadline_miss_gpu_h=baseline_queue.cumulative_missed_gpu_h,
            baseline_terminal_backlog_gpu_h=baseline_queue.backlog_gpu_h,
            events=self._events,
        )

    @property
    def observation_version(self) -> str:
        """Semantic version for saved-policy compatibility checks."""

        return OBSERVATION_VERSION

    @property
    def observation_feature_names(self) -> tuple[str, ...]:
        """Stable, auditable ordering of the normalized policy inputs."""

        return self._observation_feature_names

    def _observation_spec(self) -> tuple[tuple[str, ...], tuple[float, ...], tuple[float, ...]]:
        entries: list[tuple[str, float, float]] = [
            ("hour_sin", -1.0, 1.0),
            ("hour_cos", -1.0, 1.0),
            ("weekday_sin", -1.0, 1.0),
            ("weekday_cos", -1.0, 1.0),
            ("community_net_fraction", 0.0, 2.0),
            ("pv_fraction", 0.0, 2.0),
            ("pcc_limit_fraction", 0.0, 2.0),
            ("fixed_dc_fraction", 0.0, 2.0),
            ("available_flexible_power_fraction", -1.0, 1.0),
            ("event_request_fraction", 0.0, 2.0),
            ("backlog_horizon_fraction", 0.0, _MAX_NORMALIZED_LOAD),
            ("baseline_backlog_horizon_fraction", 0.0, _MAX_NORMALIZED_LOAD),
            ("excess_backlog_horizon_fraction", 0.0, _MAX_NORMALIZED_LOAD),
            ("cumulative_arrival_utilization", 0.0, _MAX_NORMALIZED_LOAD),
            ("deadline_miss_rate_so_far", 0.0, 1.0),
            ("baseline_deadline_miss_rate_so_far", 0.0, 1.0),
            ("terminal_excess_fraction_so_far", 0.0, _MAX_NORMALIZED_LOAD),
            ("mean_slack_fraction", 0.0, 1.0),
            ("p10_slack_fraction", 0.0, 1.0),
        ]
        entries.extend(
            (
                f"deadline_feasibility_{label}h",
                0.0,
                _MAX_NORMALIZED_LOAD,
            )
            for label in self.config.deadline_bucket_labels_h
        )
        entries.extend(
            (
                f"excess_deadline_feasibility_{label}h",
                0.0,
                _MAX_NORMALIZED_LOAD,
            )
            for label in self.config.deadline_bucket_labels_h
        )
        entries.extend(
            [
                ("event_active", 0.0, 1.0),
                ("recovery_active", 0.0, 1.0),
                ("event_window_active", 0.0, 1.0),
                ("notice_active", 0.0, 1.0),
                ("event_remaining_fraction", 0.0, 1.0),
                ("notice_remaining_fraction", 0.0, 1.0),
                ("recovery_remaining_fraction", 0.0, 1.0),
                ("events_last_24h_squashed", 0.0, 1.0),
                ("has_previous_event", 0.0, 1.0),
                ("hours_since_previous_event_fraction", 0.0, 1.0),
                ("running_window_baseline_peak_fraction", 0.0, 2.0),
                ("running_window_pcc_peak_fraction", 0.0, 2.0),
                ("running_window_relief_fraction", -_MAX_NORMALIZED_LOAD, _MAX_NORMALIZED_LOAD),
                ("running_rebound_ratio", 0.0, _MAX_NORMALIZED_LOAD),
                ("previous_action_fraction", 0.0, 1.0),
                ("previous_pcc_fraction", 0.0, 2.0),
            ]
        )
        for step in range(1, self.config.forecast_horizon_hours + 1):
            entries.append((f"community_forecast_t+{step}_fraction", 0.0, 2.0))
        for step in range(1, self.config.forecast_horizon_hours + 1):
            entries.append((f"available_flexible_forecast_t+{step}_fraction", -1.0, 1.0))
        names, lows, highs = zip(*entries, strict=True)
        return tuple(names), tuple(lows), tuple(highs)

    def _build_episode(self, seed: int) -> None:
        total = self.config.total_hours + self.config.forecast_horizon_hours
        seed_sequences = np.random.SeedSequence(seed).spawn(3)
        community_seed, workload_seed, event_seed = (
            int(sequence.generate_state(1, dtype=np.uint64)[0])
            for sequence in seed_sequences
        )
        self._random_stream_seeds = {
            "community": community_seed,
            "workload": workload_seed,
            "events": event_seed,
        }
        if self._frozen_scenario is not None:
            self._community = self._frozen_scenario.community.copy()
            self._arrivals = self._frozen_scenario.arrivals.copy()
        else:
            if self._community_profile is None:
                self._community = make_synthetic_hourly_community(
                    hours=total,
                    peak_kw=self.config.background_community_peak_kw,
                    seed=community_seed,
                    pv_enabled=self.config.pv_enabled,
                )
            else:
                episode_start = self.config.community_episode_start
                if self._dr_manifest is not None:
                    episode_start = select_dr_aligned_episode_start(
                        self._community_profile,
                        self._dr_manifest,
                        total_hours=total,
                        main_hours=self.config.main_hours,
                        seed=community_seed,
                        episode_start=episode_start,
                    )
                self._community = select_hourly_community_window(
                    self._community_profile,
                    hours=total,
                    seed=community_seed,
                    episode_start=episode_start,
                )
            # The clearance tail drains work from the seven-day main horizon;
            # it must not introduce fresh workload, independent of source.
            if self.config.workload_source == "synthetic":
                self._arrivals = make_synthetic_hourly_arrivals(
                    hours=self.config.main_hours,
                    total_gpu_count=self.power_model.data_center.total_gpu_count,
                    target_total_utilization=self.config.target_total_utilization,
                    workload_mix=self.config.workload_mix,
                    seed=workload_seed,
                )
            else:
                if self.config.alibaba_arrivals_path is not None:
                    self._arrivals = load_hourly_arrivals(self.config.alibaba_arrivals_path)
                else:
                    if self.config.alibaba_summary_path is None:
                        raise RuntimeError("Alibaba Lite workload source has no summary path")
                    self._arrivals = make_alibaba_lite_hourly_arrivals(
                        self.config.alibaba_summary_path,
                        hours=self.config.main_hours,
                        total_gpu_count=self.power_model.data_center.total_gpu_count,
                        target_total_utilization=self.config.target_total_utilization,
                        workload_shares=self.config.workload_mix.shares,
                        flexible_fractions=self.config.workload_mix.flexible_fractions,
                        flexible_priorities=self.config.flexible_priorities,
                        deadline_policy=self.config.deadline_policy,
                        arrival_process=self.config.alibaba_arrival_process,
                        seed=workload_seed,
                    )
        net_community = self._community["net_community_load_kw"].to_numpy(dtype="float64")
        full_flexible = self.power_model.predict(self._capacity_gpu_h).dc_power_kw
        idle_flexible = self.power_model.predict(0.0).dc_power_kw
        dynamic_flexible_kw = full_flexible - idle_flexible
        scenario_rng = np.random.default_rng(event_seed)
        # The PCC or transformer constraint applies in every interval, not
        # only during a DR event.  Event limits may be tighter, but can never
        # relax the physical interconnection limit.
        limits = np.full(total, self.config.pcc_capacity_kw, dtype="float64")
        active = np.zeros(total, dtype=bool)
        remaining = np.zeros(total, dtype="float64")
        notice_remaining = np.zeros(total, dtype="float64")
        post_event = np.zeros(total, dtype=bool)
        event_ids = np.full(total, -1, dtype="int64")
        event_source_ids = np.full(total, "", dtype=object)
        event_window_active = np.zeros(total, dtype=bool)
        requested_reductions = np.zeros(total, dtype="float64")
        rebound_references = np.zeros(total, dtype="float64")
        request_references = np.zeros(total, dtype="float64")
        recovery_remaining = np.zeros(total, dtype="float64")
        events: list[HourlyDREvent] = []
        event_specs: list[tuple[str, int, int, float, float]] = []
        if self._frozen_scenario is not None:
            if (
                self.config.event_duration_choices is not None
                or self.config.event_notice_choices is not None
                or self.config.event_reduction_fraction_range is not None
                or self.config.event_start_jitter_hours != 0
            ):
                raise ValueError(
                    "frozen scenarios require fixed duration, notice, reduction, and event starts"
                )
            anchored_events = self._frozen_scenario.events
            if self.config.frozen_event_ids is not None:
                by_id = {int(event["event_id"]): event for event in anchored_events}
                missing_event_ids = set(self.config.frozen_event_ids) - set(by_id)
                if missing_event_ids:
                    raise ValueError(
                        "frozen scenario does not contain requested event IDs: "
                        f"{sorted(missing_event_ids)}"
                    )
                anchored_events = tuple(
                    by_id[event_id] for event_id in self.config.frozen_event_ids
                )
            event_specs.extend(
                (
                    str(event["source_event_id"]),
                    int(event["start_hour"]),
                    min(
                        int(event["start_hour"]) + self.config.event_duration_hours,
                        self.config.main_hours,
                    ),
                    (
                        self.config.event_reduction_kw
                        if self.config.event_reduction_kw is not None
                        else float(event["requested_reduction_kw"])
                    ),
                    (
                        float(self.config.frozen_event_notice_hours)
                        if self.config.frozen_event_notice_hours is not None
                        else float(event["notice_hours"])
                    ),
                )
                for event in anchored_events
                if int(event["start_hour"]) < self.config.main_hours
            )
        elif self._dr_manifest is None:
            event_duration_h = (
                int(scenario_rng.choice(self.config.event_duration_choices))
                if self.config.event_duration_choices is not None
                else self.config.event_duration_hours
            )
            event_reduction_fraction = (
                float(scenario_rng.uniform(*self.config.event_reduction_fraction_range))
                if self.config.event_reduction_fraction_range is not None
                else self.config.event_reduction_fraction
            )
            requested_reduction_kw = (
                self.config.event_reduction_kw
                if self.config.event_reduction_kw is not None
                else dynamic_flexible_kw * event_reduction_fraction
            )
            sampled_starts = tuple(
                int(
                    np.clip(
                        start
                        + scenario_rng.integers(
                            -self.config.event_start_jitter_hours,
                            self.config.event_start_jitter_hours + 1,
                        ),
                        0,
                        max(self.config.main_hours - event_duration_h, 0),
                    )
                )
                for start in self.config.event_start_hours
            )
            event_specs.extend(
                (
                    f"configured_{event_id}",
                    start,
                    min(start + event_duration_h, self.config.main_hours),
                    requested_reduction_kw,
                    float(
                        scenario_rng.choice(self.config.event_notice_choices)
                        if self.config.event_notice_choices is not None
                        else self.config.event_notice_hours
                    ),
                )
                for event_id, start in enumerate(sampled_starts)
                if start < self.config.main_hours
            )
        else:
            manifest_episode_start = pd.Timestamp(self._community["timestamp"].iloc[0])
            main_end = manifest_episode_start + timedelta(hours=self.config.main_hours)
            selected_events = self._dr_manifest.loc[
                (self._dr_manifest["start_time"] >= manifest_episode_start)
                & (self._dr_manifest["end_time"] <= main_end)
            ]
            for row in selected_events.to_dict(orient="records"):
                start = int(
                    (pd.Timestamp(row["start_time"]) - manifest_episode_start).total_seconds()
                    // 3_600
                )
                stop = int(
                    (pd.Timestamp(row["end_time"]) - manifest_episode_start).total_seconds()
                    // 3_600
                )
                if self.config.event_reduction_kw is not None:
                    requested_reduction_kw = self.config.event_reduction_kw
                elif row.get("requested_reduction_kw") is not None:
                    requested_reduction_kw = float(row["requested_reduction_kw"])
                else:
                    requested_reduction_kw = dynamic_flexible_kw * float(row["reduction_fraction"])
                event_specs.append(
                    (
                        str(row["event_id"]),
                        start,
                        stop,
                        requested_reduction_kw,
                        float(row["notice_minutes"]) / 60.0,
                    )
                )
        for event_id, (source_event_id, start, stop, requested_reduction_kw, notice_h) in enumerate(
            event_specs
        ):
            recovery_stop = min(stop + self.config.recovery_window_hours, self.config.total_hours)
            event_limits = (
                net_community[start:stop] + full_flexible - requested_reduction_kw
            )
            limits[start:stop] = np.minimum(limits[start:stop], event_limits)
            active[start:stop] = True
            remaining[start:stop] = np.arange(stop - start, 0, -1, dtype="float64")
            event_ids[start:stop] = event_id
            event_source_ids[start:stop] = source_event_id
            # The DR request remains explicit even if no-control happens to
            # have insufficient backlog to realize the nominal baseline.
            requested_reductions[start:stop] = requested_reduction_kw
            notice_start = max(0, start - math.ceil(notice_h))
            request_references[notice_start:recovery_stop] = np.maximum(
                request_references[notice_start:recovery_stop],
                requested_reduction_kw,
            )
            for notice_index in range(notice_start, start):
                hours_until_start = float(start - notice_index)
                current_notice = notice_remaining[notice_index]
                if current_notice == 0.0 or hours_until_start < current_notice:
                    notice_remaining[notice_index] = hours_until_start
            post_event[stop:recovery_stop] = True
            event_window_active[start:recovery_stop] = True
            rebound_references[stop:recovery_stop] = np.maximum(
                rebound_references[stop:recovery_stop], requested_reduction_kw
            )
            recovery_remaining[stop:recovery_stop] = np.maximum(
                recovery_remaining[stop:recovery_stop],
                np.arange(recovery_stop - stop, 0, -1, dtype="float64"),
            )
            events.append(
                HourlyDREvent(
                    event_id=event_id,
                    start_hour=start,
                    stop_hour=stop,
                    recovery_stop_hour=recovery_stop,
                    requested_reduction_kw=requested_reduction_kw,
                    source_event_id=source_event_id,
                    notice_hours=notice_h,
                )
            )
        self._pcc_limit_kw = limits
        self._event_active = active
        self._event_remaining_h = remaining
        self._event_notice_remaining_h = notice_remaining
        self._requested_reduction_kw = requested_reductions
        self._rebound_reference_kw = rebound_references
        self._event_request_reference_kw = request_references
        self._recovery_remaining_h = recovery_remaining
        self._post_event = post_event
        self._event_ids = event_ids
        self._event_source_ids = event_source_ids
        self._event_window_active = event_window_active
        self._events = tuple(events)
        self._running_baseline_peak_kw = np.zeros(len(events), dtype="float64")
        self._running_controlled_peak_kw = np.zeros(len(events), dtype="float64")
        self._running_rebound_peak_kw = np.zeros(len(events), dtype="float64")
        event_starts = np.asarray([event.start_hour for event in self._events], dtype="int64")
        events_last_24h = np.zeros(total, dtype="int64")
        hours_since = np.full(total, -1.0, dtype="float64")
        for index in range(total):
            previous = event_starts[event_starts <= index]
            if len(previous):
                hours_since[index] = float(index - previous[-1])
            started_in_previous_day = (event_starts <= index) & (event_starts > index - 24)
            events_last_24h[index] = int(started_in_previous_day.sum())
        self._events_last_24h = events_last_24h
        self._hours_since_previous_event = hours_since
        self._queue.reset()
        self._baseline_queue.reset()
        self._current_arrival_gpu_h = self._preload_arrivals(0)
        self._time_index = 0
        self._previous_action_fraction = 1.0
        self._previous_pcc_power_kw = 0.0

    def _preload_arrivals(self, index: int) -> float:
        """Make the current hour's released work visible before action selection."""

        arrivals = arrivals_for_hour(self._arrivals, index)
        controlled = self._queue.add(arrivals)
        baseline = self._baseline_queue.add(arrivals)
        if not math.isclose(controlled, baseline, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError("controlled and baseline queues received different arrivals")
        return controlled

    @staticmethod
    def _bounded(value: float, lower: float, upper: float) -> float:
        return float(np.clip(value, lower, upper))

    def _normalize_power(self, power_kw: float) -> float:
        ratio = power_kw / max(self.config.pcc_capacity_kw, 1.0)
        return self._bounded(ratio, 0.0, 2.0)

    @staticmethod
    def _huber_violation(value: float) -> float:
        """Transition from quadratic to linear at one normalized threshold."""

        if value <= 1.0:
            return 0.5 * value * value
        return value - 0.5

    def _normalize_flexible_power(self, power_kw: float) -> float:
        return self._bounded(power_kw / self._flexible_power_range_kw, 0.0, 2.0)

    def _available_flexible_fraction(self, *, community_kw: float, limit_kw: float) -> float:
        available_kw = limit_kw - community_kw - self._fixed_dc_power_kw
        return self._bounded(available_kw / self._flexible_power_range_kw, -1.0, 1.0)

    def _deadline_feasibility_ratios(self, queue: HourlyDeadlineBuckets) -> np.ndarray:
        """Cumulative due work divided by capacity available before each deadline."""

        remaining = np.asarray(queue.remaining_by_deadline_gpu_h, dtype="float64")
        ratios: list[float] = []
        for label in self.config.deadline_bucket_labels_h:
            # Bucket label 0 is work due by the end of the current interval;
            # label 1 includes the current and next intervals.  The terminal
            # label is capped at the queue's configured deadline horizon.
            horizon = min(label + 1, self.config.max_deadline_hours)
            due = float(remaining[:horizon].sum())
            ratios.append(due / max(self._capacity_gpu_h * horizon, 1e-9))
        return np.asarray(ratios, dtype="float64")

    def _window_observation_state(self, index: int) -> tuple[float, float, float, float]:
        active_ids = [
            event.event_id
            for event in self._events
            if event.start_hour <= index < event.recovery_stop_hour
        ]
        if not active_ids:
            return 0.0, 0.0, 0.0, 0.0
        event_states: list[tuple[float, float, float, float]] = []
        for event_id in active_ids:
            event = self._events[event_id]
            request = max(event.requested_reduction_kw, 1e-9)
            baseline_peak = float(self._running_baseline_peak_kw[event_id])
            controlled_peak = float(self._running_controlled_peak_kw[event_id])
            relief_fraction = (baseline_peak - controlled_peak) / request
            rebound_ratio = float(self._running_rebound_peak_kw[event_id]) / request
            event_states.append((baseline_peak, controlled_peak, relief_fraction, rebound_ratio))
        # The least relieved active window is the binding recovery state.  The
        # rebound signal remains the maximum across overlapping windows.
        binding = min(event_states, key=lambda item: item[2])
        return binding[0], binding[1], binding[2], max(item[3] for item in event_states)

    def _update_window_trackers(
        self,
        *,
        index: int,
        baseline_pcc_power_kw: float,
        pcc_power_kw: float,
    ) -> None:
        for event in self._events:
            if event.start_hour <= index < event.recovery_stop_hour:
                event_id = event.event_id
                self._running_baseline_peak_kw[event_id] = max(
                    self._running_baseline_peak_kw[event_id],
                    baseline_pcc_power_kw,
                )
                self._running_controlled_peak_kw[event_id] = max(
                    self._running_controlled_peak_kw[event_id],
                    pcc_power_kw,
                )
                if index >= event.stop_hour:
                    self._running_rebound_peak_kw[event_id] = max(
                        self._running_rebound_peak_kw[event_id],
                        pcc_power_kw - baseline_pcc_power_kw,
                        0.0,
                    )

    def _observation(self) -> np.ndarray:
        index = min(self._time_index, self.config.total_hours - 1)
        timestamp = self._community["timestamp"].iloc[index]
        hour = float(timestamp.hour)
        weekday = float(timestamp.dayofweek)
        net_community = float(self._community["net_community_load_kw"].iloc[index])
        pv = float(self._community["pv_generation_kw"].iloc[index])
        backlog_norm = max(self._capacity_gpu_h * self.config.max_deadline_hours, 1.0)
        controlled_feasibility = self._deadline_feasibility_ratios(self._queue)
        baseline_feasibility = self._deadline_feasibility_ratios(self._baseline_queue)
        excess_feasibility = np.maximum(controlled_feasibility - baseline_feasibility, 0.0)
        baseline_peak, controlled_peak, window_relief, running_rebound = (
            self._window_observation_state(index)
        )
        released_hours = min(index + 1, self.config.main_hours)
        cumulative_arrival_utilization = self._queue.cumulative_arrived_gpu_h / max(
            self._capacity_gpu_h * released_hours,
            1e-9,
        )
        cumulative_arrivals = max(self._queue.cumulative_arrived_gpu_h, 1e-9)
        deadline_miss_rate = self._queue.cumulative_missed_gpu_h / cumulative_arrivals
        baseline_deadline_miss_rate = (
            self._baseline_queue.cumulative_missed_gpu_h / cumulative_arrivals
        )
        terminal_excess_fraction = (
            max(
                self._queue.backlog_gpu_h - self._baseline_queue.backlog_gpu_h,
                0.0,
            )
            / cumulative_arrivals
        )
        forecast_stop = index + self.config.forecast_horizon_hours + 1
        community_forecast = (
            self._community["net_community_load_kw"]
            .iloc[index + 1 : forecast_stop]
            .to_numpy(dtype="float64")
        )
        limit_forecast = self._pcc_limit_kw[index + 1 : forecast_stop]
        if len(community_forecast) < self.config.forecast_horizon_hours:
            community_forecast = np.pad(
                community_forecast,
                (0, self.config.forecast_horizon_hours - len(community_forecast)),
                mode="edge",
            )
            limit_forecast = np.pad(
                limit_forecast,
                (0, self.config.forecast_horizon_hours - len(limit_forecast)),
                mode="edge",
            )
        forecast_headroom = [
            self._available_flexible_fraction(community_kw=float(community), limit_kw=float(limit))
            for community, limit in zip(community_forecast, limit_forecast, strict=True)
        ]
        has_previous_event = self._hours_since_previous_event[index] >= 0.0
        hours_since_fraction = (
            min(
                max(self._hours_since_previous_event[index], 0.0)
                / self.config.recovery_window_hours,
                1.0,
            )
            if has_previous_event
            else 0.0
        )
        events_last_24h = float(self._events_last_24h[index])
        values = [
            math.sin(2.0 * math.pi * hour / 24.0),
            math.cos(2.0 * math.pi * hour / 24.0),
            math.sin(2.0 * math.pi * weekday / 7.0),
            math.cos(2.0 * math.pi * weekday / 7.0),
            self._normalize_power(net_community),
            self._normalize_power(pv),
            self._normalize_power(float(self._pcc_limit_kw[index])),
            self._normalize_power(self._fixed_dc_power_kw),
            self._available_flexible_fraction(
                community_kw=net_community,
                limit_kw=float(self._pcc_limit_kw[index]),
            ),
            self._normalize_flexible_power(float(self._event_request_reference_kw[index])),
            self._bounded(self._queue.backlog_gpu_h / backlog_norm, 0.0, _MAX_NORMALIZED_LOAD),
            self._bounded(
                self._baseline_queue.backlog_gpu_h / backlog_norm,
                0.0,
                _MAX_NORMALIZED_LOAD,
            ),
            self._bounded(
                max(self._queue.backlog_gpu_h - self._baseline_queue.backlog_gpu_h, 0.0)
                / backlog_norm,
                0.0,
                _MAX_NORMALIZED_LOAD,
            ),
            self._bounded(
                cumulative_arrival_utilization,
                0.0,
                _MAX_NORMALIZED_LOAD,
            ),
            self._bounded(deadline_miss_rate, 0.0, 1.0),
            self._bounded(baseline_deadline_miss_rate, 0.0, 1.0),
            self._bounded(
                terminal_excess_fraction,
                0.0,
                _MAX_NORMALIZED_LOAD,
            ),
            self._queue.mean_slack_h / self.config.max_deadline_hours,
            self._queue.p10_slack_h / self.config.max_deadline_hours,
            *np.clip(controlled_feasibility, 0.0, _MAX_NORMALIZED_LOAD).tolist(),
            *np.clip(excess_feasibility, 0.0, _MAX_NORMALIZED_LOAD).tolist(),
            float(self._event_active[index]),
            float(self._post_event[index]),
            float(self._event_window_active[index]),
            float(self._event_notice_remaining_h[index] > 0.0),
            self._bounded(
                self._event_remaining_h[index] / max(self._event_duration_scale_h, 1.0),
                0.0,
                1.0,
            ),
            self._bounded(
                self._event_notice_remaining_h[index] / max(self._event_notice_scale_h, 1.0),
                0.0,
                1.0,
            ),
            self._bounded(
                self._recovery_remaining_h[index] / self.config.recovery_window_hours,
                0.0,
                1.0,
            ),
            events_last_24h / (events_last_24h + 1.0),
            float(has_previous_event),
            hours_since_fraction,
            self._normalize_power(baseline_peak),
            self._normalize_power(controlled_peak),
            self._bounded(window_relief, -_MAX_NORMALIZED_LOAD, _MAX_NORMALIZED_LOAD),
            self._bounded(running_rebound, 0.0, _MAX_NORMALIZED_LOAD),
            self._previous_action_fraction,
            self._normalize_power(self._previous_pcc_power_kw),
            *[self._normalize_power(value) for value in community_forecast],
            *forecast_headroom,
        ]
        observation = np.asarray(values, dtype=np.float32)
        if observation.shape != self.observation_space.shape:
            raise RuntimeError(
                f"observation shape {observation.shape} does not match "
                f"declared {self.observation_space.shape}"
            )
        if not self.observation_space.contains(observation):
            raise RuntimeError("normalized observation escaped its declared bounds")
        return observation

    @property
    def current_observation(self) -> np.ndarray:
        """Copy the current policy observation for an external evaluation policy."""

        return self._observation().copy()

    def _action_fraction(self, action: np.ndarray | int) -> float:
        if self.config.action_mode == "continuous":
            array = np.asarray(action, dtype="float32")
            if array.shape != (1,) or not self.action_space.contains(array):
                raise ValueError(
                    "continuous action must be a float32 array of shape (1,) in [0, 1]"
                )
            return float(array[0])
        if isinstance(action, bool) or not isinstance(action, int | np.integer):
            raise ValueError("discrete action must be an integer")
        action_index = int(action)
        if not self.action_space.contains(action_index):
            raise ValueError("discrete action is outside the action space")
        return float(DISCRETE_ACTION_FRACTIONS[action_index])

    def _control_state(self, *, current_pcc_kw: float) -> dict[str, Any]:
        index = min(self._time_index, self.config.total_hours - 1)
        bucket_gpu_h = self._queue.bucket_gpu_h
        controlled_feasibility = self._deadline_feasibility_ratios(self._queue)
        baseline_feasibility = self._deadline_feasibility_ratios(self._baseline_queue)
        baseline_peak, controlled_peak, window_relief, running_rebound = (
            self._window_observation_state(index)
        )
        forecast_stop = index + self.config.forecast_horizon_hours + 1
        community_forecast = (
            self._community["net_community_load_kw"]
            .iloc[index:forecast_stop]
            .to_numpy(dtype="float64")
        )
        limit_forecast = self._pcc_limit_kw[index:forecast_stop]
        if len(community_forecast) < self.config.forecast_horizon_hours + 1:
            padding = self.config.forecast_horizon_hours + 1 - len(community_forecast)
            community_forecast = np.pad(
                community_forecast,
                (0, padding),
                mode="edge",
            )
            limit_forecast = np.pad(limit_forecast, (0, padding), mode="edge")
        return {
            "pcc_limit_kw": float(self._pcc_limit_kw[index]),
            **self._sizing_metadata(),
            "community_power_kw": float(self._community["net_community_load_kw"].iloc[index]),
            # The idle flexible pool cannot be removed by an hourly workload
            # scheduler, so it belongs to the fixed term in Threshold RBC.
            "rigid_dc_power_kw": self._fixed_dc_power_kw,
            "flexible_pool_peak_power_kw": self._flexible_power_range_kw,
            "backlog_gpu_h": self._queue.backlog_gpu_h,
            "backlog_gpu_h_by_class": self._queue.backlog_gpu_h_by_class,
            "baseline_backlog_gpu_h": self._baseline_queue.backlog_gpu_h,
            "backlog_excess_gpu_h": max(
                self._queue.backlog_gpu_h - self._baseline_queue.backlog_gpu_h,
                0.0,
            ),
            "compute_debt_kwh": (
                self.power_model.queued_work_energy_kwh(dict(self._queue.backlog_gpu_h_by_class))
            ),
            "deadline_bucket_gpu_h": bucket_gpu_h,
            "remaining_by_deadline_gpu_h": self._queue.remaining_by_deadline_gpu_h,
            "deadline_feasibility_ratio": tuple(float(value) for value in controlled_feasibility),
            "baseline_deadline_feasibility_ratio": tuple(
                float(value) for value in baseline_feasibility
            ),
            "urgent_gpu_h": float(sum(bucket_gpu_h[:2])),
            "mean_slack_h": self._queue.mean_slack_h,
            "p10_slack_h": self._queue.p10_slack_h,
            "flexible_capacity_gpu_h": self._capacity_gpu_h,
            "community_forecast_kw": tuple(float(value) for value in community_forecast),
            "pcc_limit_forecast_kw": tuple(float(value) for value in limit_forecast),
            "event_active": bool(self._event_active[index]),
            "event_id": int(self._event_ids[index]),
            "event_source_id": str(self._event_source_ids[index]),
            "event_remaining_hours": float(self._event_remaining_h[index]),
            "event_notice_remaining_hours": float(self._event_notice_remaining_h[index]),
            "requested_reduction_kw": float(self._requested_reduction_kw[index]),
            "event_request_reference_kw": float(self._event_request_reference_kw[index]),
            "recovery_active": bool(self._post_event[index]),
            "recovery_remaining_hours": float(self._recovery_remaining_h[index]),
            "event_window_active": bool(self._event_window_active[index]),
            "running_window_baseline_peak_kw": baseline_peak,
            "running_window_pcc_peak_kw": controlled_peak,
            "running_window_relief_fraction": window_relief,
            "running_rebound_ratio": running_rebound,
            "events_last_24h": int(self._events_last_24h[index]),
            "hours_since_previous_event": float(self._hours_since_previous_event[index]),
            "current_pcc_power_kw": current_pcc_kw,
            "community_source": str(self._community["source"].iloc[0]),
            "community_profile_id": str(self._community["profile_id"].iloc[0]),
            "community_episode_start": str(self._community["timestamp"].iloc[0]),
            "dr_source": self.config.dr_source,
            "observation_version": self.observation_version,
        }

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        del options
        super().reset(seed=seed)
        # Explicit seeds remain exactly reproducible for evaluation.  During
        # SB3 training, auto-resets use ``seed=None``; sampling a fresh seed
        # there prevents a policy from memorizing one synthetic representative
        # week across every episode.
        seed_range = self.config.episode_seed_range
        if seed_range is not None:
            lower, upper = seed_range
            if seed is None:
                self._episode_seed = int(self.np_random.integers(lower, upper + 1))
            elif lower <= seed <= upper:
                self._episode_seed = seed
            else:
                self._episode_seed = lower + seed % (upper - lower + 1)
        elif seed is None:
            episode_offset = int(self.np_random.integers(0, np.iinfo(np.int32).max))
            self._episode_seed = self.config.seed + episode_offset
        else:
            self._episode_seed = self.config.seed + seed
        self._build_episode(self._episode_seed)
        observation = self._observation()
        return observation, {
            "training_share": self.config.workload_mix.training_share,
            "flexible_workload_share": self.config.workload_mix.flexible_share,
            "virtual_node_count": self.power_model.data_center.node_count,
            "flexible_gpu_count": self.power_model.data_center.flexible_gpu_count,
            **self._sizing_metadata(),
            **self._scenario_provenance(),
            **self._hardware_provenance(),
            "workload_source": self.config.workload_source,
            "episode_seed": self._episode_seed,
            "observation_version": self.observation_version,
            "observation_size": len(self.observation_feature_names),
            "community_source": str(self._community["source"].iloc[0]),
            "community_profile_id": str(self._community["profile_id"].iloc[0]),
            "community_episode_start": str(self._community["timestamp"].iloc[0]),
            "dr_source": self.config.dr_source,
            "dr_events_path": (
                str(self.config.dr_manifest_path)
                if self.config.dr_manifest_path is not None
                else "configured_in_yaml"
            ),
            "control_state": self._control_state(current_pcc_kw=0.0),
        }

    def step(
        self, action: np.ndarray | int
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self._time_index >= self.config.total_hours:
            raise RuntimeError("episode is complete; call reset before step")
        action_fraction = self._action_fraction(action)
        index = self._time_index
        queue_step = self._queue.advance(
            (),
            requested_gpu_h=action_fraction * self._capacity_gpu_h,
            capacity_gpu_h=self._capacity_gpu_h,
        )
        baseline_step = self._baseline_queue.advance(
            (),
            requested_gpu_h=self._capacity_gpu_h,
            capacity_gpu_h=self._capacity_gpu_h,
        )
        arrived_gpu_h = self._current_arrival_gpu_h
        prediction = self.power_model.predict_by_class(
            dict(queue_step.executed_gpu_h_by_class),
            timestep_hours=self.config.timestep_hours,
        )
        baseline_prediction = self.power_model.predict_by_class(
            dict(baseline_step.executed_gpu_h_by_class),
            timestep_hours=self.config.timestep_hours,
        )
        community_gross_power_kw = float(self._community["community_load_kw"].iloc[index])
        pv_generation_kw = float(self._community["pv_generation_kw"].iloc[index])
        community_power_kw = float(self._community["net_community_load_kw"].iloc[index])
        pcc_power_kw = community_power_kw + prediction.dc_power_kw
        baseline_pcc_power_kw = community_power_kw + baseline_prediction.dc_power_kw
        self._update_window_trackers(
            index=index,
            baseline_pcc_power_kw=baseline_pcc_power_kw,
            pcc_power_kw=pcc_power_kw,
        )
        limit_kw = float(self._pcc_limit_kw[index])
        violation_kw = max(pcc_power_kw - limit_kw, 0.0)
        requested_reduction_kw = float(self._requested_reduction_kw[index])
        delivered_reduction_kw = max(baseline_pcc_power_kw - pcc_power_kw, 0.0)
        delivery_ratio = (
            min(delivered_reduction_kw / requested_reduction_kw, 1.0)
            if requested_reduction_kw > 0.0
            else 1.0
        )
        rebound_excess_kw = (
            max(pcc_power_kw - baseline_pcc_power_kw, 0.0) if self._post_event[index] else 0.0
        )
        dr_tracking_error_fraction = (
            violation_kw / requested_reduction_kw if requested_reduction_kw > 0.0 else 0.0
        )
        rebound_reference_kw = float(self._rebound_reference_kw[index])
        rebound_ratio_proxy = (
            rebound_excess_kw / rebound_reference_kw if rebound_reference_kw > 0.0 else 0.0
        )
        backlog_excess_gpu_h = max(
            queue_step.backlog_gpu_h - baseline_step.backlog_gpu_h,
            0.0,
        )
        backlog_norm = max(self._capacity_gpu_h * self.config.max_deadline_hours, 1.0)
        reward_spec = self.config.reward
        delivery_violation_cost = (
            max(reward_spec.min_delivery_ratio - delivery_ratio, 0.0)
            / max(1.0 - reward_spec.min_delivery_ratio, 1e-9)
            if requested_reduction_kw > 0.0
            else 0.0
        )
        controlled_feasibility = self._deadline_feasibility_ratios(self._queue)
        baseline_feasibility = self._deadline_feasibility_ratios(self._baseline_queue)
        feasibility_violation_cost = float(
            np.maximum(
                controlled_feasibility / np.maximum(baseline_feasibility, 1.0) - 1.0,
                0.0,
            ).max()
        )
        cumulative_arrivals = max(self._queue.cumulative_arrived_gpu_h, 1e-9)
        deadline_miss_rate_so_far = self._queue.cumulative_missed_gpu_h / cumulative_arrivals
        deadline_violation_cost = (
            max(
                deadline_miss_rate_so_far - reward_spec.max_deadline_miss_rate,
                0.0,
            )
            / reward_spec.max_deadline_miss_rate
            if index + 1 >= self.config.total_hours
            else 0.0
        )
        _, _, running_window_relief, running_rebound_ratio = self._window_observation_state(index)
        running_rebound_violation_cost = (
            max(
                running_rebound_ratio - reward_spec.max_rebound_ratio,
                0.0,
            )
            / reward_spec.max_rebound_ratio
        )
        running_window_relief_violation_cost = (
            max(
                reward_spec.min_window_peak_relief_fraction - running_window_relief,
                0.0,
            )
            / reward_spec.min_window_peak_relief_fraction
        )
        completed_recovery_events = [
            event for event in self._events if index == event.recovery_stop_hour - 1
        ]
        rebound_violation_cost = sum(
            max(
                self._running_rebound_peak_kw[event.event_id]
                / max(event.requested_reduction_kw, 1e-9)
                - reward_spec.max_rebound_ratio,
                0.0,
            )
            / reward_spec.max_rebound_ratio
            for event in completed_recovery_events
        )
        window_relief_violation_cost = sum(
            max(
                reward_spec.min_window_peak_relief_fraction
                - (
                    self._running_baseline_peak_kw[event.event_id]
                    - self._running_controlled_peak_kw[event.event_id]
                )
                / max(event.requested_reduction_kw, 1e-9),
                0.0,
            )
            / reward_spec.min_window_peak_relief_fraction
            for event in completed_recovery_events
        )
        excess_backlog_shaping_cost = backlog_excess_gpu_h / backlog_norm
        switching_cost = abs(action_fraction - self._previous_action_fraction)
        self._previous_action_fraction = action_fraction
        self._previous_pcc_power_kw = pcc_power_kw
        self._time_index += 1
        truncated = self._time_index >= self.config.total_hours
        terminal_backlog_violation_cost = 0.0
        terminal_backlog_excess_gpu_h = max(
            queue_step.backlog_gpu_h - baseline_step.backlog_gpu_h,
            0.0,
        )
        terminal_backlog_excess_fraction = terminal_backlog_excess_gpu_h / cumulative_arrivals
        if truncated:
            terminal_backlog_violation_cost = (
                max(
                    terminal_backlog_excess_fraction - reward_spec.max_terminal_backlog_fraction,
                    0.0,
                )
                / reward_spec.max_terminal_backlog_fraction
            )
        weighted_reward_costs = {
            "delivery": reward_spec.delivery_violation_weight
            * self._huber_violation(delivery_violation_cost),
            "feasibility": reward_spec.feasibility_violation_weight
            * self._huber_violation(feasibility_violation_cost),
            "deadline": reward_spec.deadline_violation_weight
            * self._huber_violation(deadline_violation_cost),
            "rebound": reward_spec.rebound_violation_weight
            * self._huber_violation(rebound_violation_cost),
            "window_relief": reward_spec.window_violation_weight
            * self._huber_violation(window_relief_violation_cost),
            "terminal_backlog": reward_spec.terminal_violation_weight
            * self._huber_violation(terminal_backlog_violation_cost),
            "excess_backlog": reward_spec.excess_backlog_weight * excess_backlog_shaping_cost,
            "switching": reward_spec.switching_weight * switching_cost,
        }
        reward_penalty = sum(weighted_reward_costs.values())
        reward = -reward_penalty
        recovery_tolerance_gpu_h = (
            self.config.recovery_backlog_tolerance_fraction * self._capacity_gpu_h
        )
        has_completed_event = any(event.stop_hour <= index for event in self._events)
        recovery_complete = (
            has_completed_event and terminal_backlog_excess_gpu_h <= recovery_tolerance_gpu_h
        )
        if not truncated:
            self._current_arrival_gpu_h = self._preload_arrivals(self._time_index)
        else:
            self._current_arrival_gpu_h = 0.0
        observation = self._observation()
        info: dict[str, Any] = {
            "pcc_power_kw": pcc_power_kw,
            "baseline_pcc_power_kw": baseline_pcc_power_kw,
            "dc_power_kw": prediction.dc_power_kw,
            "community_power_kw": community_power_kw,
            "community_gross_power_kw": community_gross_power_kw,
            "pv_generation_kw": pv_generation_kw,
            "pcc_limit_kw": limit_kw,
            "requested_reduction_kw": requested_reduction_kw,
            "delivered_reduction_kw": delivered_reduction_kw,
            "delivery_ratio": delivery_ratio,
            "limit_violation_kw": violation_kw,
            "dr_tracking_error_fraction": dr_tracking_error_fraction,
            "reward_version": reward_spec.version,
            "delivery_violation_cost": delivery_violation_cost,
            "deadline_feasibility_violation_cost": feasibility_violation_cost,
            "deadline_miss_rate_so_far": deadline_miss_rate_so_far,
            "deadline_violation_cost": deadline_violation_cost,
            "rebound_violation_cost": rebound_violation_cost,
            "window_relief_violation_cost": window_relief_violation_cost,
            "running_rebound_violation_cost": running_rebound_violation_cost,
            "running_window_relief_violation_cost": (
                running_window_relief_violation_cost if self._event_window_active[index] else 0.0
            ),
            "completed_recovery_event_count": len(completed_recovery_events),
            "terminal_backlog_violation_cost": terminal_backlog_violation_cost,
            "excess_backlog_shaping_cost": excess_backlog_shaping_cost,
            "switching_cost": switching_cost,
            "reward_penalty": reward_penalty,
            **{f"weighted_{name}_cost": value for name, value in weighted_reward_costs.items()},
            "executed_gpu_h": queue_step.executed_gpu_h,
            "arrival_gpu_h": arrived_gpu_h,
            "backlog_gpu_h": queue_step.backlog_gpu_h,
            "arrival_gpu_h_by_class": queue_step.arrived_gpu_h_by_class,
            "executed_gpu_h_by_class": queue_step.executed_gpu_h_by_class,
            "missed_gpu_h_by_class": queue_step.missed_gpu_h_by_class,
            "backlog_gpu_h_by_class": queue_step.backlog_gpu_h_by_class,
            "baseline_backlog_gpu_h": baseline_step.backlog_gpu_h,
            "backlog_excess_gpu_h": backlog_excess_gpu_h,
            "missed_gpu_h": queue_step.missed_gpu_h,
            "mean_slack_h": queue_step.mean_slack_h,
            "p10_slack_h": queue_step.p10_slack_h,
            "compute_debt_kwh": (
                self.power_model.queued_work_energy_kwh(dict(queue_step.backlog_gpu_h_by_class))
            ),
            "deadline_bucket_gpu_h": queue_step.bucket_gpu_h,
            "action_fraction": action_fraction,
            "event_active": bool(self._event_active[index]),
            "event_id": int(self._event_ids[index]),
            "event_source_id": str(self._event_source_ids[index]),
            "event_remaining_hours": float(self._event_remaining_h[index]),
            "event_notice_remaining_hours": float(self._event_notice_remaining_h[index]),
            "event_request_reference_kw": float(self._event_request_reference_kw[index]),
            "recovery_active": bool(self._post_event[index]),
            "recovery_remaining_hours": float(self._recovery_remaining_h[index]),
            "event_window_active": bool(self._event_window_active[index]),
            "events_last_24h": int(self._events_last_24h[index]),
            "hours_since_previous_event": float(self._hours_since_previous_event[index]),
            "rebound_excess_kw": rebound_excess_kw,
            "rebound_reference_kw": rebound_reference_kw,
            "rebound_ratio_proxy": rebound_ratio_proxy,
            "running_window_relief_fraction": running_window_relief,
            "running_rebound_ratio": running_rebound_ratio,
            "flexible_active_gpus": prediction.active_flexible_gpus,
            "flexible_energy_kwh": prediction.flexible_energy_kwh,
            "dc_energy_kwh": prediction.dc_energy_kwh,
            "is_clearance_tail": index >= self.config.main_hours,
            "training_share": self.config.workload_mix.training_share,
            "flexible_workload_share": self.config.workload_mix.flexible_share,
            **self._sizing_metadata(),
            **self._hardware_provenance(),
            **self._scenario_provenance(),
            "workload_source": self.config.workload_source,
            "episode_seed": self._episode_seed,
            "observation_version": self.observation_version,
            "community_source": str(self._community["source"].iloc[0]),
            "community_profile_id": str(self._community["profile_id"].iloc[0]),
            "community_episode_start": str(self._community["timestamp"].iloc[0]),
            "dr_source": self.config.dr_source,
            "dr_events_path": (
                str(self.config.dr_manifest_path)
                if self.config.dr_manifest_path is not None
                else "configured_in_yaml"
            ),
            "conservation_error_gpu_h": self._queue.conservation_error_gpu_h(),
            "terminal_backlog_penalty": weighted_reward_costs["terminal_backlog"],
            "terminal_backlog_excess_gpu_h": terminal_backlog_excess_gpu_h,
            "terminal_backlog_excess_fraction": terminal_backlog_excess_fraction,
            "recovery_complete": recovery_complete,
            "control_state": self._control_state(current_pcc_kw=pcc_power_kw),
        }
        return observation, float(reward), False, truncated, info


class ContinuousCommunityAIDemandResponseEnv(HourlyCommunityAIDemandResponseEnv):
    """Continuous action specialization: fraction of flexible GPU-hour capacity."""

    def __init__(self, config: str | Path | Mapping[str, Any]) -> None:
        super().__init__(config, action_mode="continuous")


class DiscreteCommunityAIDemandResponseEnv(HourlyCommunityAIDemandResponseEnv):
    """Five-level discrete action specialization for DQN and rule baselines."""

    def __init__(self, config: str | Path | Mapping[str, Any]) -> None:
        super().__init__(config, action_mode="discrete")
