"""Deterministic community-load and demand-response event generators."""

from __future__ import annotations

import glob
import re
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.splits import sha256_file

COMMUNITY_COLUMNS = (
    "timestamp",
    "community_load_kw",
    "pv_generation_kw",
    "net_community_load_kw",
    "profile_id",
    "season",
    "source",
)
DR_COLUMNS = (
    "event_id",
    "start_time",
    "end_time",
    "duration_minutes",
    "notice_minutes",
    "reduction_fraction",
    "pcc_limit_kw",
    "post_event_ramp_minutes",
)


def make_synthetic_community(
    output: str | Path,
    *,
    days: int = 30,
    resolution_seconds: int = 900,
    peak_kw: float = 100.0,
    seed: int = 42,
) -> dict[str, object]:
    """Generate a reproducible smoke profile with correlated noise and two peaks."""

    if days <= 0 or resolution_seconds <= 0 or peak_kw <= 0:
        raise ValueError("days, resolution_seconds, and peak_kw must be positive")
    if 86_400 % resolution_seconds != 0:
        raise ValueError("resolution_seconds must divide one day exactly")

    periods = days * 86_400 // resolution_seconds
    timestamps = pd.date_range(
        "2020-01-01T00:00:00Z",
        periods=periods,
        freq=timedelta(seconds=resolution_seconds),
    )
    hours = (
        timestamps.hour.to_numpy(dtype="float64")
        + timestamps.minute.to_numpy(dtype="float64") / 60.0
    )
    morning = 0.23 * np.exp(-0.5 * ((hours - 7.5) / 1.6) ** 2)
    evening = 0.43 * np.exp(-0.5 * ((hours - 19.0) / 2.0) ** 2)
    daily = 0.06 * np.sin(2.0 * np.pi * (hours - 4.0) / 24.0)
    rng = np.random.default_rng(seed)
    innovations = rng.normal(0.0, 0.012, size=periods)
    correlated_noise = np.empty(periods, dtype="float64")
    correlated_noise[0] = innovations[0]
    for index in range(1, periods):
        correlated_noise[index] = 0.92 * correlated_noise[index - 1] + innovations[index]
    day_modulation = 1.0 + 0.04 * np.sin(2.0 * np.pi * np.arange(periods) / periods)
    raw_load = np.clip(
        (0.55 + morning + evening + daily + correlated_noise) * day_modulation,
        0.1,
        None,
    )
    community_load = peak_kw * raw_load / float(raw_load.max())

    daylight = np.maximum(0.0, np.sin(np.pi * (hours - 6.0) / 12.0))
    pv_generation = 0.15 * peak_kw * daylight**1.8
    net_load = community_load - pv_generation
    month = timestamps.month.to_numpy()
    season = np.select(
        [
            np.isin(month, [12, 1, 2]),
            np.isin(month, [3, 4, 5]),
            np.isin(month, [6, 7, 8]),
        ],
        ["winter", "spring", "summer"],
        default="autumn",
    )
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "community_load_kw": community_load,
            "pv_generation_kw": pv_generation,
            "net_community_load_kw": net_load,
            "profile_id": f"synthetic_seed_{seed}",
            "season": season,
            "source": "synthetic_smoke",
        }
    ).loc[:, COMMUNITY_COLUMNS]
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    energy_kwh = float(frame["community_load_kw"].sum() * resolution_seconds / 3600.0)
    return {
        "dataset": "community_synthetic",
        "rows": len(frame),
        "days": days,
        "resolution_seconds": resolution_seconds,
        "peak_kw": peak_kw,
        "energy_kwh": energy_kwh,
        "seed": seed,
        "output": str(output_path),
    }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def catalog_community_profiles(input_pattern: str, output: str | Path) -> dict[str, object]:
    """Discover downloaded EULP profiles without hard-coding locations in code."""

    paths = [Path(value) for value in sorted(glob.glob(input_pattern, recursive=True))]
    if not paths:
        raise FileNotFoundError(f"no community CSV files matched: {input_pattern}")
    profiles: list[dict[str, object]] = []
    for path in paths:
        sample = pd.read_csv(path, nrows=1)
        if sample.empty:
            raise ValueError(f"community CSV is empty: {path}")
        if "in.ashrae_iecc_climate_zone_2004" in sample.columns:
            source_kind = "resstock"
            climate_column = "in.ashrae_iecc_climate_zone_2004"
            building_column = "in.geometry_building_type_recs"
            total_column = "out.electricity.total.energy_consumption..kwh"
            pv_column = "out.electricity.pv.energy_consumption..kwh"
            net_column = "out.electricity.net.energy_consumption..kwh"
            release = "resstock_amy2018_release_1"
        elif "in.ashrae_iecc_climate_zone_2006" in sample.columns:
            source_kind = "comstock"
            climate_column = "in.ashrae_iecc_climate_zone_2006"
            building_column = "in.comstock_building_type"
            total_column = "out.electricity.total.energy_consumption.kwh"
            pv_column = "out.electricity.pv.energy_consumption.kwh"
            net_column = "out.electricity.net.energy_consumption.kwh"
            release = "comstock_amy2018_release_3"
        else:
            raise ValueError(f"unsupported EULP schema: {path}")
        required = {
            "timestamp",
            climate_column,
            building_column,
            total_column,
            pv_column,
            net_column,
        }
        missing = sorted(required - set(sample.columns))
        if missing:
            raise ValueError(f"{path} is missing EULP columns: {missing}")
        climate_zone = str(sample[climate_column].iloc[0])
        building_type = str(sample[building_column].iloc[0])
        profile_id = f"eulp_{source_kind}_{_slug(climate_zone)}_{_slug(building_type)}"
        profiles.append(
            {
                "profile_id": profile_id,
                "source_kind": source_kind,
                "source_release": release,
                "climate_zone": climate_zone,
                "building_type": building_type,
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "timestamp_column": "timestamp",
                "climate_column": climate_column,
                "building_column": building_column,
                "total_column": total_column,
                "pv_column": pv_column,
                "net_column": net_column,
            }
        )
    profile_ids = [str(entry["profile_id"]) for entry in profiles]
    duplicate_ids = {profile_id for profile_id in profile_ids if profile_ids.count(profile_id) > 1}
    used_ids = set(profile_ids) - duplicate_ids
    for entry in profiles:
        base_id = str(entry["profile_id"])
        if base_id not in duplicate_ids:
            continue
        source_tag = _slug(Path(str(entry["path"])).stem)
        candidate = f"{base_id}_{source_tag}"
        if candidate in used_ids:
            candidate = f"{candidate}_{str(entry['sha256'])[:8]}"
        entry["profile_id"] = candidate
        used_ids.add(candidate)
    profile_ids = [str(entry["profile_id"]) for entry in profiles]
    document: dict[str, object] = {
        "schema_version": 1,
        "selection_policy": "configuration_driven",
        "profiles": profiles,
    }
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(document, handle, sort_keys=False)
    return {"profiles": profile_ids, "count": len(profiles), "output": str(output_path)}


