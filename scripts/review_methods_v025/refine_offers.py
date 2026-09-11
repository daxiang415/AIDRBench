"""Local prospective refinement; reuses, but never edits, the frozen controller/runner."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "operating_tradeoffs_2026-09-09"))
import run_tradeoffs as r  # noqa: E402 -- original study module uses the path above
import select_and_analyse as a  # noqa: E402 -- original study module uses the path above

PARENT = r.OUT
OUT = ROOT / "results/nature_mainline/commitment_mechanisms_v1"
SOURCE = ROOT / "manuscript/source_data/nature_commitment_mechanisms_v1"
LOCK = HERE / "refinement_protocol.json"
GRID = {"H8P16": [0.5, 0.55, 0.6, 0.65, 0.7, 0.75], "H4P16": [0.75, 0.8, 0.85, 0.9, 0.95, 1.0]}


def configure():
    r.OUT = OUT
    r.PROTOCOL = LOCK
    r.VARIANTS = [dict(name="u65d100g10", utilization=0.65, slack_multiplier=1.0, gpu_share=0.1)]


configure()


def task(seed, role, p, f):
    return dict(
        role=role,
        variant=r.REFERENCE_VARIANT,
        seed=seed,
        program=p,
        fraction=float(f),
        kind="repeated",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["freeze", "development", "select", "confirmation", "analyse"])
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True)
    if args.stage == "freeze":
        assert not LOCK.exists() and not (OUT / "runs").exists()
        r.m.save(
            LOCK,
            dict(
                frozen_at_utc=datetime.now(UTC).isoformat(),
                design_sha256=r.m.sha(HERE / "DESIGN_ZH.md"),
                runner_sha256=r.m.sha(__file__),
                parent_runner_sha256=r.m.sha(r.__file__),
                parent_controller_sha256=r.m.sha(
                    HERE.parent / "repeat_mechanism_2026-09-09/recovery_controller.py"
                ),
                development_seeds=[988000, 988099],
                confirmation_seeds=[989000, 989299],
                reference_capacity_kw=r.REFERENCE,
                grid=GRID,
                selection=(
                    "largest local-grid offer with development one-sided Wilson95"
                    " >= .95; two endpoints; no confirmation reselection"
                ),
                confirmation_comparators={"H4P16": [0.75], "H8P16": [0.5, 0.75]},
                variants=r.VARIANTS,
                clock="unchanged phase-matched four-call series",
                scope=(
                    "follow-up conditional model study, pointwise confidence; fin"
                    "ite local grid, no physical boundary claim"
                ),
            ),
        )
        print("Frozen", r.m.sha(LOCK), flush=True)
        return
    protocol = json.loads(LOCK.read_text())
    assert protocol["runner_sha256"] == r.m.sha(__file__) and protocol[
        "parent_runner_sha256"
    ] == r.m.sha(r.__file__)
    selection = HERE / "refinement_selection.json"
    if args.stage == "select":
        assert not selection.exists() and not (OUT / "runs/confirmation").exists()
        data = pd.read_csv(OUT / "development_ledgers.csv")
        summary = a.summarize(data)
        summary.to_csv(SOURCE / "refinement_development_summary.csv", index=False)
        rows = []
        for p in GRID:
            for endpoint in ["success_1pct", "success_zero"]:
                g = summary[
                    (summary.program == p) & (summary.endpoint == endpoint) & summary.qualified
                ].sort_values("fraction")
                chosen = None if g.empty else g.iloc[-1]
                rows.append(
                    dict(
                        variant=r.REFERENCE_VARIANT,
                        program=p,
                        endpoint=endpoint,
                        selected_fraction=None if chosen is None else float(chosen.fraction),
                        selected_capacity_kw=None if chosen is None else float(chosen.capacity_kw),
                        development_successes=None if chosen is None else int(chosen.successes),
                    )
                )
        tasks = []
        for seed in range(989000, 989300):
            for p in GRID:
                values = set(protocol["confirmation_comparators"][p]) | {
                    x["selected_fraction"]
                    for x in rows
                    if x["program"] == p and x["selected_fraction"] is not None
                }
                tasks.extend(task(seed, "confirmation", p, f) for f in sorted(values))
        r.m.save(
            selection,
            dict(
                frozen_at_utc=datetime.now(UTC).isoformat(),
                protocol_sha256=r.m.sha(LOCK),
                development_sha256=r.m.sha(OUT / "development_ledgers.csv"),
                confirmation_not_yet_run=True,
                selections=rows,
                confirmation_tasks=tasks,
            ),
        )
        print(pd.DataFrame(rows).to_string(index=False), flush=True)
        return
    if args.stage == "analyse":
        summary = a.summarize(pd.read_csv(OUT / "confirmation_ledgers.csv"))
        summary.to_csv(SOURCE / "refinement_confirmation_summary.csv", index=False)
        sel = json.loads(selection.read_text())
        assert sel["protocol_sha256"] == r.m.sha(LOCK)
        rows = []
        for x in sel["selections"]:
            y = dict(x)
            if x["selected_fraction"] is None:
                y.update(confirmation_successes=None, confirmation_lower=None, offerable=False)
            else:
                g = summary[
                    (summary.program == x["program"])
                    & (summary.endpoint == x["endpoint"])
                    & np.isclose(summary.fraction, x["selected_fraction"])
                ]
                assert len(g) == 1
                y.update(
                    confirmation_successes=int(g.successes.iloc[0]),
                    confirmation_lower=float(g.wilson_lower.iloc[0]),
                    offerable=bool(g.qualified.iloc[0]),
                )
            rows.append(y)
        pd.DataFrame(rows).to_csv(SOURCE / "refinement_selected_confirmed.csv", index=False)
        print(pd.DataFrame(rows).to_string(index=False), flush=True)
        return
    role = args.stage
    lo, hi = protocol[role + "_seeds"]
    seeds = range(lo, hi + 1)
    tasks = (
        [task(s, role, p, f) for s in seeds for p, values in GRID.items() for f in values]
        if role == "development"
        else json.loads(selection.read_text())["confirmation_tasks"]
    )
    receipts = r.m.parallel(
        r.freeze_seed, [(role, s) for s in seeds], args.workers, "freeze " + role
    )
    r.m.save(OUT / f"{role}_baseline_receipts.json", receipts)
    results = r.m.parallel(r.evaluate, tasks, args.workers, role)
    pd.DataFrame([x["row"] for x in results]).sort_values(["program", "fraction", "seed"]).to_csv(
        OUT / f"{role}_ledgers.csv", index=False
    )
    print("Finished", role, len(results), flush=True)


if __name__ == "__main__":
    main()
