"""Restore one complete frozen input from the supplied deduplicated data.

Example: python restore_scenario.py --data ../03_data --case f10 --seed 960000
Requires the supplied pandas/pyarrow versions for identical Parquet bytes.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def restore(data, case, seed, output, role="confirmation"):
    source = Path(data) / "recovery_inputs"
    index = pd.read_csv(source / "reconstruction_index.csv", float_precision="round_trip")
    match = index[(index.case == case) & (index.seed == seed) & (index.role == role)]
    if len(match) != 1:
        raise ValueError("No unique saved scenario for this case, role and seed")
    row = match.iloc[0]
    template = source / row.template_directory
    metadata = json.loads((source / row.manifest).read_text())
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    output.mkdir(parents=True)
    arrivals = pd.read_parquet(template / "arrivals.parquet")
    factors = {
        "training": row.training_work_multiplier,
        "offline_inference": row.offline_work_multiplier,
    }
    arrivals["arrival_gpu_h"] *= arrivals.job_class.map(factors)
    arrivals.to_parquet(output / "arrivals.parquet", index=False)
    shutil.copyfile(template / "community.parquet", output / "community.parquet")
    for name in ["environment_config.yaml", "baseline.parquet"]:
        shutil.copyfile(source / row.scenario_files / name, output / name)
    for name, digest in metadata["files"].items():
        if sha(output / name) != digest:
            raise ValueError(
                f"Restored file differs from original: {name}; use pinned pandas/pyarrow"
            )
    shutil.copyfile(source / row.manifest, output / "metadata.json")
    return {
        "case": case,
        "seed": seed,
        "role": role,
        "scenario_hash": metadata["scenario_hash"],
        "all_file_hashes_match": True,
        "path": str(output),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--case", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--role", default="confirmation", choices=["development", "confirmation"])
    ap.add_argument("--output", type=Path, default=Path("RESTORED_SCENARIO"))
    a = ap.parse_args()
    print(json.dumps(restore(a.data, a.case, a.seed, a.output, a.role), indent=2))


if __name__ == "__main__":
    main()