def _load_catalog(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("profiles"), list):
        raise ValueError("community catalog must contain a profiles list")
    profiles: list[dict[str, object]] = []
    for raw_entry in document["profiles"]:
        if not isinstance(raw_entry, dict):
            raise ValueError("community catalog profile entries must be mappings")
        profiles.append({str(key): value for key, value in raw_entry.items()})
    return profiles


def list_community_profiles(catalog: str | Path) -> list[dict[str, object]]:
    """Return the selectable profile fields shown by the CLI."""

    fields = (
        "profile_id",
        "source_kind",
        "source_release",
        "climate_zone",
        "building_type",
        "path",
    )
    return [{field: entry[field] for field in fields} for entry in _load_catalog(catalog)]


def _season(timestamps: pd.Series[Any]) -> np.ndarray[Any, np.dtype[np.str_]]:
    month = timestamps.dt.month.to_numpy()
    return np.select(
        [
            np.isin(month, [12, 1, 2]),
            np.isin(month, [3, 4, 5]),
            np.isin(month, [6, 7, 8]),
        ],
        ["winter", "spring", "summer"],
        default="autumn",
    )


def _load_eulp_profile(entry: dict[str, object], peak_kw: float) -> pd.DataFrame:
    columns = [
        str(entry["timestamp_column"]),
        str(entry["total_column"]),
        str(entry["pv_column"]),
        str(entry["net_column"]),
    ]
    raw = pd.read_csv(str(entry["path"]), usecols=columns)
    timestamps = pd.to_datetime(raw[columns[0]])
    differences = timestamps.sort_values().diff().dt.total_seconds().dropna()
    resolution_seconds = float(differences.median())
    if resolution_seconds <= 0:
        raise ValueError(f"invalid EULP time resolution for {entry['profile_id']}")
    energy_to_kw = 3600.0 / resolution_seconds
    gross_kw = pd.to_numeric(raw[columns[1]], errors="raise") * energy_to_kw
    pv_kw = (-pd.to_numeric(raw[columns[2]], errors="raise") * energy_to_kw).clip(lower=0)
    net_kw = pd.to_numeric(raw[columns[3]], errors="raise") * energy_to_kw
    scale = peak_kw / float(gross_kw.max())
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "community_load_kw": gross_kw * scale,
            "pv_generation_kw": pv_kw * scale,
            "net_community_load_kw": net_kw * scale,
            "profile_id": str(entry["profile_id"]),
            "season": _season(timestamps),
            "source": "nlr_nrel_eulp_modeled",
            "climate_zone": str(entry["climate_zone"]),
            "building_type": str(entry["building_type"]),
            "profile_kind": str(entry["source_kind"]),
            "source_file": Path(str(entry["path"])).name,
            "timezone_basis": "source_local_clock_unspecified",
        }
    )


