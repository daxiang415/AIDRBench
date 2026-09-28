"""Run one frozen stage of the repeated-capacity extension."""

from __future__ import annotations

import argparse
from pathlib import Path

from aidrbench.evaluation.repeat_capacity import OUTPUT, run_stage

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=["freeze-development", "development", "freeze-confirmation", "confirmation"],
    )
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    run_stage(args.stage, workers=args.workers, output=args.output, pilot=args.pilot)
