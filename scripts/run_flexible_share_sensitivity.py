"""Run each resumable stage of the nonlocked flexible-share analysis."""

import argparse

from aidrbench.evaluation.flexible_share_sensitivity import run_stage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["freeze", "pi", "causal", "export"])
    parser.add_argument("--spec", default="configs/sensitivity/nature_flexible_share_v1.yaml")
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    run_stage(args.spec, stage=args.stage, workers=args.workers)


if __name__ == "__main__":
    main()
