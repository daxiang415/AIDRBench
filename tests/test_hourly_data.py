from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aidrbench.data.hourly import (
    WorkloadMix,
    load_hourly_community_profile,
    load_hourly_dr_manifest,
    make_synthetic_hourly_arrivals,
    select_dr_aligned_episode_start,
    select_hourly_community_window,
)


def _mix(training_share: float) -> WorkloadMix:
    return WorkloadMix(
        shares={
            "training": training_share,
            "offline_inference": 0.0,
            "online_inference": 1.0 - training_share,
        },
        flexible_fractions={
            "training": 1.0,
            "offline_inference": 0.8,
            "online_inference": 0.0,
        },
    )


def test_training_share_changes_flexible_gpu_hour_supply() -> None:
    low_training = make_synthetic_hourly_arrivals(
        hours=48,
        total_gpu_count=16,
        target_total_utilization=0.60,
        workload_mix=_mix(0.20),
        seed=17,
    )
    high_training = make_synthetic_hourly_arrivals(
        hours=48,
        total_gpu_count=16,
        target_total_utilization=0.60,
        workload_mix=_mix(0.80),
        seed=17,
    )

    assert _mix(0.20).flexible_share == pytest.approx(0.20)
    assert _mix(0.80).flexible_share == pytest.approx(0.80)
    assert high_training["arrival_gpu_h"].sum() == pytest.approx(
        low_training["arrival_gpu_h"].sum() * 4.0
    )


def test_hourly_arrivals_are_reproducible_from_seed() -> None:
    kwargs = {
        "hours": 24,
        "total_gpu_count": 8,
        "target_total_utilization": 0.5,
        "workload_mix": _mix(0.50),
        "seed": 99,
    }

    first = make_synthetic_hourly_arrivals(**kwargs)
    second = make_synthetic_hourly_arrivals(**kwargs)

    assert first.equals(second)


def _write_subhourly_community(path: Path, *, hours: int = 12) -> None:
    timestamps = pd.date_range("2018-01-01 00:15:00", periods=hours * 4, freq="15min")
    records: list[pd.DataFrame] = []
    for profile_id, multiplier in (("residential", 1.0), ("commercial", 2.0)):
        gross = pd.Series(range(1, len(timestamps) + 1), dtype="float64") * multiplier
        records.append(
            pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "community_load_kw": gross,
                    "pv_generation_kw": gross * 0.10,
                    "net_community_load_kw": gross * 0.90,
                    "profile_id": profile_id,
                    "source": "test_eulp",
                }
            )
        )
    pd.concat(records, ignore_index=True).to_parquet(path, index=False)


def test_real_community_profile_is_selected_resampled_and_scaled(tmp_path: Path) -> None:
    source = tmp_path / "community.parquet"
    _write_subhourly_community(source)

    hourly = load_hourly_community_profile(
        source,
        profile_id="residential",
        target_peak_kw=1_000.0,
        pv_enabled=True,
    )

    assert len(hourly) == 12
    assert hourly["timestamp"].iloc[0] == pd.Timestamp("2018-01-01 00:00:00")
    assert hourly["community_load_kw"].max() == pytest.approx(1_000.0)
    assert hourly["pv_generation_kw"].max() == pytest.approx(100.0)
    assert hourly["net_community_load_kw"].max() == pytest.approx(900.0)
    assert set(hourly["profile_id"]) == {"residential"}


def test_real_community_requires_profile_selection_and_has_reproducible_windows(
    tmp_path: Path,
) -> None:
    source = tmp_path / "community.parquet"
    _write_subhourly_community(source)

    with pytest.raises(ValueError, match="multiple profiles"):
        load_hourly_community_profile(
            source,
            profile_id=None,
            target_peak_kw=1_000.0,
            pv_enabled=False,
        )
    hourly = load_hourly_community_profile(
        source,
        profile_id="commercial",
        target_peak_kw=1_000.0,
        pv_enabled=False,
    )
    first = select_hourly_community_window(hourly, hours=4, seed=19)
    second = select_hourly_community_window(hourly, hours=4, seed=19)

    assert first.equals(second)
    assert first["pv_generation_kw"].sum() == pytest.approx(0.0)
    assert first["community_load_kw"].equals(first["net_community_load_kw"])


def test_real_community_window_selection_respects_temporal_partition(tmp_path: Path) -> None:
    source = tmp_path / "community.parquet"
    _write_subhourly_community(source, hours=72)
    hourly = load_hourly_community_profile(
        source,
        profile_id="commercial",
        target_peak_kw=1_000.0,
        pv_enabled=False,
    )

    selected = select_hourly_community_window(
        hourly,
        hours=12,
        seed=7,
        window_start="2018-01-02T00:00:00",
        window_end="2018-01-03T00:00:00",
    )

    assert selected["timestamp"].iloc[0] == pd.Timestamp("2018-01-02T00:00:00")
    assert selected["timestamp"].iloc[-1] < pd.Timestamp("2018-01-03T00:00:00")


def test_hourly_dr_manifest_is_validated_and_selects_an_event_window(tmp_path: Path) -> None:
    community_source = tmp_path / "community.parquet"
    _write_subhourly_community(community_source, hours=72)
    community = load_hourly_community_profile(
        community_source,
        profile_id="residential",
        target_peak_kw=1_000.0,
        pv_enabled=True,
    )
    manifest_path = tmp_path / "dr.parquet"
    pd.DataFrame(
        {
            "event_id": ["event_a"],
            "start_time": [pd.Timestamp("2018-01-02 12:00:00")],
            "end_time": [pd.Timestamp("2018-01-02 14:00:00")],
            "duration_minutes": [120],
            "notice_minutes": [120],
            "reduction_fraction": [0.2],
            "community_profile_id": ["residential"],
        }
    ).to_parquet(manifest_path, index=False)

    events = load_hourly_dr_manifest(manifest_path, profile_id="residential")
    start = select_dr_aligned_episode_start(
        community,
        events,
        total_hours=27,
        main_hours=24,
        seed=3,
        episode_start="2018-01-02 00:00:00",
    )

    assert start == "2018-01-02T00:00:00"
    assert events.loc[0, "event_id"] == "event_a"


def test_hourly_dr_manifest_rejects_subhourly_events(tmp_path: Path) -> None:
    manifest_path = tmp_path / "dr.parquet"
    pd.DataFrame(
        {
            "event_id": ["event_a"],
            "start_time": [pd.Timestamp("2018-01-02 12:15:00")],
            "end_time": [pd.Timestamp("2018-01-02 12:45:00")],
            "duration_minutes": [30],
            "notice_minutes": [15],
            "reduction_fraction": [0.2],
        }
    ).to_parquet(manifest_path, index=False)

    with pytest.raises(ValueError, match="whole-hour"):
        load_hourly_dr_manifest(manifest_path, profile_id=None)