def preprocess_community_profiles(
    catalog: str | Path,
    output: str | Path,
    *,
    profiles: list[str] | None = None,
    peak_kw: float = 100.0,
    include_mixed: bool = False,
    commercial_weight: float = 0.25,
) -> dict[str, object]:
    """Scale any catalog-selected EULP profiles and optionally construct mixtures."""

    if peak_kw <= 0:
        raise ValueError("peak_kw must be positive")
    if not 0 < commercial_weight < 1:
        raise ValueError("commercial_weight must be strictly between zero and one")
    entries = _load_catalog(catalog)
    available = {str(entry["profile_id"]): entry for entry in entries}
    selected_ids = profiles if profiles else sorted(available)
    unknown = sorted(set(selected_ids) - set(available))
    if unknown:
        raise ValueError(f"unknown community profile IDs: {unknown}")
    selected_entries = [available[profile_id] for profile_id in selected_ids]
    loaded = {
        str(entry["profile_id"]): _load_eulp_profile(entry, peak_kw) for entry in selected_entries
    }
    output_frames = list(loaded.values())
    mixed_ids: list[str] = []
    if include_mixed:
        residential = [entry for entry in selected_entries if entry["source_kind"] == "resstock"]
        commercial = [entry for entry in selected_entries if entry["source_kind"] == "comstock"]
        for residential_entry in residential:
            for commercial_entry in commercial:
                if residential_entry["climate_zone"] != commercial_entry["climate_zone"]:
                    continue
                residential_id = str(residential_entry["profile_id"])
                commercial_id = str(commercial_entry["profile_id"])
                left = loaded[residential_id]
                right = loaded[commercial_id]
                merged = left.merge(right, on="timestamp", suffixes=("_res", "_com"))
                mixed_id = f"eulp_mixed_{_slug(str(residential_entry['climate_zone']))}"
                gross = (1.0 - commercial_weight) * merged["community_load_kw_res"] + (
                    commercial_weight * merged["community_load_kw_com"]
                )
                pv = (1.0 - commercial_weight) * merged["pv_generation_kw_res"] + (
                    commercial_weight * merged["pv_generation_kw_com"]
                )
                net = (1.0 - commercial_weight) * merged["net_community_load_kw_res"] + (
                    commercial_weight * merged["net_community_load_kw_com"]
                )
                scale = peak_kw / float(gross.max())
                output_frames.append(
                    pd.DataFrame(
                        {
                            "timestamp": merged["timestamp"],
                            "community_load_kw": gross * scale,
                            "pv_generation_kw": pv * scale,
                            "net_community_load_kw": net * scale,
                            "profile_id": mixed_id,
                            "season": merged["season_res"],
                            "source": "nlr_nrel_eulp_modeled_mixture",
                            "climate_zone": str(residential_entry["climate_zone"]),
                            "building_type": "residential_plus_small_commercial",
                            "profile_kind": "mixed",
                            "source_file": (
                                f"{Path(str(residential_entry['path'])).name}"
                                f"+{Path(str(commercial_entry['path'])).name}"
                            ),
                            "timezone_basis": "source_local_clock_unspecified",
                        }
                    )
                )
                mixed_ids.append(mixed_id)
    result = pd.concat(output_frames, ignore_index=True)
    result = result.sort_values(["timestamp", "profile_id"], kind="stable").reset_index(drop=True)
    ordered_columns = (
        *COMMUNITY_COLUMNS,
        *(column for column in result if column not in COMMUNITY_COLUMNS),
    )
    result = result.loc[:, ordered_columns]
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    return {
        "dataset": "nlr_nrel_eulp",
        "rows": len(result),
        "selected_profiles": selected_ids,
        "mixed_profiles": sorted(mixed_ids),
        "peak_kw": peak_kw,
        "commercial_weight": commercial_weight if include_mixed else None,
        "output": str(output_path),
    }


