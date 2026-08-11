from __future__ import annotations

from pathlib import Path

import pandas as pd

from aidrbench.data.alibaba import preprocess_alibaba
from aidrbench.data.burstgpt import REQUIRED_COLUMNS, preprocess_burstgpt
from aidrbench.data.community import (
    DR_COLUMNS,
    catalog_community_profiles,
    generate_dr_events,
    list_community_profiles,
    make_synthetic_community,
    preprocess_community_profiles,
)
from aidrbench.data.splits import (
    create_split_manifest,
    validate_manifest,
    validate_source_manifest,
)


def test_burstgpt_filters_scales_and_preserves_schema(tmp_path: Path) -> None:
    source = tmp_path / "burst.csv"
    pd.DataFrame(
        {
            "Timestamp": [10, 20, 40],
            "Model": ["ChatGPT", "GPT-4", "GPT-4"],
            "Request tokens": [100, 0, 200],
            "Response tokens": [20, 30, 0],
            "Total tokens": [120, 30, 200],
            "Log Type": ["Conversation log"] * 3,
        }
    ).to_csv(source, index=False)
    output = tmp_path / "requests.parquet"

    summary = preprocess_burstgpt(str(source), output, time_scale=2.0)
    result = pd.read_parquet(output)

    assert summary["output_rows"] == 1
    assert tuple(result.columns) == REQUIRED_COLUMNS
    assert result.loc[0, "timestamp_s"] == 10
    assert result.loc[0, "elapsed_time_s"] == 0


def test_alibaba_marks_deadlines_as_synthetic(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs.csv"
    tasks = tmp_path / "tasks.csv"
    pd.DataFrame(
        [
            ["job-a", "id-a", "u", "Terminated", 100, 200],
            ["job-b", "id-b", "u", "Failed", 110, 210],
        ],
        columns=["job_name", "inst_id", "user", "status", "start_time", "end_time"],
    ).to_csv(jobs, index=False)
    pd.DataFrame(
        [["job-a", "worker", 2, "Terminated", 110, 190, 100, 4, 50, "V100"]],
        columns=[
            "job_name",
            "task_name",
            "inst_num",
            "status",
            "start_time",
            "end_time",
            "plan_cpu",
            "plan_mem",
            "plan_gpu",
            "gpu_type",
        ],
    ).to_csv(tasks, index=False)
    output = tmp_path / "batch.parquet"

    preprocess_alibaba(jobs, tasks, output, seed=7)
    result = pd.read_parquet(output)

    assert len(result) == 1
    assert result.loc[0, "work_gpu_seconds"] == 80
    assert bool(result.loc[0, "deadline_is_synthetic"])
    assert result.loc[0, "deadline_time_s"] > result.loc[0, "release_time_s"]


def test_community_dr_and_split_are_reproducible(tmp_path: Path) -> None:
    community_a = tmp_path / "community-a.parquet"
    community_b = tmp_path / "community-b.parquet"
    make_synthetic_community(community_a, days=3, seed=11)
    make_synthetic_community(community_b, days=3, seed=11)
    first = pd.read_parquet(community_a)
    second = pd.read_parquet(community_b)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 3 * 96
    assert first["community_load_kw"].max() == 100.0
    assert first["community_load_kw"].sum() > 0

    dr_a = tmp_path / "dr-a.parquet"
    dr_b = tmp_path / "dr-b.parquet"
    kwargs = {
        "days": 3,
        "reductions": [0.1, 0.2, 0.3],
        "durations": [15, 30, 60],
        "notices": [0, 5, 15],
        "seed": 13,
    }
    generate_dr_events(community_a, dr_a, **kwargs)
    generate_dr_events(community_a, dr_b, **kwargs)
    dr_first = pd.read_parquet(dr_a)
    pd.testing.assert_frame_equal(dr_first, pd.read_parquet(dr_b))
    assert tuple(dr_first.columns[: len(DR_COLUMNS)]) == DR_COLUMNS
    assert len(dr_first) >= 3
    assert (dr_first["end_time"] > dr_first["start_time"]).all()

    manifest_path = tmp_path / "split.yaml"
    manifest = create_split_manifest({"community": community_a, "dr": dr_a}, manifest_path, seed=42)
    datasets = manifest["datasets"]
    assert isinstance(datasets, dict)
    community_splits = datasets["community"]["splits"]
    assert community_splits["train"]["end"] < community_splits["validation"]["start"]
    assert community_splits["validation"]["end"] < community_splits["test"]["start"]
    validation = validate_manifest(manifest_path)
    assert validation["valid"] is True


def test_eulp_catalog_allows_configurable_profiles_and_mixtures(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    timestamps = pd.date_range("2018-01-01 00:15:00", periods=4, freq="15min")
    residential = raw_dir / "res.csv"
    commercial = raw_dir / "com.csv"
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "in.ashrae_iecc_climate_zone_2004": "3A",
            "in.geometry_building_type_recs": "Single-Family Detached",
            "out.electricity.total.energy_consumption..kwh": [10, 20, 30, 40],
            "out.electricity.pv.energy_consumption..kwh": [0, -1, -2, 0],
            "out.electricity.net.energy_consumption..kwh": [10, 19, 28, 40],
        }
    ).to_csv(residential, index=False)
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "in.ashrae_iecc_climate_zone_2006": "3A",
            "in.comstock_building_type": "SmallOffice",
            "out.electricity.total.energy_consumption.kwh": [40, 30, 20, 10],
            "out.electricity.pv.energy_consumption.kwh": [0, 0, 0, 0],
            "out.electricity.net.energy_consumption.kwh": [40, 30, 20, 10],
        }
    ).to_csv(commercial, index=False)
    catalog = tmp_path / "catalog.yaml"
    catalog_community_profiles(str(raw_dir / "*.csv"), catalog)
    selectable = list_community_profiles(catalog)
    assert {entry["profile_id"] for entry in selectable} == {
        "eulp_resstock_3a_single_family_detached",
        "eulp_comstock_3a_smalloffice",
    }

    residential_only = tmp_path / "residential.parquet"
    preprocess_community_profiles(
        catalog,
        residential_only,
        profiles=["eulp_resstock_3a_single_family_detached"],
        peak_kw=100,
    )
    selected = pd.read_parquet(residential_only)
    assert selected["profile_id"].unique().tolist() == ["eulp_resstock_3a_single_family_detached"]
    assert selected["community_load_kw"].max() == 100

    mixed_output = tmp_path / "mixed.parquet"
    preprocess_community_profiles(catalog, mixed_output, include_mixed=True, peak_kw=100)
    mixed = pd.read_parquet(mixed_output)
    assert set(mixed["profile_id"].unique()) == {
        "eulp_resstock_3a_single_family_detached",
        "eulp_comstock_3a_smalloffice",
        "eulp_mixed_3a",
    }
    assert len(mixed) == 12
    assert mixed.groupby("profile_id")["community_load_kw"].max().eq(100).all()


