"""Export the exact, post-filter data values displayed in every manuscript panel."""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from aidrbench.evaluation.nature_figures import (
    _bool_series,
    _calibration_run_groups,
    _float,
    _int,
    _load_manifest,
    _numeric,
    _verified_table,
)

_SCHEMA_VERSION = "aidrbench.figure_panel_plot_data.v1"
_DISPLAY_DURATION_GRID = tuple(range(1, 9))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_panel(
    destination: Path,
    *,
    figure: str,
    panel: str,
    frame: pd.DataFrame,
    source_tables: tuple[str, ...],
    selection: str,
    transformation: str,
) -> dict[str, object]:
    if frame.empty:
        raise ValueError(f"{figure}{panel}: exact panel plot data must not be empty")
    output = f"figure_{figure.lower()}_panel_{panel}.csv"
    path = destination / output
    exported = frame.reset_index(drop=True).copy()
    exported.to_csv(
        path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        float_format="%.12g",
    )
    return {
        "figure": figure,
        "panel": panel,
        "output": output,
        "output_sha256": _sha256(path),
        "row_count": int(len(exported)),
        "columns": list(exported.columns),
        "source_tables": list(source_tables),
        "selection": selection,
        "transformation": transformation,
    }


def _write_manifest(destination: Path, records: list[dict[str, object]]) -> dict[str, object]:
    manifest = {
        "schema_version": _SCHEMA_VERSION,
        "panel_table_count": len(records),
        "panels": records,
    }
    path = destination / "panel_plot_data_manifest.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _prepare_destination(destination: Path) -> None:
    """Require a fresh panel-data directory so obsolete figure files cannot survive."""

    if destination.exists():
        if not destination.is_dir():
            raise FileExistsError(f"panel-data destination is not a directory: {destination}")
        if any(destination.iterdir()):
            raise FileExistsError(
                f"panel-data destination must be empty to prevent stale files: {destination}"
            )
    destination.mkdir(parents=True, exist_ok=True)


