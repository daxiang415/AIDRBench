"""AIDRBench command-line interface."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from aidrbench._version import __version__
from aidrbench.envs.actions import all_actions
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aidrbench", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("project-check", help="validate the repository skeleton")
    check.add_argument("--root", default=".", help="repository root (default: current directory)")
    subparsers.add_parser("show-actions", help="print the 27 discrete V0 actions")
    _add_data_parsers(subparsers)
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
        except (FileNotFoundError, KeyError, ValueError) as error:
            parser.error(str(error))
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