def generate_dr_events(
    community: str | Path,
    output: str | Path,
    *,
    days: int,
    reductions: list[float],
    durations: list[int],
    notices: list[int],
    seed: int = 42,
    profile_id: str | None = None,
) -> dict[str, object]:
    """Generate a fixed DR manifest against a community counterfactual baseline."""

    if days <= 0 or not reductions or not durations or not notices:
        raise ValueError("days and all DR factor lists must be non-empty")
    if any(value <= 0 or value >= 1 for value in reductions):
        raise ValueError("reductions must be fractions strictly between zero and one")
    if any(value <= 0 for value in durations) or any(value < 0 for value in notices):
        raise ValueError("durations must be positive and notices must be non-negative")

    load = pd.read_parquet(community)
    required = {"timestamp", "net_community_load_kw"}
    if not required.issubset(load.columns):
        raise ValueError(
            f"community Parquet is missing columns: {sorted(required - set(load.columns))}"
        )
    selected_profile_id = profile_id
    if "profile_id" in load.columns:
        available_profiles = sorted(load["profile_id"].astype("string").unique().tolist())
        if selected_profile_id is None and len(available_profiles) > 1:
            raise ValueError(
                "community contains multiple profiles; select one with --profile-id from "
                f"{available_profiles}"
            )
        selected_profile_id = selected_profile_id or str(available_profiles[0])
        if selected_profile_id not in available_profiles:
            raise ValueError(f"unknown community profile_id: {selected_profile_id}")
        load = load[load["profile_id"] == selected_profile_id]
    load = load.loc[:, ["timestamp", "net_community_load_kw"]].copy()
    load["timestamp"] = pd.to_datetime(load["timestamp"])
    load = load.sort_values("timestamp", kind="stable").reset_index(drop=True)
    first_day = load["timestamp"].dt.floor("D").min()
    available_days = int(load["timestamp"].dt.floor("D").nunique())
    if days > available_days:
        raise ValueError(f"requested {days} days but community contains {available_days}")

    rng = np.random.default_rng(seed)
    events: list[dict[str, object]] = []
    event_counter = 0
    for day_index in range(days):
        day_start = first_day + timedelta(days=day_index)
        event_count = int(rng.integers(1, 4))
        if day_index % 3 == 0:
            event_count = max(2, event_count)
        previous_end = day_start + timedelta(hours=10)
        for within_day in range(event_count):
            duration = int(rng.choice(durations))
            notice = int(rng.choice(notices))
            reduction = float(rng.choice(reductions))
            if within_day == 0:
                candidate = day_start + timedelta(minutes=int(rng.integers(11 * 60, 14 * 60 + 1)))
            else:
                gap = int(rng.choice([15, 30, 60, 180]))
                candidate = previous_end + timedelta(minutes=gap)
            latest_start = day_start + timedelta(days=1, minutes=-duration - 1)
            start = min(candidate, latest_start)
            end = start + timedelta(minutes=duration)
            nearest_index = int((load["timestamp"] - start).abs().idxmin())
            baseline_kw = cast(float, load.loc[nearest_index, "net_community_load_kw"])
            event_counter += 1
            events.append(
                {
                    "event_id": f"dr_{event_counter:05d}",
                    "start_time": start,
                    "end_time": end,
                    "duration_minutes": duration,
                    "notice_minutes": notice,
                    "reduction_fraction": reduction,
                    "pcc_limit_kw": baseline_kw * (1.0 - reduction),
                    "post_event_ramp_minutes": int(rng.choice([15, 30, 60])),
                }
            )
            previous_end = end

    frame = pd.DataFrame(events).loc[:, DR_COLUMNS]
    frame["community_profile_id"] = selected_profile_id or "unspecified"
    frame = frame.sort_values("start_time", kind="stable").reset_index(drop=True)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    return {
        "dataset": "dr_events_synthetic",
        "rows": len(frame),
        "days": days,
        "seed": seed,
        "baseline": "community_counterfactual_at_event_start",
        "community_profile_id": selected_profile_id,
        "output": str(output_path),
    }