def _complete_duration_display_grid(
    frame: pd.DataFrame,
    *,
    group_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Expose the full 1--8 h display axis without inventing missing results.

    The frozen mainline evaluated H={1,2,3,4,6,8}.  Reindexing panel exports
    makes the two unevaluated integer hours explicit to a reader while keeping
    their numerical cells empty.  Renderers still draw only computed rows.
    """

    if "duration_h" not in frame.columns:
        raise ValueError("duration display grid requires a duration_h column")
    source = frame.copy()
    source["duration_h"] = _numeric(source, "duration_h").astype(int)
    frames: list[pd.DataFrame] = []
    grouped_frames: list[tuple[object, pd.DataFrame]]
    if group_columns:
        grouped_frames = [
            (key, selected)
            for key, selected in source.groupby(
                list(group_columns),
                sort=True,
                dropna=False,
            )
        ]
    else:
        grouped_frames = [((), source)]
    for raw_key, selected in grouped_frames:
        keys = raw_key if isinstance(raw_key, tuple) else (raw_key,)
        evaluated = set(_numeric(selected, "duration_h").astype(int))
        completed = selected.set_index("duration_h").reindex(_DISPLAY_DURATION_GRID)
        for column, value in zip(group_columns, keys, strict=True):
            completed[column] = value
        completed.index.name = "duration_h"
        completed = completed.reset_index()
        completed["duration_grid_status"] = [
            "evaluated" if duration in evaluated else "not_evaluated"
            for duration in _DISPLAY_DURATION_GRID
        ]
        completed["value_origin"] = [
            "computed_original_mainline"
            if duration in evaluated
            else "no_value_no_interpolation"
            for duration in _DISPLAY_DURATION_GRID
        ]
        frames.append(completed)
    ordered = pd.concat(frames, ignore_index=True)
    base_columns = list(frame.columns)
    return ordered[
        [*base_columns, "duration_grid_status", "value_origin"]
    ].sort_values([*group_columns, "duration_h"])


def _supplementary_s5_source(
    specification: dict[str, object],
    *,
    repository_root: Path,
) -> tuple[Path, dict[str, object], dict[str, str]]:
    """Resolve the hash-verified source bundle declared for external S5 artwork."""

    raw_external = specification.get("external_artwork")
    if not isinstance(raw_external, dict) or set(raw_external) != {"S5"}:
        raise ValueError("supplementary specification must declare external_artwork.S5")
    raw_s5 = raw_external["S5"]
    if not isinstance(raw_s5, dict):
        raise ValueError("external_artwork.S5 must be a mapping")
    if raw_s5.get("renderer") != "web_gpt":
        raise ValueError("Supplementary Figure S5 must use the declared Web-GPT route")
    if raw_s5.get("locked_sets_used") is not False:
        raise ValueError("Supplementary Figure S5 must remain non-locked")
    if raw_s5.get("evidence_scope") != "paired_development_profile_sensitivity":
        raise ValueError("Supplementary Figure S5 evidence scope mismatch")

    raw_source = raw_s5.get("source_data_directory")
    if not isinstance(raw_source, str) or not raw_source:
        raise ValueError("external_artwork.S5.source_data_directory must be a path")
    source = (repository_root / raw_source).resolve()
    try:
        source.relative_to(repository_root)
    except ValueError as error:
        raise ValueError("Supplementary Figure S5 source bundle escapes repository root") from error
    if "locked" in source.as_posix().lower():
        raise ValueError("Supplementary Figure S5 must not read a locked source-data path")

    _manifest_path, loaded_manifest = _load_manifest(source)
    manifest: dict[str, object] = dict(loaded_manifest)
    expected_bundle = raw_s5.get("expected_bundle_id")
    if not isinstance(expected_bundle, str) or manifest.get("bundle_id") != expected_bundle:
        raise ValueError("Supplementary Figure S5 source-data bundle identity mismatch")

    raw_table_ids = raw_s5.get("source_table_ids")
    if not isinstance(raw_table_ids, dict):
        raise ValueError("external_artwork.S5.source_table_ids must be a mapping")
    required_roles = {
        "representative_curves",
        "pi_firm_boundaries",
        "causal_transfer",
        "pv_hosting_summary",
    }
    if set(raw_table_ids) != required_roles or not all(
        isinstance(value, str) and bool(value) for value in raw_table_ids.values()
    ):
        raise ValueError("Supplementary Figure S5 source-table declaration mismatch")
    return source, manifest, {
        str(role): str(table_id) for role, table_id in raw_table_ids.items()
    }


def export_main_figure_panel_plot_data(
    source_data_directory: str | Path,
    output_directory: str | Path,
) -> dict[str, object]:
    """Export one human-auditable CSV for every quantitative main-figure panel."""

    source = Path(source_data_directory).resolve()
    destination = Path(output_directory).resolve()
    _prepare_destination(destination)
    _manifest_path, manifest = _load_manifest(source)
    def table(table_id: str) -> pd.DataFrame:
        return _verified_table(source, manifest, table_id)
    records: list[dict[str, object]] = []

    pi = table("fig1_fig2_pi_firm_boundaries")
    q95_pi = pi[np.isclose(_numeric(pi, "reliability_target"), 0.95)].copy()
    q95_pi = q95_pi.sort_values("duration_h")
    q95_pi["overstatement_percent_of_nominal"] = 100.0 * (
        _numeric(q95_pi, "nominal_flexibility_kw")
        - _numeric(q95_pi, "perfect_information_firm_capacity_kw")
    ) / _numeric(q95_pi, "nominal_flexibility_kw")
    q95_pi_display = _complete_duration_display_grid(q95_pi)
    records.append(
        _write_panel(
            destination,
            figure="1",
            panel="b",
            frame=q95_pi_display[
                [
                    "duration_h",
                    "reliability_target",
                    "confidence_level",
                    "scenario_count",
                    "nominal_flexibility_kw",
                    "perfect_information_firm_capacity_kw",
                    "physical_gap_kw",
                    "overstatement_percent_of_nominal",
                    "duration_grid_status",
                    "value_origin",
                ]
            ],
            source_tables=("fig1_fig2_pi_firm_boundaries",),
            selection="reliability_target == 0.95; complete 1-8 h display grid",
            transformation="overstatement = 100 * (nominal - PI tolerance lower bound) / nominal; H=5 and H=7 are explicit not_evaluated rows with no interpolation",
        )
    )

    calibration = table("fig1_calibration_run_means").copy()
    for mode in ("training", "offline_inference"):
        for gpu_count in (1, 4):
            _calibration_run_groups(calibration, mode=mode, gpu_count=gpu_count)
    calibration["run_mean_power_w"] = calibration.groupby(
        ["mode", "gpu_count", "repeat"]
    )["mean_power_w"].transform("mean")
    calibration["calibration_role"] = np.where(
        _numeric(calibration, "repeat") == 3,
        "held_out",
        "fit",
    )
    records.append(
        _write_panel(
            destination,
            figure="1",
            panel="c",
            frame=calibration.sort_values(["mode", "gpu_count", "repeat", "gpu_index"]),
            source_tables=("fig1_calibration_run_means",),
            selection="all 30 per-board observations",
            transformation="dots are per-board means; short bars are within-run means",
        )
    )

    na = table("fig2_restricted_na_surface")
    certificates = table("fig2_fig5_locked_id_certificates")
    q95_na = na[
        np.isclose(_numeric(na, "ensemble_success_fraction_target"), 0.95)
        & np.isclose(_numeric(na, "notice_h"), 0)
    ].copy()
    q95_cert = certificates[
        np.isclose(_numeric(certificates, "reliability_target"), 0.95)
        & np.isclose(_numeric(certificates, "notice_h"), 0)
    ].copy()
    figure2a = q95_pi[
        [
            "duration_h",
            "nominal_flexibility_kw",
            "perfect_information_firm_capacity_kw",
        ]
    ].merge(
        q95_na[["duration_h", "non_anticipative_capacity_kw"]],
        on="duration_h",
        validate="one_to_one",
    )
    figure2a = figure2a.merge(
        q95_cert[["duration_h", "candidate_reduction_kw", "certified"]],
        on="duration_h",
        validate="one_to_one",
    ).sort_values("duration_h")
    figure2a = _complete_duration_display_grid(figure2a)
    records.append(
        _write_panel(
            destination,
            figure="2",
            panel="a",
            frame=figure2a,
            source_tables=(
                "fig1_fig2_pi_firm_boundaries",
                "fig2_restricted_na_surface",
                "fig2_fig5_locked_id_certificates",
            ),
            selection="q == 0.95 and notice == 0 h; complete 1-8 h display grid",
            transformation="duration-keyed one-to-one merge; no averaging; H=5 and H=7 are explicit not_evaluated rows with no interpolation",
        )
    )
    figure2b = certificates[
        np.isclose(_numeric(certificates, "notice_h"), 0)
        & _numeric(certificates, "reliability_target").isin([0.90, 0.95, 0.99])
    ].sort_values(["reliability_target", "duration_h"])
    figure2b = _complete_duration_display_grid(
        figure2b,
        group_columns=("reliability_target",),
    )
    records.append(
        _write_panel(
            destination,
            figure="2",
            panel="b",
            frame=figure2b,
            source_tables=("fig2_fig5_locked_id_certificates",),
            selection="notice == 0 h and q in {0.90, 0.95, 0.99}; complete 1-8 h display grid",
            transformation="filled marker if certified; open marker otherwise; H=5 and H=7 are explicit not_evaluated rows with no interpolation",
        )
    )
    diagnostics = table("fig2_notice_mechanism_diagnostics")
    figure2c = diagnostics[
        np.isclose(_numeric(diagnostics, "notice_h"), 6)
    ].sort_values("duration_h")
    records.append(
        _write_panel(
            destination,
            figure="2",
            panel="c",
            frame=figure2c,
            source_tables=("fig2_notice_mechanism_diagnostics",),
            selection="notice == 6 h; durations H in {4, 8}",
            transformation="bars show scenario means; text shows NA notice gain",
        )
    )

    event = table("fig3_exhaustion_event_summary")
    figure3ab = (
        event.groupby(["evaluation_split", "duration_h", "event_ordinal"], as_index=False)
        .agg(
            mean_paired_compute_debt_increment_kwh=(
                "mean_paired_compute_debt_increment_kwh",
                "mean",
            ),
            fixed_commitment_residual_flexibility_ratio=(
                "fixed_commitment_residual_flexibility_ratio",
                "mean",
            ),
            recovery_gap_condition_count=("recovery_gap_h", "nunique"),
            scenarios_per_condition=("scenario_count", "min"),
        )
        .sort_values(["evaluation_split", "duration_h", "event_ordinal"])
    )
    figure3ab["mean_paired_compute_debt_increment_mwh"] = (
        figure3ab["mean_paired_compute_debt_increment_kwh"] / 1000.0
    )
    records.append(
        _write_panel(
            destination,
            figure="3",
            panel="a_b",
            frame=figure3ab,
            source_tables=("fig3_exhaustion_event_summary",),
            selection="development and validation; H in {4, 8}; event ordinal 1-4",
            transformation="arithmetic mean over five recovery-gap conditions; kWh divided by 1000 for MWh axis",
        )
    )
    joint = table("fig3_exhaustion_joint_episode_summary")
    for panel, split in (("c", "development"), ("d", "validation")):
        records.append(
            _write_panel(
                destination,
                figure="3",
                panel=panel,
                frame=joint[joint["evaluation_split"] == split].sort_values(
                    ["duration_h", "recovery_gap_h"]
                ),
                source_tables=("fig3_exhaustion_joint_episode_summary",),
                selection=f"evaluation_split == {split}",
                transformation="heatmap cell is joint_episode_success_fraction; no interpolation",
            )
        )

    pv_hosting = table("fig4_pv_hosting_summary")
    figure4a = pv_hosting[
        (pv_hosting["evaluation_split"] == "validation")
        & (pv_hosting["analysis_variant"] == "headline_pv_hosting_envelope")
    ].copy()
    feasible = _bool_series(figure4a["all_scenarios_feasible"]).to_numpy(dtype=bool)
    figure4a["display_pv_hosting_kw"] = np.where(
        feasible,
        _numeric(figure4a, "simultaneous_feasible_pv_hosting_kw"),
        _numeric(figure4a, "minimum_scenario_pv_hosting_kw"),
    )
    figure4a["display_marker"] = np.where(feasible, "filled_all_scenarios", "open_partial")
    records.append(
        _write_panel(
            destination,
            figure="4",
            panel="a",
            frame=figure4a.sort_values(
                ["dc_operation", "bess_enabled", "dc_scale_of_reference_mix"]
            ),
            source_tables=("fig4_pv_hosting_summary",),
            selection="validation and headline_pv_hosting_envelope",
            transformation="all-feasible cells plot simultaneous boundary; partial cells plot minimum-scenario boundary as open markers",
        )
    )
    pv_gains = table("fig4_pv_hosting_contrasts")
    records.append(
        _write_panel(
            destination,
            figure="4",
            panel="b",
            frame=pv_gains.sort_values(["evaluation_split", "conditioning_level"]),
            source_tables=("fig4_pv_hosting_contrasts",),
            selection="all four precomputed contrasts at DC scale 1.0",
            transformation="point = paired mean; whisker = Bonferroni 95% simultaneous bootstrap CI",
        )
    )
    operation = table("fig4_pv_operation_contrasts")
    metrics = ["total_pv_curtailed_kwh", "pv_utilisation_fraction", "total_grid_import_kwh"]
    figure4c = operation[
        (operation["evaluation_split"] == "validation")
        & operation["metric"].isin(metrics)
    ].copy()
    figure4c["display_scale"] = np.where(
        figure4c["metric"] == "pv_utilisation_fraction", 100.0, 1.0
    )
    for column in ("estimate_mean", "simultaneous_ci_lower", "simultaneous_ci_upper"):
        figure4c[f"display_{column}"] = _numeric(figure4c, column) * figure4c["display_scale"]
    records.append(
        _write_panel(
            destination,
            figure="4",
            panel="c",
            frame=figure4c.sort_values(["metric", "conditioning_level"]),
            source_tables=("fig4_pv_operation_contrasts",),
            selection="validation; three displayed metrics; BESS off/on",
            transformation="PV-utilisation fractions multiplied by 100 to percentage points; other metrics remain kWh",
        )
    )
    interactions = table("fig4_hosting_paired_contrasts")
    figure4d = interactions[interactions["contrast"] != "AI_HOSTING_GAIN"].copy()
    records.append(
        _write_panel(
            destination,
            figure="4",
            panel="d",
            frame=figure4d.sort_values(
                ["evaluation_split", "contrast", "conditioning_level"]
            ),
            source_tables=("fig4_hosting_paired_contrasts",),
            selection="all interaction contrasts; AI_HOSTING_GAIN excluded because panel b reports that estimand",
            transformation="point = difference-in-differences; whisker = simultaneous CI; grey band = ± equivalence margin",
        )
    )

    power = table("fig5_power_case_sensitivity")
    figure5a = power[np.isclose(_numeric(power, "reliability_target"), 0.95)].copy()
    figure5a = _complete_duration_display_grid(
        figure5a,
        group_columns=("power_case",),
    )
    records.append(
        _write_panel(
            destination,
            figure="5",
            panel="a",
            frame=figure5a.sort_values(["power_case", "duration_h"]),
            source_tables=("fig5_power_case_sensitivity",),
            selection="q == 0.95; lower, nominal and upper power cases; complete 1-8 h display grid",
            transformation="no aggregation; H=5 and H=7 are explicit not_evaluated rows with no interpolation",
        )
    )
    workload = table("fig5_workload_sensitivity")
    criteria = table("fig5_success_criteria_sensitivity").copy()
    criteria_reference = criteria[criteria["criteria_case"] == "reference"].set_index(
        "duration_h"
    )
    criteria["capacity_delta_kw"] = [
        _float(row.perfect_information_firm_capacity_kw)
        - _float(
            criteria_reference.loc[
                _int(row.duration_h),
                "perfect_information_firm_capacity_kw",
            ]
        )
        for row in criteria.itertuples(index=False)
    ]
    infrastructure = table("fig5_infrastructure_sensitivity")
    ranges: list[dict[str, object]] = []
    for group, frame, case_column, value_column in (
        (
            "Workload",
            workload,
            "workload_case",
            "firm_capacity_delta_from_reference_kw",
        ),
        ("Success criteria", criteria, "criteria_case", "capacity_delta_kw"),
        (
            "Infrastructure",
            infrastructure,
            "infrastructure_case",
            "firm_capacity_delta_from_reference_kw",
        ),
    ):
        for duration_h in (4, 8):
            selected = frame[
                (~frame[case_column].astype(str).eq("reference"))
                & np.isclose(_numeric(frame, "duration_h"), duration_h)
            ].copy()
            values = _numeric(selected, value_column)
            minimum_index = values.idxmin()
            maximum_index = values.idxmax()
            ranges.append(
                {
                    "sensitivity_group": group,
                    "duration_h": duration_h,
                    "minimum_capacity_delta_kw": _float(values.loc[minimum_index]),
                    "minimum_case": str(selected.loc[minimum_index, case_column]),
                    "maximum_capacity_delta_kw": _float(values.loc[maximum_index]),
                    "maximum_case": str(selected.loc[maximum_index, case_column]),
                    "non_reference_case_count": int(len(selected)),
                }
            )
    records.append(
        _write_panel(
            destination,
            figure="5",
            panel="b",
            frame=pd.DataFrame.from_records(ranges),
            source_tables=(
                "fig5_workload_sensitivity",
                "fig5_success_criteria_sensitivity",
                "fig5_infrastructure_sensitivity",
            ),
            selection="H in {4, 8}; all non-reference cases in each predeclared family",
            transformation="segment endpoints are the minimum and maximum capacity deltas; endpoint case names are retained",
        )
    )
    locked_id = certificates[
        np.isclose(_numeric(certificates, "reliability_target"), 0.95)
        & np.isclose(_numeric(certificates, "notice_h"), 0)
    ].copy()
    locked_ood_table = table("fig5_locked_ood_certificates")
    locked_ood = locked_ood_table[
        np.isclose(_numeric(locked_ood_table, "reliability_target"), 0.95)
        & np.isclose(_numeric(locked_ood_table, "notice_h"), 0)
    ].copy()
    figure5c = locked_id.merge(
        locked_ood,
        on=["duration_h", "notice_h", "reliability_target", "candidate_reduction_kw"],
        suffixes=("_locked_id", "_locked_ood"),
        validate="one_to_one",
    ).sort_values("duration_h")
    figure5c = _complete_duration_display_grid(figure5c)
    records.append(
        _write_panel(
            destination,
            figure="5",
            panel="c",
            frame=figure5c,
            source_tables=("fig2_fig5_locked_id_certificates", "fig5_locked_ood_certificates"),
            selection="q == 0.95 and notice == 0 h; matched by duration and fixed candidate; complete 1-8 h display grid",
            transformation="one-to-one ID/OOD merge; plotted y values are one-sided 95% Wilson lower bounds; H=5 and H=7 are explicit not_evaluated rows with no interpolation",
        )
    )

    return _write_manifest(destination, records)


def export_supplementary_panel_plot_data(
    source_data_directory: str | Path,
    specification_path: str | Path,
    output_directory: str | Path,
    *,
    repository_root: str | Path = ".",
) -> dict[str, object]:
    """Export exact plot data for all quantitative Supplementary Figure panels."""

    source = Path(source_data_directory).resolve()
    root = Path(repository_root).resolve()
    destination = Path(output_directory).resolve()
    _prepare_destination(destination)
    specification = yaml.safe_load(Path(specification_path).read_text(encoding="utf-8"))
    if not isinstance(specification, dict):
        raise ValueError("supplementary figure specification must be a mapping")
    records: list[dict[str, object]] = []

    calibration = pd.read_csv(source / "supplementary_figure_2_calibration.csv")
    calibration["run_mean_power_w"] = calibration.groupby(
        ["mode", "gpu_count", "repeat"]
    )["mean_power_w"].transform("mean")
    calibration["calibration_role"] = np.where(
        _numeric(calibration, "repeat") == 3,
        "held_out",
        "fit",
    )
    records.append(
        _write_panel(
            destination,
            figure="S2",
            panel="a",
            frame=calibration.sort_values(["mode", "gpu_count", "repeat", "gpu_index"]),
            source_tables=("supplementary_figure_2_calibration.csv",),
            selection="all 30 per-board observations",
            transformation="dots are per-board means; short bars are within-run means",
        )
    )
    calibration_spec = specification.get("calibration")
    if not isinstance(calibration_spec, dict):
        raise ValueError("supplementary calibration specification must be a mapping")
    artifact_path = root / str(calibration_spec["artifact"])
    artifact = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    active = artifact["parameters"]["active_power_w_per_gpu_by_class"]
    validation = artifact["validation"]
    parameter_rows: list[dict[str, object]] = []
    for workload_class in ("training", "offline_inference"):
        entry = active[workload_class]
        parameter_rows.append(
            {
                "workload_class": workload_class,
                "estimate_w_per_gpu": entry["estimate_w"],
                "interval_lower_w_per_gpu": entry["uncertainty_interval_w"][0],
                "interval_upper_w_per_gpu": entry["uncertainty_interval_w"][1],
                "confidence_level": entry["confidence_level"],
                "statistical_unit": entry["statistical_unit"],
                "independent_run_count": entry["independent_unit_count"],
                "held_out_overall_mae_w_per_gpu": validation["held_out_power_mae_w"],
            }
        )
    records.append(
        _write_panel(
            destination,
            figure="S2",
            panel="b",
            frame=pd.DataFrame.from_records(parameter_rows),
            source_tables=(str(calibration_spec["artifact"]),),
            selection="training and offline-inference active-power parameters",
            transformation="error bars are the stored Student-t 95% intervals over two fit run means",
        )
    )

    observation = pd.read_csv(source / "supplementary_figure_3_observation.csv")
    counts = (
        observation.groupby("observation_group", sort=False)
        .size()
        .rename("dimension_count")
        .reset_index()
    )
    records.append(
        _write_panel(
            destination,
            figure="S3",
            panel="a",
            frame=counts,
            source_tables=("supplementary_figure_3_observation.csv",),
            selection="all 63 policy-observation features",
            transformation="bar length is the feature count within each declared observation group",
        )
    )

    trajectory = pd.read_csv(source / "supplementary_figure_4_trajectory.csv")
    metadata = json.loads(
        (source / "representative_trajectory_metadata.json").read_text(encoding="utf-8")
    )
    start = int(metadata["event_start_hour"])
    stop = int(metadata["event_stop_hour"])
    pre = int(metadata.get("plot_window_pre_event_h", 12))
    post = int(metadata.get("plot_window_post_event_h", 24))
    required_columns = {"relative_hour", "hour"}
    missing_columns = sorted(required_columns.difference(trajectory.columns))
    if missing_columns:
        raise ValueError(
            "Supplementary Figure S4 plot data are missing columns: "
            + ", ".join(missing_columns)
        )
    observed_relative_hours = _numeric(trajectory, "relative_hour").to_numpy(dtype=int)
    expected_relative_hours = np.arange(-pre, stop - start + post, dtype=int)
    if not np.array_equal(observed_relative_hours, expected_relative_hours):
        raise ValueError("Supplementary Figure S4 relative-hour window is incomplete")
    absolute_hours = _numeric(trajectory, "hour").to_numpy(dtype=int)
    if not np.array_equal(observed_relative_hours, absolute_hours - start):
        raise ValueError("Supplementary Figure S4 absolute and relative hours disagree")
    records.append(
        _write_panel(
            destination,
            figure="S4",
            panel="a_b_c_d",
            frame=trajectory,
            source_tables=(
                "supplementary_figure_4_trajectory.csv",
                "representative_trajectory_metadata.json",
            ),
            selection="exact stored window from 12 h before event start through 24 h after event stop",
            transformation="no additional filtering; relative_hour equals absolute hour minus event_start_hour and the same rows feed panels a-d",
        )
    )

    s5_source, s5_manifest, s5_table_ids = _supplementary_s5_source(
        specification,
        repository_root=root,
    )

    def s5_table(role: str) -> pd.DataFrame:
        return _verified_table(s5_source, s5_manifest, s5_table_ids[role])

    profiles = s5_table("representative_curves").copy()
    profile_frames: list[pd.DataFrame] = []
    for zone in ("3A", "3C", "5A"):
        selected = profiles[profiles["climate_zone"].astype(str) == zone].copy()
        selected["timestamp"] = pd.to_datetime(selected["timestamp"])
        selected = selected.sort_values("timestamp").head(168)
        if len(selected) != 168:
            raise ValueError(
                f"Supplementary Figure S5a climate zone {zone} needs exactly "
                "168 plotted rows"
            )
        selected["elapsed_hour"] = np.arange(168, dtype=int)
        selected["elapsed_day"] = selected["elapsed_hour"] / 24.0
        profile_frames.append(selected)
    records.append(
        _write_panel(
            destination,
            figure="S5",
            panel="a",
            frame=pd.concat(profile_frames, ignore_index=True),
            source_tables=(s5_table_ids["representative_curves"],),
            selection="earliest 168 chronological hours within each climate zone",
            transformation="timestamp mapped to elapsed hour/day; no smoothing",
        )
    )

    firm = _complete_duration_display_grid(
        s5_table("pi_firm_boundaries"),
        group_columns=("climate_zone",),
    )
    records.append(
        _write_panel(
            destination,
            figure="S5",
            panel="b",
            frame=firm.sort_values(["climate_zone", "duration_h"]),
            source_tables=(s5_table_ids["pi_firm_boundaries"],),
            selection="all three climate zones and complete 1-8 h display grid at q == 0.95",
            transformation="no aggregation; maximum spread annotation is max(zone) - min(zone) within evaluated duration; H=5 and H=7 are explicit not_evaluated rows with no interpolation",
        )
    )

    causal = s5_table("causal_transfer")
    records.append(
        _write_panel(
            destination,
            figure="S5",
            panel="c",
            frame=causal.sort_values(["climate_zone", "duration_h"]),
            source_tables=(s5_table_ids["causal_transfer"],),
            selection="all three climate zones; H in {4, 8}",
            transformation="filled marker = empirical success; open marker = Wilson lower bound",
        )
    )

    hosting = s5_table("pv_hosting_summary")
    records.append(
        _write_panel(
            destination,
            figure="S5",
            panel="d",
            frame=hosting.sort_values(
                ["bess_enabled", "climate_zone", "dc_operation"]
            ),
            source_tables=(s5_table_ids["pv_hosting_summary"],),
            selection="complete 3 climate zone × 2 BESS × 2 operation design",
            transformation="open marker = rigid; filled marker = flexible; connecting segment is the paired planning gain",
        )
    )

    return _write_manifest(destination, records)
