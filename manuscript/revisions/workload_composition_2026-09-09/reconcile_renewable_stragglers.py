"""Apply the frozen numerical acceptance rule after original workers stop."""

import argparse
import json
from pathlib import Path

import run_study_final as m

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--originals-stopped", action="store_true")
    args = ap.parse_args()
    protocol_path = HERE / "solver_acceleration_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    assert m.sha(HERE / "accelerate_renewable_stragglers.py") == protocol["runner_sha256"]
    assert m.sha(m.ROOT / "src/aidrbench/evaluation/renewable_integration.py") == protocol["model_source_sha256"]
    choices = []
    for item in protocol["cases"]:
        case, seed = item["case"], item["seed"]
        cache = m.OUT / "renewable" / case / f"{seed}.json"
        if cache.is_file():
            rows = json.loads(cache.read_text())
            assert len(rows) == 8 and all(r["status"] == "optimal" for r in rows)
            choices.append(dict(case=case, seed=seed, source="original", cache_sha256=m.sha(cache)))
            continue
        candidates = []
        for path in (m.OUT / "numerical_multistart" / case / str(seed)).glob("*.json"):
            receipt = json.loads(path.read_text())
            if receipt["status"] != "OPTIMAL_COMPLETE":
                continue
            assert receipt["protocol_sha256"] == m.sha(protocol_path)
            assert receipt["solver_random_seed"] in protocol["solver_random_seeds"]
            assert len(receipt["rows"]) == 8
            assert all(row["status"] == "optimal" for row in receipt["rows"])
            for stage in receipt["stages"]:
                assert stage["status"] == "optimal"
                if stage["mip"]:
                    assert stage["gap"] <= 1e-4 + 1e-10 or abs(stage["primal"] - stage["dual"]) <= 1e-6 + 1e-9
            candidates.append((receipt["finished_unix"], path, receipt))
        assert candidates, f"No complete optimal coverage for {case}/{seed}"
        _, path, receipt = min(candidates, key=lambda value: value[0])
        choices.append(dict(case=case, seed=seed, source="multistart", receipt=str(path.relative_to(m.ROOT)), receipt_sha256=m.sha(path), solver_random_seed=receipt["solver_random_seed"]))
    assert args.originals_stopped, "Stop original worker sessions before reconciling caches."
    for choice in choices:
        if choice["source"] == "multistart":
            cache = m.OUT / "renewable" / choice["case"] / f'{choice["seed"]}.json'
            assert not cache.exists()
            receipt = json.loads((m.ROOT / choice["receipt"]).read_text())
            m.save(cache, receipt["rows"])
            choice["cache_sha256"] = m.sha(cache)
    report = dict(status="PASS", rule=protocol["acceptance"], protocol_sha256=m.sha(protocol_path), choices=choices, used_alternate_groups=sum(c["source"] == "multistart" for c in choices))
    m.save(HERE / "numerical_reconciliation.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