def test_eulp_catalog_disambiguates_same_zone_location_files(tmp_path: Path) -> None:
    timestamps = pd.date_range("2018-01-01 00:15:00", periods=2, freq="15min")
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "in.ashrae_iecc_climate_zone_2004": "5A",
            "in.geometry_building_type_recs": "Single-Family Detached",
            "out.electricity.total.energy_consumption..kwh": [10, 20],
            "out.electricity.pv.energy_consumption..kwh": [0, 0],
            "out.electricity.net.energy_consumption..kwh": [10, 20],
        }
    )
    frame.to_csv(tmp_path / "location-alpha.csv", index=False)
    frame.to_csv(tmp_path / "location-beta.csv", index=False)
    catalog = tmp_path / "catalog.yaml"

    catalog_community_profiles(str(tmp_path / "location-*.csv"), catalog)
    selectable = list_community_profiles(catalog)
    profile_ids = [str(entry["profile_id"]) for entry in selectable]

    assert len(profile_ids) == 2
    assert len(set(profile_ids)) == 2
    assert all(
        profile_id.startswith("eulp_resstock_5a_single_family_detached_")
        for profile_id in profile_ids
    )
    assert {Path(str(entry["path"])).name for entry in selectable} == {
        "location-alpha.csv",
        "location-beta.csv",
    }


def test_source_manifest_checks_hash_and_size(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_bytes(b"source-data\n")
    from aidrbench.data.splits import sha256_file

    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        "files:\n"
        f"  - local_path: {source}\n"
        f"    sha256: {sha256_file(source)}\n"
        f"    bytes: {source.stat().st_size}\n",
        encoding="utf-8",
    )
    assert validate_source_manifest(manifest)["valid"] is True
    source.write_bytes(b"changed\n")
    assert validate_source_manifest(manifest)["valid"] is False
