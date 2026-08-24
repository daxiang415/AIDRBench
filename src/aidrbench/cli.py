"""AIDRBench command-line interface."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from aidrbench._version import __version__
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.project_check import check_project, format_report


def _add_data_parsers(subparsers: Any) -> None:
    data = subparsers.add_parser("data", help="prepare and validate formal datasets")
    commands = data.add_subparsers(dest="data_command")

    alibaba_summary = commands.add_parser(
        "preprocess-alibaba-summary",
        help="normalize Alibaba GPU v2026 Lite job summary data",
    )
    alibaba_summary.add_argument("--input", required=True)
    alibaba_summary.add_argument("--output", required=True)
    alibaba_summary.add_argument("--winsorize-quantile", type=float, default=0.995)

    alibaba_arrivals = commands.add_parser(
        "make-alibaba-lite-arrivals",
        help="build a scaled Alibaba-2026-calibrated synthetic hourly scenario",
    )
    alibaba_arrivals.add_argument("--config", required=True)
    alibaba_arrivals.add_argument("--output", required=True)
    alibaba_arrivals.add_argument("--hours", type=int)
    alibaba_arrivals.add_argument("--seed", type=int, default=1)

    alibaba_sampler = commands.add_parser(
        "make-alibaba-lite-sampler",
        help="stream a bounded empirical sampler pool from the Alibaba 2026 summary",
    )
    alibaba_sampler.add_argument("--input", required=True)
    alibaba_sampler.add_argument("--output", required=True)
    alibaba_sampler.add_argument(
        "--job-classes", nargs="+", default=("training", "offline_inference")
    )
    alibaba_sampler.add_argument("--priorities", nargs="+", default=("lp",))
    alibaba_sampler.add_argument("--rows-per-stratum", type=int, default=50_000)
    alibaba_sampler.add_argument("--seed", type=int, default=2026)

    community = commands.add_parser(
        "make-synthetic-community", help="create a deterministic smoke profile"
    )
    community.add_argument("--days", type=int, default=30)
    community.add_argument("--resolution-seconds", type=int, default=900)
    community.add_argument("--peak-kw", type=float, default=100.0)
    community.add_argument("--seed", type=int, default=42)
    community.add_argument("--output", required=True)

    catalog = commands.add_parser(
        "catalog-community", help="discover selectable downloaded EULP profiles"
    )
    catalog.add_argument("--input", required=True)
    catalog.add_argument("--output", required=True)

    list_profiles = commands.add_parser(
        "list-community-profiles", help="list profile IDs available to benchmark configs"
    )
    list_profiles.add_argument("--catalog", required=True)

    real_community = commands.add_parser(
        "preprocess-community", help="prepare selected real EULP profiles"
    )
    real_community.add_argument("--catalog", required=True)
    real_community.add_argument("--profile", action="append")
    real_community.add_argument("--peak-kw", type=float, default=100.0)
    real_community.add_argument("--include-mixed", action="store_true")
    real_community.add_argument("--commercial-weight", type=float, default=0.25)
    real_community.add_argument("--output", required=True)

    dr = commands.add_parser("generate-dr-events", help="create a deterministic DR manifest")
    dr.add_argument("--community", required=True)
    dr.add_argument("--days", type=int, required=True)
    dr.add_argument("--reductions", type=float, nargs="+", required=True)
    dr.add_argument("--durations", type=int, nargs="+", required=True)
    dr.add_argument("--notices", type=int, nargs="+", required=True)
    dr.add_argument("--seed", type=int, default=42)
    dr.add_argument("--profile-id")
    dr.add_argument("--align-minutes", type=int)
    dr.add_argument("--output", required=True)

    split = commands.add_parser("create-split-manifest", help="hash chronological datasets")
    split.add_argument("--dataset", action="append", required=True, metavar="NAME=PATH")
    split.add_argument("--seed", type=int, default=42)
    split.add_argument("--output", required=True)

    validate = commands.add_parser("validate", help="validate hashes in a split manifest")
    validate.add_argument("--manifest", required=True)

    validate_sources = commands.add_parser(
        "validate-sources", help="re-hash external raw files in a source manifest"
    )
    validate_sources.add_argument("--manifest", required=True)

    preprocess = commands.add_parser("preprocess", help="run one configs/data YAML file")
    preprocess.add_argument("--config", required=True)


def _add_calibration_parsers(subparsers: Any) -> None:
    calibration = subparsers.add_parser("calibrate", help="validate hardware calibration")
    commands = calibration.add_subparsers(dest="calibration_command")

    validate_artifact = commands.add_parser(
        "validate-artifact",
        help="verify a hardware calibration artifact's schema, checksum, and provenance",
    )
    validate_artifact.add_argument("--artifact", required=True)

    telemetry = commands.add_parser(
        "collect-telemetry", help="collect read-only nvidia-smi telemetry to Parquet"
    )
    telemetry.add_argument("--output", required=True)
    telemetry.add_argument("--duration-seconds", type=float, required=True)
    telemetry.add_argument("--interval-seconds", type=float, default=1.0)
    telemetry.add_argument("--gpu-id", type=int, action="append")
    telemetry.add_argument("--nvidia-smi", default="nvidia-smi", dest="nvidia_smi")



def _add_hourly_environment_parsers(subparsers: Any) -> None:
    environment = subparsers.add_parser("env", help="inspect the hourly Gymnasium environments")
    commands = environment.add_subparsers(dest="env_command")
    check = commands.add_parser("check", help="run Gymnasium check_env on one hourly config")
    check.add_argument("--config", required=True)

    rollout = subparsers.add_parser("rollout", help="run one hourly baseline episode")
    rollout.add_argument(
        "--controller",
        choices=("no_control", "threshold", "edf_valley", "mpc", "robust_mpc", "oracle"),
        required=True,
    )
    rollout.add_argument(
        "--scenario",
        default="synthetic_week_001",
        help="human-readable scenario label recorded with the output",
    )
    rollout.add_argument("--config", default="configs/env/hourly_continuous.yaml")
    rollout.add_argument("--seed", type=int, default=1)
    rollout.add_argument("--save", required=True)


def _add_scenario_parsers(subparsers: Any) -> None:
    scenario = subparsers.add_parser(
        "scenario", help="freeze and inspect immutable hourly exogenous scenarios"
    )
    commands = scenario.add_subparsers(dest="scenario_command")
    freeze = commands.add_parser(
        "freeze",
        help="materialize hash-verified community, workload, event, and baseline artifacts",
    )
    freeze.add_argument("--config", required=True)
    freeze.add_argument("--seeds", nargs="+", type=int, required=True)
    freeze.add_argument(
        "--calibration-power-case",
        choices=("lower_bound", "nominal", "upper_bound"),
        help="override only the declared calibration uncertainty case before freezing",
    )
    freeze.add_argument("--preregistration-manifest")
    freeze.add_argument("--unlock-locked-ood", action="store_true")
    freeze.add_argument("--acknowledge-one-time-locked-use", action="store_true")
    freeze.add_argument("--output", required=True)
    freeze_exhaustion = commands.add_parser(
        "freeze-exhaustion",
        help="freeze preregistered development/validation repeated-event programs",
    )
    freeze_exhaustion.add_argument("--specification", required=True)
    freeze_exhaustion.add_argument("--seeds", nargs="+", type=int, required=True)
    freeze_exhaustion.add_argument("--output", required=True)
    inspect = commands.add_parser(
        "inspect", help="verify one frozen scenario and display its provenance"
    )
    inspect.add_argument("--input", required=True)
    sensitivity_check = commands.add_parser(
        "check-sensitivities",
        help="gate a sparse sensitivity design on no-DR service feasibility",
    )
    sensitivity_check.add_argument("--specification", required=True)
    sensitivity_check.add_argument("--seeds", nargs="+", type=int, required=True)
    sensitivity_check.add_argument("--output", required=True)
    infrastructure_check = commands.add_parser(
        "check-infrastructure-sensitivities",
        help="gate sparse PUE/node-overhead cases on no-DR service feasibility",
    )
    infrastructure_check.add_argument("--specification", required=True)
    infrastructure_check.add_argument("--seeds", nargs="+", type=int, required=True)
    infrastructure_check.add_argument("--output", required=True)
    freeze_sensitivities = commands.add_parser(
        "freeze-sensitivities",
        help="freeze paired development scenarios for a sparse workload design",
    )
    freeze_sensitivities.add_argument("--specification", required=True)
    freeze_sensitivities.add_argument("--output", required=True)
    freeze_infrastructure = commands.add_parser(
        "freeze-infrastructure-sensitivities",
        help="freeze paired development scenarios for sparse infrastructure cases",
    )
    freeze_infrastructure.add_argument("--specification", required=True)
    freeze_infrastructure.add_argument("--output", required=True)


def _add_optimization_parsers(subparsers: Any) -> None:
    optimize = subparsers.add_parser(
        "optimize", help="compute auditable planning bounds on frozen scenarios"
    )
    commands = optimize.add_subparsers(dest="optimization_command")
    frontier = commands.add_parser(
        "pi-frontier",
        help="compute a single-event perfect-information power-duration frontier",
    )
    frontier.add_argument("--scenarios", required=True)
    frontier.add_argument("--durations", nargs="+", type=int, required=True)
    frontier.add_argument("--event-id", type=int, default=0)
    frontier.add_argument("--reliabilities", nargs="+", type=float, default=[])
    frontier.add_argument("--confidence-level", type=float, default=0.95)
    frontier.add_argument("--nominal-flexibility-fraction", type=float, default=0.50)
    frontier.add_argument(
        "--workers",
        type=int,
        default=1,
        help="independent frozen scenarios to solve concurrently (default: 1)",
    )
    frontier.add_argument("--output", required=True)
    criteria_sensitivity = commands.add_parser(
        "criteria-sensitivity",
        help="solve a predeclared one-factor-at-a-time PI success-criteria sensitivity",
    )
    criteria_sensitivity.add_argument("--scenarios", required=True)
    criteria_sensitivity.add_argument("--specification", required=True)
    criteria_sensitivity.add_argument(
        "--workers",
        type=int,
        default=1,
        help="independent frozen scenarios to solve concurrently (default: 1)",
    )
    criteria_sensitivity.add_argument("--output", required=True)
    workload_sensitivity = commands.add_parser(
        "workload-sensitivity",
        help="solve a predeclared paired sparse workload PI sensitivity",
    )
    workload_sensitivity.add_argument("--scenarios", required=True)
    workload_sensitivity.add_argument("--specification", required=True)
    workload_sensitivity.add_argument(
        "--workers",
        type=int,
        default=1,
        help="independent frozen scenarios to solve concurrently (default: 1)",
    )
    workload_sensitivity.add_argument("--output", required=True)
    infrastructure_sensitivity = commands.add_parser(
        "infrastructure-sensitivity",
        help="solve predeclared sparse PUE/node-overhead PI sensitivity",
    )
    infrastructure_sensitivity.add_argument("--scenarios", required=True)
    infrastructure_sensitivity.add_argument("--specification", required=True)
    infrastructure_sensitivity.add_argument(
        "--workers",
        type=int,
        default=1,
        help="independent frozen scenarios to solve concurrently (default: 1)",
    )
    infrastructure_sensitivity.add_argument("--output", required=True)
    non_anticipative = commands.add_parser(
        "non-anticipative-firm",
        help="compute a restricted finite-scenario causal non-anticipative bound",
    )
    non_anticipative.add_argument("--scenarios", required=True)
    non_anticipative.add_argument("--durations", nargs="+", type=int, required=True)
    non_anticipative.add_argument("--notice-hours", nargs="+", type=int, default=[0])
    non_anticipative.add_argument("--event-id", type=int, default=0)
    non_anticipative.add_argument(
        "--ensemble-success-fraction-target",
        "--reliability-target",
        dest="reliability_target",
        type=float,
        default=1.0,
        help="finite optimization-ensemble success fraction; not an OOD certificate",
    )
    non_anticipative.add_argument(
        "--information-structure",
        choices=("common_open_loop", "coarse_observation_partition_tree"),
        default="coarse_observation_partition_tree",
        help=(
            "causal policy restriction; the default bins current net load, a limited "
            "forecast, arrivals and notified DR events"
        ),
    )
    non_anticipative.add_argument("--forecast-horizon-hours", type=int, default=6)
    non_anticipative.add_argument("--power-bin-width-pu", type=float, default=0.10)
    non_anticipative.add_argument("--arrival-bin-width-fraction", type=float, default=0.10)
    non_anticipative.add_argument("--minimum-shared-node-size", type=int, default=2)
    non_anticipative.add_argument(
        "--matched-pi-frontier",
        help=(
            "optional matched PI frontier parquet used only for the same-ensemble "
            "empirical information-restriction gap"
        ),
    )
    non_anticipative.add_argument("--output", required=True)
    merge_non_anticipative = commands.add_parser(
        "merge-non-anticipative",
        help="merge independently solved non-anticipative grid partitions",
    )
    merge_non_anticipative.add_argument("--inputs", nargs="+", required=True)
    merge_non_anticipative.add_argument("--output", required=True)
    notice_diagnostics = commands.add_parser(
        "notice-diagnostics",
        help="combine existing PI/NA bounds with development-only frozen-spec robust MPC",
    )
    notice_diagnostics.add_argument("--scenarios", required=True)
    notice_diagnostics.add_argument("--pi-frontier", required=True)
    notice_diagnostics.add_argument("--na-frontier", required=True)
    notice_diagnostics.add_argument("--na-policies", required=True)
    notice_diagnostics.add_argument("--controller-config", required=True)
    notice_diagnostics.add_argument("--durations", nargs="+", type=int, default=[4, 8])
    notice_diagnostics.add_argument("--notices", nargs="+", type=int, default=[0, 6])
    notice_diagnostics.add_argument("--reliability", type=float, default=0.95)
    notice_diagnostics.add_argument("--workers", type=int, default=1)
    notice_diagnostics.add_argument("--output", required=True)
    exhaustion = commands.add_parser(
        "exhaustion-diagnostics",
        help="evaluate frozen Model A over development/validation repeated-event chains",
    )
    exhaustion.add_argument("--scenarios", required=True)
    exhaustion.add_argument("--specification", required=True)
    exhaustion.add_argument("--workers", type=int, default=1)
    exhaustion.add_argument("--output", required=True)
    hosting = commands.add_parser(
        "hosting-capacity",
        help="compute frozen-scenario absolute-PCC hosting-capacity planning bounds",
    )
    hosting.add_argument("--scenarios", required=True)
    hosting.add_argument("--portfolio", required=True)
    hosting.add_argument(
        "--dc-operation",
        choices=("rigid", "flexible", "matrix"),
        default="matrix",
        help="matrix evaluates the 2 x 2 x 2 rigid/flexible x PV x BESS comparison",
    )
    hosting.add_argument("--output", required=True)
    hosting_ensemble = commands.add_parser(
        "hosting-ensemble",
        help="solve the preregistered scenario-level 2 x 2 x 2 hosting ensemble",
    )
    hosting_ensemble.add_argument("--scenarios", required=True)
    hosting_ensemble.add_argument("--specification", required=True)
    hosting_ensemble.add_argument("--workers", type=int, default=1)
    hosting_ensemble.add_argument("--output", required=True)
    renewable_integration = commands.add_parser(
        "renewable-integration",
        help=(
            "solve the preregistered fixed-DC PV-hosting envelope and "
            "fixed-capacity PV-utilisation study"
        ),
    )
    renewable_integration.add_argument("--scenarios", required=True)
    renewable_integration.add_argument("--specification", required=True)
    renewable_integration.add_argument("--workers", type=int, default=1)
    renewable_integration.add_argument("--output", required=True)


def _add_protocol_parser(subparsers: Any) -> None:
    protocol = subparsers.add_parser(
        "protocol-check", help="validate a declared experiment protocol"
    )
    protocol.add_argument(
        "--manifest",
        default="data/manifests/nature_mainline_protocol_v1.yaml",
    )
    protocol.add_argument(
        "--require-execution-ready",
        action="store_true",
        help="also require external datasets, hashes, and optimization dependencies",
    )

def _add_firm_flexibility_parsers(subparsers: Any) -> None:
    certify = subparsers.add_parser(
        "certify", help="certify rebound-aware reliable hourly flexibility"
    )
    certify.add_argument(
        "certification_command",
        nargs="?",
        choices=("frozen-select", "frozen-test"),
        help=(
            "select on validation or evaluate an already frozen selection on the locked test split"
        ),
    )
    certify.add_argument(
        "--controller-config",
        help="complete validated controller specification required by frozen-select/test",
    )
    certify.add_argument("--durations", type=int, nargs="+")
    certify.add_argument(
        "--notices",
        type=int,
        nargs="+",
        help="notice-hour certificate keys; select defaults to the validation config choices",
    )
    certify.add_argument(
        "--candidate-fractions",
        type=float,
        nargs="+",
        default=(0.0, 1.0),
        help="grid points, or lower/upper bounds when --search binary",
    )
    certify.add_argument("--search", choices=("grid", "binary"), default="binary")
    certify.add_argument("--binary-iterations", type=int, default=8)
    certify.add_argument("--reliability", type=float, default=0.95)
    certify.add_argument("--confidence", type=float, default=0.95)
    certify.add_argument("--min-delivery-ratio", type=float, default=0.95)
    certify.add_argument("--min-interval-delivery-ratio", type=float, default=0.95)
    certify.add_argument("--max-deadline-miss-rate", type=float, default=0.01)
    certify.add_argument("--max-rebound-ratio", type=float, default=0.25)
    certify.add_argument("--min-window-peak-relief-fraction", type=float, default=0.50)
    certify.add_argument("--max-terminal-backlog-fraction", type=float, default=0.02)
    certify.add_argument("--selection", help="frozen validation selection for certify locked-test")
    certify.add_argument(
        "--scenarios",
        help="frozen validation or locked-ID scenario directory for frozen certification",
    )
    certify.add_argument("--output", help="output directory for certify select or locked-test")
    certify.add_argument(
        "--workers",
        type=int,
        default=1,
        help="independent frozen scenarios to replay concurrently (default: 1)",
    )

    compare_envelopes = subparsers.add_parser(
        "compare-envelopes", help="compare static planning envelopes with certificates"
    )
    compare_envelopes.add_argument("--static-fractions", type=float, nargs="+", required=True)
    compare_envelopes.add_argument(
        "--certificates",
        nargs="+",
        required=True,
        help="one or more certify output directories or certificates.parquet paths",
    )
    compare_envelopes.add_argument("--save", required=True)



def _add_paper_parsers(subparsers: Any) -> None:
    paper = subparsers.add_parser(
        "paper", help="export manuscript source data and generate frozen mainline figures"
    )
    commands = paper.add_subparsers(dest="paper_command")

    source_data = commands.add_parser(
        "export-source-data",
        help="export hash-bound manuscript source-data CSV files",
    )
    source_data.add_argument(
        "--specification",
        default="configs/paper/nature_source_data_v1.yaml",
    )
    source_data.add_argument(
        "--output",
        default="results/nature_mainline/source_data_v1",
    )
    source_data.add_argument("--repository-root", default=".")

    figures = commands.add_parser(
        "figures",
        help="generate publication figures from a verified source-data bundle",
    )
    figures.add_argument(
        "--source-data",
        default="results/nature_mainline/source_data_v1",
    )
    figures.add_argument(
        "--output",
        default="results/figures/nature_mainline_v1",
    )
    figures.add_argument("--figures", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    figures.add_argument(
        "--formats",
        nargs="+",
        choices=("svg", "pdf", "tiff", "png"),
        default=["svg", "pdf", "tiff", "png"],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aidrbench", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("project-check", help="validate the repository skeleton")
    check.add_argument("--root", default=".", help="repository root (default: current directory)")
    _add_data_parsers(subparsers)
    _add_calibration_parsers(subparsers)
    _add_hourly_environment_parsers(subparsers)
    _add_scenario_parsers(subparsers)
    _add_optimization_parsers(subparsers)
    _add_protocol_parser(subparsers)
    _add_firm_flexibility_parsers(subparsers)
    _add_paper_parsers(subparsers)
    return parser


def _print_summary(summary: object) -> None:
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


def _parse_datasets(values: list[str]) -> dict[str, str]:
    datasets: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"dataset must be NAME=PATH, got: {value}")
        name, path = value.split("=", 1)
        if not name or not path:
            raise ValueError(f"dataset must be NAME=PATH, got: {value}")
        datasets[name] = path
    return datasets


def _run_config(config_path: str) -> dict[str, object]:
    with Path(config_path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("data config must be a YAML mapping")
    dataset = config.get("dataset")
    if dataset == "alibaba_gpu_v2026_summary":
        from aidrbench.data.alibaba2026 import preprocess_alibaba_summary

        return preprocess_alibaba_summary(
            str(config["input"]),
            str(config["output"]),
            winsorize_quantile=(
                float(config["winsorize_quantile"])
                if config.get("winsorize_quantile") is not None
                else None
            ),
        )
    if dataset == "alibaba_gpu_v2026_sampler":
        from aidrbench.data.alibaba2026 import make_alibaba_lite_sampler_pool

        return make_alibaba_lite_sampler_pool(
            str(config["input"]),
            str(config["output"]),
            job_classes=[str(value) for value in config["job_classes"]],
            priorities=[str(value) for value in config["priorities"]],
            rows_per_stratum=int(config.get("rows_per_stratum", 50_000)),
            seed=int(config.get("seed", 2026)),
        )
    if dataset == "community" and config.get("mode") == "synthetic_smoke":
        from aidrbench.data.community import make_synthetic_community

        return make_synthetic_community(
            str(config["output"]),
            days=int(config.get("days", 30)),
            resolution_seconds=int(config.get("resolution_seconds", 900)),
            peak_kw=float(config.get("peak_kw", 100.0)),
            seed=int(config.get("seed", 42)),
        )
    if dataset == "community_eulp":
        from aidrbench.data.community import (
            catalog_community_profiles,
            preprocess_community_profiles,
        )

        catalog_community_profiles(str(config["input_glob"]), str(config["catalog"]))
        configured_profiles = config.get("profiles")
        if configured_profiles is not None and not isinstance(configured_profiles, list):
            raise ValueError("community_eulp profiles must be a list")
        return preprocess_community_profiles(
            str(config["catalog"]),
            str(config["output"]),
            profiles=(
                [str(profile_id) for profile_id in configured_profiles]
                if configured_profiles is not None
                else None
            ),
            peak_kw=float(config.get("peak_kw", 100.0)),
            include_mixed=bool(config.get("include_mixed", False)),
            commercial_weight=float(config.get("commercial_weight", 0.25)),
        )
    if dataset == "dr_events" and config.get("mode") == "synthetic_hourly":
        from aidrbench.data.community import generate_dr_events

        return generate_dr_events(
            str(config["community"]),
            str(config["output"]),
            days=int(config.get("days", 90)),
            reductions=[float(value) for value in config["reductions"]],
            durations=[int(value) for value in config["durations_minutes"]],
            notices=[int(value) for value in config["notices_minutes"]],
            seed=int(config.get("seed", 42)),
            profile_id=(str(config["profile_id"]) if config.get("profile_id") else None),
            align_minutes=int(config.get("align_minutes", 60)),
        )
    raise ValueError(f"unsupported data config dataset/mode: {dataset}/{config.get('mode')}")


def _run_data(args: argparse.Namespace) -> int:
    if args.data_command == "preprocess-alibaba-summary":
        from aidrbench.data.alibaba2026 import preprocess_alibaba_summary

        summary = preprocess_alibaba_summary(
            args.input,
            args.output,
            winsorize_quantile=args.winsorize_quantile,
        )
    elif args.data_command == "make-alibaba-lite-arrivals":
        from aidrbench.data.alibaba2026 import write_alibaba_lite_hourly_arrivals
        from aidrbench.envs.hourly_config import load_hourly_environment_config

        config = load_hourly_environment_config(args.config)
        if config.workload_source != "alibaba2026_lite":
            raise ValueError("Lite arrival construction requires workload.source=alibaba2026_lite")
        if config.alibaba_summary_path is None:
            raise ValueError("Lite arrival construction requires workload.summary_path")
        summary = write_alibaba_lite_hourly_arrivals(
            config.alibaba_summary_path,
            args.output,
            hours=args.hours or config.main_hours,
            total_gpu_count=config.make_power_model().data_center.total_gpu_count,
            flexible_arrival_utilization=config.flexible_arrival_utilization,
            workload_shares=config.workload_mix.shares,
            flexible_fractions=config.workload_mix.flexible_fractions,
            flexible_priorities=config.flexible_priorities,
            deadline_policy=config.deadline_policy,
            deadline_slack_scale=config.deadline_slack_scale,
            max_deadline_hours=config.max_deadline_hours,
            arrival_process=config.alibaba_arrival_process,
            seed=args.seed,
        )
    elif args.data_command == "make-alibaba-lite-sampler":
        from aidrbench.data.alibaba2026 import make_alibaba_lite_sampler_pool

        summary = make_alibaba_lite_sampler_pool(
            args.input,
            args.output,
            job_classes=args.job_classes,
            priorities=args.priorities,
            rows_per_stratum=args.rows_per_stratum,
            seed=args.seed,
        )
    elif args.data_command == "make-synthetic-community":
        from aidrbench.data.community import make_synthetic_community

        summary = make_synthetic_community(
            args.output,
            days=args.days,
            resolution_seconds=args.resolution_seconds,
            peak_kw=args.peak_kw,
            seed=args.seed,
        )
    elif args.data_command == "catalog-community":
        from aidrbench.data.community import catalog_community_profiles

        summary = catalog_community_profiles(args.input, args.output)
    elif args.data_command == "list-community-profiles":
        from aidrbench.data.community import list_community_profiles

        summary = {"profiles": list_community_profiles(args.catalog)}
    elif args.data_command == "preprocess-community":
        from aidrbench.data.community import preprocess_community_profiles

        summary = preprocess_community_profiles(
            args.catalog,
            args.output,
            profiles=args.profile,
            peak_kw=args.peak_kw,
            include_mixed=args.include_mixed,
            commercial_weight=args.commercial_weight,
        )
    elif args.data_command == "generate-dr-events":
        from aidrbench.data.community import generate_dr_events

        summary = generate_dr_events(
            args.community,
            args.output,
            days=args.days,
            reductions=args.reductions,
            durations=args.durations,
            notices=args.notices,
            seed=args.seed,
            profile_id=args.profile_id,
            align_minutes=args.align_minutes,
        )
    elif args.data_command == "create-split-manifest":
        from aidrbench.data.splits import create_split_manifest

        summary = create_split_manifest(_parse_datasets(args.dataset), args.output, seed=args.seed)
    elif args.data_command == "validate":
        from aidrbench.data.splits import validate_manifest

        summary = validate_manifest(args.manifest)
        _print_summary(summary)
        return 0 if summary["valid"] else 1
    elif args.data_command == "validate-sources":
        from aidrbench.data.splits import validate_source_manifest

        summary = validate_source_manifest(args.manifest)
        _print_summary(summary)
        return 0 if summary["valid"] else 1
    elif args.data_command == "preprocess":
        summary = _run_config(args.config)
    else:
        raise ValueError("a data subcommand is required")
    _print_summary(summary)
    return 0


def _run_calibration(args: argparse.Namespace) -> int:
    if args.calibration_command == "validate-artifact":
        from aidrbench.calibration.artifact import load_hardware_calibration_artifact

        artifact = load_hardware_calibration_artifact(args.artifact)
        _print_summary(artifact.summary())
        return 0
    if args.calibration_command == "collect-telemetry":
        from aidrbench.telemetry.nvidia_smi import collect_nvidia_smi_telemetry

        telemetry_summary = collect_nvidia_smi_telemetry(
            args.output,
            duration_seconds=args.duration_seconds,
            interval_seconds=args.interval_seconds,
            gpu_ids=args.gpu_id,
            executable=args.nvidia_smi,
        )
        _print_summary(telemetry_summary)
        return 0
    raise ValueError("a calibrate subcommand is required")


def _make_hourly_environment(config_path: str) -> Any:
    from aidrbench.envs.community_ai_dr_env import (
        ContinuousCommunityAIDemandResponseEnv,
        DiscreteCommunityAIDemandResponseEnv,
    )
    from aidrbench.envs.hourly_config import load_hourly_environment_config

    config = load_hourly_environment_config(config_path)
    if config.action_mode == "continuous":
        return ContinuousCommunityAIDemandResponseEnv(config_path)
    return DiscreteCommunityAIDemandResponseEnv(config_path)


def _run_env(args: argparse.Namespace) -> int:
    if args.env_command != "check":
        raise ValueError("an env subcommand is required")
    import gymnasium as gym
    from gymnasium.utils.env_checker import check_env

    from aidrbench.envs.hourly_config import load_hourly_environment_config
    from aidrbench.envs.registration import (
        CONTINUOUS_ENV_ID,
        DISCRETE_ENV_ID,
        register_environments,
    )

    config = load_hourly_environment_config(args.config)
    register_environments()
    env_id = CONTINUOUS_ENV_ID if config.action_mode == "continuous" else DISCRETE_ENV_ID
    env = gym.make(env_id, config=args.config)
    check_env(env.unwrapped)
    hourly_env: Any = env.unwrapped
    _print_summary(
        {
            "status": "passed",
            "config": args.config,
            "environment": type(env.unwrapped).__name__,
            "action_space": str(env.action_space),
            "observation_space": str(env.observation_space),
            "observation_version": hourly_env.observation_version,
            "observation_size": len(hourly_env.observation_feature_names),
            "reward_version": config.reward.version,
            "episode_seed_range": config.episode_seed_range,
            "community_source": config.community_source,
            "community_profile_id": config.community_profile_id,
            "community_path": (
                str(config.community_path) if config.community_path is not None else None
            ),
            "dr_source": config.dr_source,
            "dr_events_path": (
                str(config.dr_manifest_path) if config.dr_manifest_path is not None else None
            ),
            "training_share": config.workload_mix.training_share,
            "flexible_workload_share": config.workload_mix.flexible_share,
        }
    )
    return 0


def _run_rollout(args: argparse.Namespace) -> int:
    from aidrbench.controllers.hourly import make_hourly_controller
    from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode, save_hourly_rollout

    env = _make_hourly_environment(args.config)
    frame, summary = rollout_hourly_episode(
        env,
        make_hourly_controller(args.controller),
        seed=args.seed,
    )
    summary["scenario"] = args.scenario
    saved = save_hourly_rollout(frame, summary, args.save)
    _print_summary({**summary, **saved})
    return 0


def _run_scenario(args: argparse.Namespace) -> int:
    if args.scenario_command == "freeze":
        from aidrbench.data.frozen_scenarios import freeze_hourly_scenarios
        from aidrbench.evaluation.locked_ood import (
            consume_locked_ood_authorization,
            prepare_locked_ood_freeze,
        )

        authorization = prepare_locked_ood_freeze(
            args.config,
            output_directory=args.output,
            preregistration_manifest=args.preregistration_manifest,
            unlock_locked_ood=args.unlock_locked_ood,
            acknowledge_one_time_locked_use=args.acknowledge_one_time_locked_use,
        )
        config: str | dict[str, Any] = args.config
        if args.calibration_power_case is not None:
            loaded = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
            if not isinstance(loaded, dict) or not isinstance(loaded.get("hardware"), dict):
                raise ValueError("scenario config must contain a hardware mapping")
            loaded["hardware"]["calibration_power_case"] = args.calibration_power_case
            config = loaded
        scenarios = freeze_hourly_scenarios(
            config,
            seeds=args.seeds,
            output_directory=args.output,
        )
        receipt = (
            consume_locked_ood_authorization(
                authorization,
                output_directory=args.output,
                scenario_hashes=[str(scenario["scenario_hash"]) for scenario in scenarios],
            )
            if authorization is not None
            else None
        )
        _print_summary(
            {
                "scenario_count": len(scenarios),
                "scenarios": scenarios,
                "locked_ood_receipt": str(receipt) if receipt is not None else None,
            }
        )
        return 0
    if args.scenario_command == "freeze-exhaustion":
        from aidrbench.evaluation.exhaustion import freeze_repeated_event_scenarios

        summary = freeze_repeated_event_scenarios(
            args.specification,
            seeds=args.seeds,
            output_directory=args.output,
        )
        _print_summary(summary)
        return 0
    if args.scenario_command == "inspect":
        from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario

        scenario = load_frozen_hourly_scenario(args.input)
        _print_summary(
            {
                "scenario_id": scenario.scenario_id,
                "scenario_hash": scenario.scenario_hash,
                "episode_seed": scenario.episode_seed,
                "community_hours": len(scenario.community),
                "arrival_rows": len(scenario.arrivals),
                "baseline_hours": len(scenario.baseline),
                "events": list(scenario.events),
                "scenario_bases": scenario.metadata["scenario_bases"],
                "power_model": scenario.metadata["power_model"],
            }
        )
        return 0
    if args.scenario_command == "check-sensitivities":
        from aidrbench.evaluation.sensitivity import (
            check_sparse_sensitivity_no_dr_feasibility,
        )

        summary = check_sparse_sensitivity_no_dr_feasibility(
            args.specification,
            seeds=args.seeds,
            output_directory=args.output,
        )
        _print_summary(summary)
        return 0
    if args.scenario_command == "check-infrastructure-sensitivities":
        from aidrbench.evaluation.infrastructure_sensitivity import (
            check_infrastructure_no_dr_feasibility,
        )

        summary = check_infrastructure_no_dr_feasibility(
            args.specification,
            seeds=args.seeds,
            output_directory=args.output,
        )
        _print_summary(summary)
        return 0
    if args.scenario_command == "freeze-sensitivities":
        from aidrbench.evaluation.workload_sensitivity import (
            freeze_workload_sensitivity_scenarios,
        )

        summary = freeze_workload_sensitivity_scenarios(
            args.specification,
            output_directory=args.output,
        )
        _print_summary(summary)
        return 0
    if args.scenario_command == "freeze-infrastructure-sensitivities":
        from aidrbench.evaluation.infrastructure_sensitivity import (
            freeze_infrastructure_sensitivity_scenarios,
        )

        summary = freeze_infrastructure_sensitivity_scenarios(
            args.specification,
            output_directory=args.output,
        )
        _print_summary(summary)
        return 0
    raise ValueError("a scenario subcommand is required")


def _run_optimization(args: argparse.Namespace) -> int:
    if args.optimization_command == "pi-frontier":
        from aidrbench.evaluation.pi_frontier import compute_and_save_pi_frontier

        summary = compute_and_save_pi_frontier(
            args.scenarios,
            durations_h=args.durations,
            output_directory=args.output,
            event_id=args.event_id,
            reliability_targets=args.reliabilities,
            confidence_level=args.confidence_level,
            nominal_flexibility_fraction=args.nominal_flexibility_fraction,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "criteria-sensitivity":
        from aidrbench.evaluation.criteria_sensitivity import (
            compute_and_save_criteria_sensitivity,
        )

        summary = compute_and_save_criteria_sensitivity(
            args.scenarios,
            specification=args.specification,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "workload-sensitivity":
        from aidrbench.evaluation.workload_sensitivity import (
            compute_and_save_workload_sensitivity,
        )

        summary = compute_and_save_workload_sensitivity(
            args.scenarios,
            specification=args.specification,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "infrastructure-sensitivity":
        from aidrbench.evaluation.infrastructure_sensitivity import (
            compute_and_save_infrastructure_sensitivity,
        )

        summary = compute_and_save_infrastructure_sensitivity(
            args.scenarios,
            specification=args.specification,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "non-anticipative-firm":
        from aidrbench.evaluation.non_anticipative import (
            ObservationPartitionSpecification,
            compute_and_save_non_anticipative_frontier,
        )

        observation_specification = (
            ObservationPartitionSpecification(
                forecast_horizon_hours=args.forecast_horizon_hours,
                power_bin_width_pu=args.power_bin_width_pu,
                arrival_bin_width_fraction=args.arrival_bin_width_fraction,
                minimum_shared_node_size=args.minimum_shared_node_size,
            )
            if args.information_structure == "coarse_observation_partition_tree"
            else None
        )
        summary = compute_and_save_non_anticipative_frontier(
            args.scenarios,
            durations_h=args.durations,
            notice_hours=args.notice_hours,
            output_directory=args.output,
            event_id=args.event_id,
            reliability_target=args.reliability_target,
            information_structure=args.information_structure,
            observation_specification=observation_specification,
            matched_pi_frontier_path=args.matched_pi_frontier,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "merge-non-anticipative":
        from aidrbench.evaluation.non_anticipative import (
            merge_non_anticipative_frontier_partitions,
        )

        summary = merge_non_anticipative_frontier_partitions(
            args.inputs,
            output_directory=args.output,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "notice-diagnostics":
        from aidrbench.evaluation.notice_diagnostics import (
            compute_notice_mechanism_diagnostics,
        )

        summary = compute_notice_mechanism_diagnostics(
            args.scenarios,
            pi_frontier_path=args.pi_frontier,
            na_frontier_path=args.na_frontier,
            na_policies_path=args.na_policies,
            controller_config=args.controller_config,
            output_directory=args.output,
            durations_h=args.durations,
            notices_h=args.notices,
            reliability_target=args.reliability,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "exhaustion-diagnostics":
        from aidrbench.evaluation.exhaustion import (
            compute_repeated_event_exhaustion_diagnostics,
        )

        summary = compute_repeated_event_exhaustion_diagnostics(
            args.scenarios,
            specification_path=args.specification,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "hosting-capacity":
        from aidrbench.evaluation.hosting_capacity import (
            compute_and_save_hosting_capacity,
            load_community_portfolio,
        )

        summary = compute_and_save_hosting_capacity(
            args.scenarios,
            portfolio=load_community_portfolio(args.portfolio),
            output_directory=args.output,
            dc_operation=args.dc_operation,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "hosting-ensemble":
        from aidrbench.evaluation.hosting_ensemble import compute_hosting_ensemble

        summary = compute_hosting_ensemble(
            args.scenarios,
            specification_path=args.specification,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.optimization_command == "renewable-integration":
        from aidrbench.evaluation.renewable_ensemble import (
            compute_renewable_integration_ensemble,
        )

        summary = compute_renewable_integration_ensemble(
            args.scenarios,
            specification_path=args.specification,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    raise ValueError("an optimize subcommand is required")


def _run_protocol_check(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    from aidrbench.evaluation.nature_protocol import validate_nature_mainline_protocol

    report = validate_nature_mainline_protocol(manifest_path)
    _print_summary(report)
    readiness_key = (
        "execution_ready"
        if args.require_execution_ready and "execution_ready" in report
        else "valid"
    )
    return 0 if bool(report[readiness_key]) else 1


def _run_certify(args: argparse.Namespace) -> int:
    if args.certification_command == "frozen-select":
        if (
            args.scenarios is None
            or args.controller_config is None
            or not args.durations
            or args.output is None
        ):
            raise ValueError(
                "certify frozen-select requires --scenarios, --controller-config, "
                "--durations, and --output"
            )
        from aidrbench.evaluation.frozen_causal_certificate import (
            select_frozen_causal_capacities,
        )

        criteria = _firm_criteria_from_args(args)
        summary = select_frozen_causal_capacities(
            args.scenarios,
            controller_config=args.controller_config,
            durations_h=args.durations,
            notices_h=args.notices or (0,),
            candidate_fractions=args.candidate_fractions,
            search=args.search,
            binary_iterations=args.binary_iterations,
            criteria=criteria,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    if args.certification_command == "frozen-test":
        if (
            args.scenarios is None
            or args.selection is None
            or args.controller_config is None
            or args.output is None
        ):
            raise ValueError(
                "certify frozen-test requires --scenarios, --selection, "
                "--controller-config, and --output"
            )
        from aidrbench.evaluation.frozen_causal_certificate import (
            certify_selected_frozen_causal_capacities,
        )

        summary = certify_selected_frozen_causal_capacities(
            args.scenarios,
            selection_path=args.selection,
            controller_config=args.controller_config,
            output_directory=args.output,
            workers=args.workers,
        )
        _print_summary(summary)
        return 0
    raise ValueError("certify requires frozen-select or frozen-test")


def _run_compare_envelopes(args: argparse.Namespace) -> int:
    from aidrbench.evaluation.envelopes import (
        compare_static_envelopes,
        load_certificate_table,
        save_envelope_comparison,
    )

    certificate_tables = [load_certificate_table(path) for path in args.certificates]
    comparison, summary = compare_static_envelopes(
        pd.concat(certificate_tables, ignore_index=True),
        static_fractions=args.static_fractions,
    )
    saved = save_envelope_comparison(
        comparison,
        summary,
        certificate_paths=args.certificates,
        output_directory=args.save,
    )
    _print_summary({"rows": len(comparison), "summary_rows": len(summary), **saved})
    return 0


def _firm_criteria_from_args(args: argparse.Namespace) -> FirmFlexibilityCriteria:
    return FirmFlexibilityCriteria(
        reliability_target=args.reliability,
        confidence_level=args.confidence,
        min_delivery_ratio=args.min_delivery_ratio,
        min_interval_delivery_ratio=args.min_interval_delivery_ratio,
        max_deadline_miss_rate=args.max_deadline_miss_rate,
        max_rebound_ratio=args.max_rebound_ratio,
        min_window_peak_relief_fraction=args.min_window_peak_relief_fraction,
        max_terminal_backlog_fraction=args.max_terminal_backlog_fraction,
    )


def _run_paper(args: argparse.Namespace) -> int:
    if args.paper_command == "export-source-data":
        from aidrbench.evaluation.source_data import export_manuscript_source_data

        summary = export_manuscript_source_data(
            args.specification,
            args.output,
            repository_root=args.repository_root,
        )
        _print_summary(summary)
        return 0
    if args.paper_command == "figures":
        from aidrbench.evaluation.nature_figures_reference import (
            plot_nature_mainline_figures,
        )

        summary = plot_nature_mainline_figures(
            args.source_data,
            args.output,
            figures=args.figures,
            formats=args.formats,
        )
        _print_summary(summary)
        return 0
    raise ValueError("paper subcommand is required")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "project-check":
        report = check_project(args.root)
        print(format_report(report))
        return 0 if report.ok else 1
    if args.command == "data":
        try:
            return _run_data(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "calibrate":
        try:
            return _run_calibration(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "env":
        try:
            return _run_env(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "scenario":
        try:
            return _run_scenario(args)
        except (FileExistsError, FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "optimize":
        try:
            return _run_optimization(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "rollout":
        try:
            return _run_rollout(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "protocol-check":
        try:
            return _run_protocol_check(args)
        except (FileNotFoundError, KeyError, TypeError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "certify":
        try:
            return _run_certify(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "compare-envelopes":
        try:
            return _run_compare_envelopes(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "paper":
        try:
            return _run_paper(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
