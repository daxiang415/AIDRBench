"""AIDRBench command-line interface."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from aidrbench._version import __version__
from aidrbench.envs.actions import all_actions
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria
from aidrbench.project_check import check_project, format_report


def _add_data_parsers(subparsers: Any) -> None:
    data = subparsers.add_parser("data", help="prepare and validate P1 datasets")
    commands = data.add_subparsers(dest="data_command")

    burst = commands.add_parser("preprocess-burstgpt", help="normalize BurstGPT CSV files")
    burst.add_argument("--input", required=True)
    burst.add_argument("--output", required=True)
    burst.add_argument("--time-scale", type=float, default=1.0)
    burst.add_argument("--include-failed-responses", action="store_true")

    alibaba = commands.add_parser("preprocess-alibaba", help="normalize Alibaba PAI tables")
    alibaba.add_argument("--job-table", required=True)
    alibaba.add_argument("--task-table", required=True)
    alibaba.add_argument("--max-local-batch-gpus", type=float, default=2.0)
    alibaba.add_argument("--deadline-policy", default="slack-mixture")
    alibaba.add_argument("--seed", type=int, default=42)
    alibaba.add_argument("--output", required=True)

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
    calibration = subparsers.add_parser(
        "calibrate", help="plan and execute P2 hardware calibration"
    )
    commands = calibration.add_subparsers(dest="calibration_command")

    make_plan = commands.add_parser(
        "make-plan", help="write the deterministic coarse-grid calibration plan"
    )
    make_plan.add_argument("--config", required=True)
    make_plan.add_argument("--output", required=True)
    make_plan.add_argument("--design", default="full-factorial")

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

    trace = commands.add_parser(
        "make-aiperf-smoke-trace",
        help="create a short time-compressed BurstGPT trace for AIPerf smoke",
    )
    trace.add_argument("--input", required=True)
    trace.add_argument("--output", required=True)
    trace.add_argument("--requests", type=int, default=10)
    trace.add_argument("--time-scale", type=float, default=20.0)

    dry_plan = commands.add_parser(
        "dry-run-plan",
        help="resolve power targets and mixed workloads without mutation or process launch",
    )
    dry_plan.add_argument("--plan", required=True)
    dry_plan.add_argument("--config", required=True)
    dry_plan.add_argument("--output", required=True)
    dry_plan.add_argument("--restore-manifest", required=True)
    dry_plan.add_argument("--audit-log", required=True)
    dry_plan.add_argument("--limit", type=int)
    dry_plan.add_argument("--nvidia-smi", default="nvidia-smi", dest="nvidia_smi")

    compare_topology = commands.add_parser(
        "compare-topology-runs",
        help="compare paired tensor-parallel AIPerf runs and GPU telemetry",
    )
    compare_topology.add_argument("--baseline-aiperf", required=True)
    compare_topology.add_argument("--baseline-telemetry", required=True)
    compare_topology.add_argument("--baseline-gpu-id", type=int, action="append", required=True)
    compare_topology.add_argument("--candidate-aiperf", required=True)
    compare_topology.add_argument("--candidate-telemetry", required=True)
    compare_topology.add_argument("--candidate-gpu-id", type=int, action="append", required=True)
    compare_topology.add_argument("--topology-class", default="unknown")
    compare_topology.add_argument("--transport", default="unknown")
    compare_topology.add_argument("--output", required=True)


def _add_fleet_parsers(subparsers: Any) -> None:
    fleet = subparsers.add_parser("fleet", help="plan evidence-aware virtual data-center capacity")
    commands = fleet.add_subparsers(dest="fleet_command")
    plan = commands.add_parser(
        "plan-capacity",
        help="compare explicit GPU profiles using Roofline and power constraints",
    )
    plan.add_argument("--config", required=True)
    plan.add_argument("--output")


def _add_hil_parsers(subparsers: Any) -> None:
    hil = subparsers.add_parser("hil", help="hardware safety preflight and recovery")
    commands = hil.add_subparsers(dest="hil_command")

    preflight = commands.add_parser(
        "power-preflight", help="capture read-only power/topology evidence and defaults"
    )
    preflight.add_argument("--config", required=True)
    preflight.add_argument("--restore-manifest", required=True)
    preflight.add_argument("--audit-log", required=True)
    preflight.add_argument("--nvidia-smi", default="nvidia-smi", dest="nvidia_smi")

    dry_action = commands.add_parser(
        "dry-run-action", help="resolve one action without changing GPU state"
    )
    dry_action.add_argument("--config", required=True)
    dry_action.add_argument("--action", required=True, type=int)
    dry_action.add_argument("--caller", default="aidrbench-cli")
    dry_action.add_argument("--restore-manifest", required=True)
    dry_action.add_argument("--audit-log", required=True)
    dry_action.add_argument("--nvidia-smi", default="nvidia-smi", dest="nvidia_smi")

    restore = commands.add_parser(
        "restore-power", help="verify or restore captured default GPU limits"
    )
    restore.add_argument("--manifest", required=True)
    restore.add_argument("--execute", action="store_true")
    restore.add_argument("--acknowledge-hardware-mutation", action="store_true")
    restore.add_argument("--nvidia-smi", default="nvidia-smi", dest="nvidia_smi")

    watchdog = commands.add_parser(
        "watchdog", help="monitor a controller heartbeat and restore defaults on timeout"
    )
    watchdog.add_argument("--heartbeat", required=True)
    watchdog.add_argument("--manifest", required=True)
    watchdog.add_argument("--timeout-seconds", type=float, required=True)
    watchdog.add_argument("--poll-seconds", type=float, default=1.0)
    watchdog.add_argument("--execute", action="store_true")
    watchdog.add_argument("--acknowledge-hardware-mutation", action="store_true")
    watchdog.add_argument("--nvidia-smi", default="nvidia-smi", dest="nvidia_smi")


def _add_hourly_environment_parsers(subparsers: Any) -> None:
    environment = subparsers.add_parser("env", help="inspect the V0 hourly Gymnasium environments")
    commands = environment.add_subparsers(dest="env_command")
    check = commands.add_parser("check", help="run Gymnasium check_env on one hourly config")
    check.add_argument("--config", required=True)

    rollout = subparsers.add_parser("rollout", help="run one V0 hourly baseline episode")
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
        choices=("lower_ci", "nominal", "upper_ci"),
        help="override only the declared calibration uncertainty case before freezing",
    )
    freeze.add_argument("--output", required=True)
    inspect = commands.add_parser(
        "inspect", help="verify one frozen scenario and display its provenance"
    )
    inspect.add_argument("--input", required=True)


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
    frontier.add_argument("--output", required=True)
    non_anticipative = commands.add_parser(
        "non-anticipative-firm",
        help="compute a chance-constrained causal non-anticipative lower bound",
    )
    non_anticipative.add_argument("--scenarios", required=True)
    non_anticipative.add_argument("--durations", nargs="+", type=int, required=True)
    non_anticipative.add_argument("--notice-hours", nargs="+", type=int, default=[0])
    non_anticipative.add_argument("--event-id", type=int, default=0)
    non_anticipative.add_argument("--reliability-target", type=float, default=1.0)
    non_anticipative.add_argument(
        "--confidence-level",
        type=float,
        help="one-sided Wilson confidence level; omit for the legacy empirical rule",
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
    non_anticipative.add_argument("--output", required=True)
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


def _add_training_parsers(subparsers: Any) -> None:
    protocol = subparsers.add_parser(
        "protocol-check", help="validate a declared experiment protocol"
    )
    protocol.add_argument(
        "--manifest",
        default="data/manifests/nature_mainline_protocol_v1.yaml",
    )

    train = subparsers.add_parser(
        "train", help="train a standard RL policy on the hourly environment"
    )
    train.add_argument("--algo", choices=("dqn", "ppo", "sac"), required=True)
    train.add_argument("--env", choices=("continuous", "discrete"), required=True)
    train.add_argument("--config", required=True)
    train.add_argument("--seed", type=int, required=True)
    train.add_argument("--save", required=True)
    train.add_argument("--timesteps", type=int)
    train.add_argument(
        "--resume",
        help="existing model.zip to continue in another bounded training segment",
    )

    evaluate = subparsers.add_parser(
        "evaluate", help="evaluate one saved RL policy with common KPIs"
    )
    evaluate.add_argument("--controller", choices=("dqn", "ppo", "sac"), required=True)
    evaluate.add_argument("--model", required=True)
    evaluate.add_argument("--config", required=True)
    evaluate.add_argument("--seed", type=int, required=True)
    evaluate.add_argument("--save", required=True)

    benchmark = subparsers.add_parser(
        "benchmark", help="evaluate controllers over matched hourly scenarios and seeds"
    )
    benchmark.add_argument(
        "--controllers",
        nargs="+",
        choices=(
            "no_control",
            "threshold",
            "edf_valley",
            "mpc",
            "robust_mpc",
            "oracle",
            "dqn",
            "ppo",
            "sac",
        ),
        required=True,
    )
    benchmark.add_argument("--config", default="configs/env/hourly_continuous.yaml")
    benchmark.add_argument("--seeds", nargs="+", type=int, required=True)
    benchmark.add_argument(
        "--model",
        action="append",
        default=[],
        metavar="CONTROLLER=PATH",
        help="saved policy path; repeat for each requested DQN/PPO/SAC controller",
    )
    benchmark.add_argument("--save", required=True)

    plot = subparsers.add_parser(
        "plot", help="plot representative hourly benchmark episodes"
    )
    plot.add_argument("--input", required=True)
    plot.add_argument("--output", required=True)
    plot.add_argument(
        "--controllers",
        nargs="+",
        choices=(
            "no_control",
            "threshold",
            "edf_valley",
            "mpc",
            "robust_mpc",
            "oracle",
            "dqn",
            "ppo",
            "sac",
        ),
        help="default: every controller in episodes.parquet",
    )
    plot.add_argument("--seed", type=int, help="default: minimum available seed per controller")
    plot.add_argument("--include-clearance-tail", action="store_true")


def _add_firm_flexibility_parsers(subparsers: Any) -> None:
    certify = subparsers.add_parser(
        "certify", help="certify rebound-aware reliable hourly flexibility"
    )
    certify.add_argument(
        "certification_command",
        nargs="?",
        choices=("select", "locked-test"),
        help=(
            "select on validation or evaluate an already frozen selection on the "
            "locked test split"
        ),
    )
    certify.add_argument(
        "--controller",
        choices=(
            "no_control",
            "threshold",
            "edf_valley",
            "mpc",
            "robust_mpc",
            "dqn",
            "ppo",
            "sac",
        ),
    )
    certify.add_argument("--model", help="required when controller is DQN, PPO, or SAC")
    certify.add_argument("--config", default="configs/env/hourly_continuous.yaml")
    certify.add_argument("--durations", type=int, nargs="+")
    certify.add_argument(
        "--notices",
        type=int,
        nargs="+",
        help="notice-hour certificate keys; select defaults to the validation config choices",
    )
    certify.add_argument("--episodes", type=int)
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
    certify.add_argument("--save")
    certify.add_argument(
        "--protocol-manifest", default="data/manifests/hourly_experiment_protocol_v2.yaml"
    )
    certify.add_argument("--selection", help="frozen validation selection for certify locked-test")
    certify.add_argument("--output", help="output directory for certify select or locked-test")

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

    stress_test = subparsers.add_parser(
        "stress-test", help="certify repeated-event flexibility exhaustion"
    )
    stress_test.add_argument(
        "--controllers",
        nargs="+",
        choices=("no_control", "threshold", "edf_valley", "mpc", "dqn", "ppo", "sac"),
        required=True,
    )
    stress_test.add_argument("--model", action="append", default=[], metavar="CONTROLLER=PATH")
    stress_test.add_argument("--config", default="configs/env/hourly_continuous.yaml")
    stress_test.add_argument("--events-per-day", type=int, nargs="+", required=True)
    stress_test.add_argument("--inter-event-gap-hours", type=int, nargs="+", required=True)
    stress_test.add_argument("--duration-hours", type=int, nargs="+", required=True)
    stress_test.add_argument("--episodes", type=int, required=True)
    stress_test.add_argument(
        "--candidate-fractions",
        type=float,
        nargs="+",
        default=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5),
    )
    stress_test.add_argument("--reliability", type=float, default=0.95)
    stress_test.add_argument("--confidence", type=float, default=0.95)
    stress_test.add_argument("--min-delivery-ratio", type=float, default=0.95)
    stress_test.add_argument("--min-interval-delivery-ratio", type=float, default=0.95)
    stress_test.add_argument("--max-deadline-miss-rate", type=float, default=0.01)
    stress_test.add_argument("--max-rebound-ratio", type=float, default=0.25)
    stress_test.add_argument("--min-window-peak-relief-fraction", type=float, default=0.50)
    stress_test.add_argument("--max-terminal-backlog-fraction", type=float, default=0.02)
    stress_test.add_argument("--save", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aidrbench", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("project-check", help="validate the repository skeleton")
    check.add_argument("--root", default=".", help="repository root (default: current directory)")
    subparsers.add_parser("show-actions", help="print the 27 discrete V0 actions")
    _add_data_parsers(subparsers)
    _add_calibration_parsers(subparsers)
    _add_fleet_parsers(subparsers)
    _add_hil_parsers(subparsers)
    _add_hourly_environment_parsers(subparsers)
    _add_scenario_parsers(subparsers)
    _add_optimization_parsers(subparsers)
    _add_training_parsers(subparsers)
    _add_firm_flexibility_parsers(subparsers)
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
    if dataset == "burstgpt":
        from aidrbench.data.burstgpt import preprocess_burstgpt

        return preprocess_burstgpt(
            str(config["input_glob"]),
            str(config["output"]),
            time_scale=float(config.get("time_scale", 1.0)),
        )
    if dataset == "alibaba_gpu_v2020":
        from aidrbench.data.alibaba import preprocess_alibaba

        return preprocess_alibaba(
            str(config["job_table"]),
            str(config["task_table"]),
            str(config["output"]),
            max_local_batch_gpus=float(config.get("max_local_batch_gpus", 2.0)),
            deadline_policy=str(config.get("deadline_policy", "slack-mixture")),
            seed=int(config.get("seed", 42)),
        )
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
    if args.data_command == "preprocess-burstgpt":
        from aidrbench.data.burstgpt import preprocess_burstgpt

        summary = preprocess_burstgpt(
            args.input,
            args.output,
            time_scale=args.time_scale,
            exclude_failed_responses=not args.include_failed_responses,
        )
    elif args.data_command == "preprocess-alibaba":
        from aidrbench.data.alibaba import preprocess_alibaba

        summary = preprocess_alibaba(
            args.job_table,
            args.task_table,
            args.output,
            max_local_batch_gpus=args.max_local_batch_gpus,
            deadline_policy=args.deadline_policy,
            seed=args.seed,
        )
    elif args.data_command == "preprocess-alibaba-summary":
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
            target_total_utilization=config.target_total_utilization,
            workload_shares=config.workload_mix.shares,
            flexible_fractions=config.workload_mix.flexible_fractions,
            flexible_priorities=config.flexible_priorities,
            deadline_policy=config.deadline_policy,
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
    if args.calibration_command == "make-plan":
        from aidrbench.calibration.plan import make_calibration_plan, summary_dict

        plan_summary = make_calibration_plan(args.config, args.output, design=args.design)
        _print_summary(summary_dict(plan_summary))
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
    if args.calibration_command == "make-aiperf-smoke-trace":
        from aidrbench.calibration.aiperf import make_burstgpt_smoke_trace

        trace_summary = make_burstgpt_smoke_trace(
            args.input,
            args.output,
            requests=args.requests,
            time_scale=args.time_scale,
        )
        _print_summary(trace_summary)
        return 0
    if args.calibration_command == "dry-run-plan":
        from aidrbench.hil.actuator_client import (
            NvidiaSmiPowerBackend,
            PowerActuator,
            load_power_actuator_config,
        )
        from aidrbench.hil.topology import NvidiaSmiTopologyBackend
        from aidrbench.hil.workload_client import (
            DryRunMixedWorkloadBackend,
            MixedWorkloadCoordinator,
            dry_run_plan,
        )

        config = load_power_actuator_config(args.config)
        actuator = PowerActuator(
            config,
            NvidiaSmiPowerBackend(args.nvidia_smi),
            restore_manifest=args.restore_manifest,
            audit_log=args.audit_log,
            dry_run=True,
            topology_backend=NvidiaSmiTopologyBackend(args.nvidia_smi),
        )
        coordinator = MixedWorkloadCoordinator(
            actuator,
            DryRunMixedWorkloadBackend(),
            batch_gpu_ids=config.batch_gpu_ids,
        )
        summary = dry_run_plan(
            args.plan,
            coordinator,
            output=args.output,
            limit=args.limit,
        )
        _print_summary(summary)
        return 0
    if args.calibration_command == "compare-topology-runs":
        from aidrbench.calibration.topology_compare import (
            compare_topology_runs,
            write_topology_comparison,
        )

        comparison = compare_topology_runs(
            args.baseline_aiperf,
            args.baseline_telemetry,
            args.candidate_aiperf,
            args.candidate_telemetry,
            baseline_gpu_ids=args.baseline_gpu_id,
            candidate_gpu_ids=args.candidate_gpu_id,
            topology_class=args.topology_class,
            transport=args.transport,
        )
        write_topology_comparison(comparison, args.output)
        _print_summary(comparison)
        return 0
    raise ValueError("a calibrate subcommand is required")


def _run_fleet(args: argparse.Namespace) -> int:
    if args.fleet_command == "plan-capacity":
        from aidrbench.datacenter.scaling import (
            capacity_comparison_dict,
            compare_capacity_options,
            write_capacity_comparison,
        )

        comparison = compare_capacity_options(args.config)
        if args.output:
            write_capacity_comparison(comparison, args.output)
        _print_summary(capacity_comparison_dict(comparison))
        return 0 if comparison.selected_profile_id is not None else 1
    raise ValueError("a fleet subcommand is required")


def _run_hil(args: argparse.Namespace) -> int:
    from aidrbench.hil.actuator_client import (
        NvidiaSmiPowerBackend,
        PowerActuator,
        actuation_result_dict,
        load_power_actuator_config,
        preflight_dict,
        restore_power_from_manifest,
    )
    from aidrbench.hil.topology import NvidiaSmiTopologyBackend

    if args.hil_command in {"power-preflight", "dry-run-action"}:
        config = load_power_actuator_config(args.config)
        actuator = PowerActuator(
            config,
            NvidiaSmiPowerBackend(args.nvidia_smi),
            restore_manifest=args.restore_manifest,
            audit_log=args.audit_log,
            dry_run=True,
            topology_backend=NvidiaSmiTopologyBackend(args.nvidia_smi),
        )
        preflight = actuator.prepare()
        if args.hil_command == "power-preflight":
            _print_summary(preflight_dict(preflight))
            return 0
        try:
            result = actuator.apply_action(args.action, caller=args.caller)
            _print_summary(actuation_result_dict(result))
            return 0
        finally:
            actuator.restore(reason="dry_run_complete")
    if args.hil_command == "restore-power":
        if args.execute and not args.acknowledge_hardware_mutation:
            raise ValueError(
                "--execute requires --acknowledge-hardware-mutation; omit both for verification"
            )
        summary = restore_power_from_manifest(
            args.manifest,
            NvidiaSmiPowerBackend(args.nvidia_smi),
            dry_run=not args.execute,
        )
        _print_summary(summary)
        return 0
    if args.hil_command == "watchdog":
        from dataclasses import asdict

        from aidrbench.hil.watchdog import monitor_heartbeat

        if args.execute and not args.acknowledge_hardware_mutation:
            raise ValueError(
                "--execute requires --acknowledge-hardware-mutation; omit both for dry-run"
            )
        restoration: dict[str, object] = {}

        def restore_after_timeout() -> None:
            restoration.update(
                restore_power_from_manifest(
                    args.manifest,
                    NvidiaSmiPowerBackend(args.nvidia_smi),
                    dry_run=not args.execute,
                )
            )

        watchdog_result = monitor_heartbeat(
            args.heartbeat,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
            on_timeout=restore_after_timeout,
        )
        _print_summary({"watchdog": asdict(watchdog_result), "restoration": restoration})
        return 0
    raise ValueError("a hil subcommand is required")


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
        _print_summary({"scenario_count": len(scenarios), "scenarios": scenarios})
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
            confidence_level=args.confidence_level,
            information_structure=args.information_structure,
            observation_specification=observation_specification,
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
    raise ValueError("an optimize subcommand is required")


def _run_train(args: argparse.Namespace) -> int:
    from aidrbench.training import train_hourly_rl

    summary = train_hourly_rl(
        args.config,
        algorithm_override=args.algo,
        environment_override=args.env,
        seed=args.seed,
        output_directory=args.save,
        total_timesteps_override=args.timesteps,
        resume_model=args.resume,
    )
    _print_summary(summary)
    return 0


def _run_protocol_check(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if (
        isinstance(document, dict)
        and document.get("study_type") == "nature_communications_mechanism_mainline"
    ):
        from aidrbench.evaluation.nature_protocol import validate_nature_mainline_protocol

        report = validate_nature_mainline_protocol(manifest_path)
    else:
        from aidrbench.evaluation.protocol import validate_hourly_experiment_protocol

        report = validate_hourly_experiment_protocol(manifest_path)
    _print_summary(report)
    return 0 if bool(report["valid"]) else 1


def _run_evaluate(args: argparse.Namespace) -> int:
    from aidrbench.controllers.hourly_sb3 import SB3HourlyPolicyController
    from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode, save_hourly_rollout

    env = _make_hourly_environment(args.config)
    if args.controller == "dqn" and env.config.action_mode != "discrete":
        raise ValueError("DQN evaluation requires the discrete hourly environment")
    if args.controller == "sac" and env.config.action_mode != "continuous":
        raise ValueError("SAC evaluation requires the continuous hourly environment")
    controller = SB3HourlyPolicyController(args.controller, args.model)
    frame, summary = rollout_hourly_episode(env, controller, seed=args.seed)
    summary["model"] = args.model
    saved = save_hourly_rollout(frame, summary, args.save)
    _print_summary({**summary, **saved})
    return 0


def _parse_model_paths(values: Sequence[str]) -> dict[str, Path]:
    """Parse repeatable ``CONTROLLER=PATH`` CLI values without ambiguity."""

    result: dict[str, Path] = {}
    for value in values:
        controller, separator, raw_path = value.partition("=")
        controller = controller.strip().lower()
        if not separator or not controller or not raw_path.strip():
            raise ValueError("--model must use CONTROLLER=PATH")
        if controller in result:
            raise ValueError(f"duplicate --model entry for {controller}")
        result[controller] = Path(raw_path.strip())
    return result


def _run_benchmark(args: argparse.Namespace) -> int:
    from aidrbench.evaluation.hourly_benchmark import run_hourly_benchmark

    summary = run_hourly_benchmark(
        config=args.config,
        controllers=tuple(args.controllers),
        seeds=tuple(args.seeds),
        output_directory=args.save,
        model_paths=_parse_model_paths(args.model),
    )
    _print_summary(summary)
    return 0


def _run_plot(args: argparse.Namespace) -> int:
    from aidrbench.evaluation.plots import plot_hourly_results

    summary = plot_hourly_results(
        args.input,
        args.output,
        controllers=args.controllers,
        seed=args.seed,
        include_clearance_tail=args.include_clearance_tail,
    )
    _print_summary(summary)
    return 0


def _run_certify(args: argparse.Namespace) -> int:
    if args.certification_command == "select":
        if args.controller is None or not args.durations or args.output is None:
            raise ValueError("certify select requires --controller, --durations, and --output")
        from aidrbench.evaluation.certification import select_firm_capacity_on_validation
        from aidrbench.evaluation.protocol import validate_hourly_experiment_protocol

        protocol = validate_hourly_experiment_protocol(args.protocol_manifest)
        if not protocol["valid"]:
            raise ValueError("protocol manifest is invalid; cannot select a capacity")
        summary = select_firm_capacity_on_validation(
            protocol_manifest=args.protocol_manifest,
            controller=args.controller,
            model_path=args.model,
            durations_h=args.durations,
            notices_h=args.notices,
            candidate_reduction_fractions=args.candidate_fractions,
            output_directory=args.output,
            search_method=args.search,
            binary_iterations=args.binary_iterations,
        )
        _print_summary(summary)
        return 0
    if args.certification_command == "locked-test":
        if args.selection is None or args.output is None:
            raise ValueError("certify locked-test requires --selection and --output")
        from aidrbench.evaluation.certification import evaluate_selected_capacity_on_locked_test
        from aidrbench.evaluation.protocol import validate_hourly_experiment_protocol

        protocol = validate_hourly_experiment_protocol(args.protocol_manifest)
        if not protocol["valid"]:
            raise ValueError("protocol manifest is invalid; cannot evaluate the locked test split")
        summary = evaluate_selected_capacity_on_locked_test(
            selection_path=args.selection,
            output_directory=args.output,
            expected_protocol_manifest=args.protocol_manifest,
        )
        _print_summary(summary)
        return 0
    if args.controller is None or not args.durations or args.episodes is None or args.save is None:
        raise ValueError("certify requires --controller, --durations, --episodes, and --save")
    from aidrbench.evaluation.certification import (
        certify_firm_flexibility,
        save_flexibility_certificate,
    )
    from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria

    if args.episodes <= 0:
        raise ValueError("--episodes must be positive")
    criteria = FirmFlexibilityCriteria(
        reliability_target=args.reliability,
        confidence_level=args.confidence,
        min_delivery_ratio=args.min_delivery_ratio,
        min_interval_delivery_ratio=args.min_interval_delivery_ratio,
        max_deadline_miss_rate=args.max_deadline_miss_rate,
        max_rebound_ratio=args.max_rebound_ratio,
        min_window_peak_relief_fraction=args.min_window_peak_relief_fraction,
        max_terminal_backlog_fraction=args.max_terminal_backlog_fraction,
    )
    output = Path(args.save)
    certificate_rows: list[dict[str, object]] = []
    saved_paths: dict[str, dict[str, str]] = {}
    notices_h = args.notices or (0,)
    for duration_h in args.durations:
        for notice_h in notices_h:
            certificate, candidates, outcomes = certify_firm_flexibility(
                config=args.config,
                controller=args.controller,
                model_path=args.model,
                duration_h=duration_h,
                notice_h=notice_h,
                candidate_reduction_fractions=args.candidate_fractions,
                seeds=tuple(range(1, args.episodes + 1)),
                criteria=criteria,
                search_method=args.search,
                binary_iterations=args.binary_iterations,
            )
            event_sequence = "-".join(
                str(value) for value in certificate.event_start_hours
            )
            certificate_key = (
                f"duration_{duration_h}h_notice_{notice_h}h_events_{event_sequence}"
            )
            saved_paths[certificate_key] = save_flexibility_certificate(
                certificate,
                candidates,
                outcomes,
                criteria,
                output / certificate_key,
            )
            certificate_rows.append(asdict(certificate))
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "certificates.parquet"
    pd.DataFrame.from_records(certificate_rows).to_parquet(summary_path, index=False)
    manifest_path = output / "certification.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": args.config,
                "controller": args.controller,
                "model": args.model,
                "criteria": criteria.as_dict(),
                "episodes": args.episodes,
                "candidate_fractions": list(args.candidate_fractions),
                "search": args.search,
                "certificates": saved_paths,
                "summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _print_summary(
        {
            "controller": args.controller,
            "certificates": certificate_rows,
            "summary": str(summary_path),
            "manifest": str(manifest_path),
        }
    )
    return 0


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


def _run_stress_test(args: argparse.Namespace) -> int:
    from aidrbench.evaluation.stress_test import (
        run_repeated_event_stress_test,
        save_repeated_event_stress_test,
    )

    if args.episodes <= 0:
        raise ValueError("--episodes must be positive")
    criteria = _firm_criteria_from_args(args)
    output = Path(args.save)
    all_certificates: list[pd.DataFrame] = []
    all_outcomes: list[pd.DataFrame] = []
    scenario_paths: dict[str, dict[str, str]] = {}
    for events_per_day, gap_h, duration_h in product(
        args.events_per_day,
        args.inter_event_gap_hours,
        args.duration_hours,
    ):
        certificates, outcomes = run_repeated_event_stress_test(
            config=args.config,
            controllers=tuple(args.controllers),
            model_paths=_parse_model_paths(args.model),
            events_per_day=events_per_day,
            inter_event_gap_h=gap_h,
            duration_h=duration_h,
            candidate_reduction_fractions=args.candidate_fractions,
            seeds=tuple(range(1, args.episodes + 1)),
            criteria=criteria,
        )
        scenario_key = f"events_{events_per_day}_gap_{gap_h}h_duration_{duration_h}h"
        scenario_paths[scenario_key] = save_repeated_event_stress_test(
            certificates,
            outcomes,
            output_directory=output / scenario_key,
        )
        all_certificates.append(certificates)
        all_outcomes.append(outcomes)
    output.mkdir(parents=True, exist_ok=True)
    certificates_path = output / "event_certificates.parquet"
    outcomes_path = output / "event_outcomes.parquet"
    pd.concat(all_certificates, ignore_index=True).to_parquet(certificates_path, index=False)
    pd.concat(all_outcomes, ignore_index=True).to_parquet(outcomes_path, index=False)
    manifest_path = output / "stress_test.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": args.config,
                "controllers": list(args.controllers),
                "model_paths": _parse_model_paths(args.model),
                "criteria": criteria.as_dict(),
                "episodes": args.episodes,
                "candidate_fractions": list(args.candidate_fractions),
                "scenarios": scenario_paths,
                "event_certificates": str(certificates_path),
                "event_outcomes": str(outcomes_path),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    _print_summary(
        {
            "scenarios": len(scenario_paths),
            "event_certificates": str(certificates_path),
            "event_outcomes": str(outcomes_path),
            "manifest": str(manifest_path),
        }
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "project-check":
        report = check_project(args.root)
        print(format_report(report))
        return 0 if report.ok else 1
    if args.command == "show-actions":
        for action_id, components in enumerate(all_actions()):
            print(f"{action_id:2d}: {components}")
        return 0
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
    if args.command == "fleet":
        try:
            return _run_fleet(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "hil":
        try:
            return _run_hil(args)
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
    if args.command == "train":
        try:
            return _run_train(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "evaluate":
        try:
            return _run_evaluate(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "benchmark":
        try:
            return _run_benchmark(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.command == "plot":
        try:
            return _run_plot(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
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
    if args.command == "stress-test":
        try:
            return _run_stress_test(args)
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
