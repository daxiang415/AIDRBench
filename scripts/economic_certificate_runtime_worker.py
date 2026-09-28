"""Replay one economic ledger group inside a certificate-pinned source tree.

This file is deliberately executed as a script, not imported as part of the
``aidrbench`` package.  The parent process supplies ``PYTHONPATH`` pointing to
the source tree recorded by the causal certificate, so every environment and
controller import below resolves from that immutable tree.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.frozen_causal_certificate import _environment_document
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

_RUNTIME_DISTRIBUTIONS = (
    "cvxpy",
    "gymnasium",
    "highspy",
    "numpy",
    "osqp",
    "pandas",
    "pyarrow",
    "pydantic",
    "pyyaml",
    "scipy",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_frame(frame: Any, path: Path) -> dict[str, object]:
    frame.to_parquet(path, index=False)
    return {"path": path.name, "row_count": len(frame), "sha256": _sha256(path)}


def _environment(
    artifact: Any,
    *,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    event_id: int,
) -> HourlyCommunityAIDemandResponseEnv:
    return HourlyCommunityAIDemandResponseEnv(
        _environment_document(
            artifact,
            duration_h=duration_h,
            notice_h=notice_h,
            requested_reduction_kw=requested_reduction_kw,
            event_id=event_id,
        )
    )


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: worker INPUT.json OUTPUT_DIRECTORY")
    input_path = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    if output.exists():
        raise FileExistsError(output)
    task = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(task, dict):
        raise ValueError("version-pinned replay task must be a JSON object")

    expected_source_root = Path(os.environ["AIDRBENCH_CERTIFICATE_SOURCE_ROOT"]).resolve()
    import aidrbench

    imported_package = Path(aidrbench.__file__).resolve()
    if expected_source_root not in imported_package.parents:
        raise RuntimeError(
            "aidrbench was not imported from the declared certificate source tree: "
            f"{imported_package}"
        )
    for module_name, module in sorted(sys.modules.items()):
        if module_name != "aidrbench" and not module_name.startswith("aidrbench."):
            continue
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            continue
        resolved_module = Path(module_file).resolve()
        if expected_source_root not in resolved_module.parents:
            raise RuntimeError(
                f"mixed aidrbench runtime detected: {module_name} -> {resolved_module}"
            )

    artifact = load_frozen_hourly_scenario(str(task["artifact_path"]))
    if (
        artifact.scenario_id != str(task["scenario_id"])
        or artifact.scenario_hash != str(task["scenario_hash"])
        or artifact.episode_seed != int(task["episode_seed"])
    ):
        raise ValueError("version-pinned task identity does not match the frozen artifact")

    controller_config = Path(str(task["controller_config"]))
    if _sha256(controller_config) != str(task["controller_config_sha256"]):
        raise ValueError("controller configuration changed before version-pinned replay")
    specification = load_robust_mpc_specification(controller_config)
    duration_h = int(task["duration_h"])
    notice_h = int(task["notice_h"])
    event_id = int(task["event_id"])
    ceiling_kw = float(task["technical_ceiling_kw"])
    fractions = tuple(float(value) for value in task["offer_fractions"])

    output.mkdir(parents=False, exist_ok=False)
    no_dr_environment = _environment(
        artifact,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=ceiling_kw,
        event_id=event_id,
    )
    no_dr, _ = rollout_hourly_episode(
        no_dr_environment,
        make_hourly_controller("no_control"),
        seed=artifact.episode_seed,
    )
    no_dr_record = _write_frame(no_dr, output / "no_dr.parquet")

    controlled_records: list[dict[str, object]] = []
    for index, fraction in enumerate(fractions):
        environment = _environment(
            artifact,
            duration_h=duration_h,
            notice_h=notice_h,
            requested_reduction_kw=ceiling_kw * fraction,
            event_id=event_id,
        )
        controlled, _ = rollout_hourly_episode(
            environment,
            make_hourly_controller(
                "robust_mpc",
                robust_mpc_specification=specification,
            ),
            seed=artifact.episode_seed,
        )
        events = [event for event in environment.event_manifest if int(event.event_id) == event_id]
        if len(events) != 1:
            raise RuntimeError(f"expected exactly one event with ID {event_id}")
        event = events[0]
        frame_record = _write_frame(controlled, output / f"controlled_{index:03d}.parquet")
        controlled_records.append(
            {
                **frame_record,
                "offer_fraction": fraction,
                "event": {
                    "event_id": int(event.event_id),
                    "start_hour": int(event.start_hour),
                    "stop_hour": int(event.stop_hour),
                    "recovery_stop_hour": int(event.recovery_stop_hour),
                    "requested_reduction_kw": float(event.requested_reduction_kw),
                    "source_event_id": str(event.source_event_id),
                    "notice_hours": float(event.notice_hours),
                },
                "recovery_tolerance_gpu_h": (
                    float(environment.config.recovery_backlog_tolerance_fraction)
                    * float(environment.power_model.flexible_capacity_gpu_h)
                ),
                "timestep_hours": float(environment.config.timestep_hours),
            }
        )

    manifest: dict[str, object] = {
        "schema_version": 1,
        "runtime_mode": "certificate_git_commit",
        "runtime_git_commit": str(task["replay_git_commit"]),
        "runtime_git_tree": str(task["replay_git_tree"]),
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "duration_h": duration_h,
        "notice_h": notice_h,
        "event_id": event_id,
        "technical_ceiling_kw": ceiling_kw,
        "offer_fractions": list(fractions),
        "controller_config_sha256": str(task["controller_config_sha256"]),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "dependency_versions": {
            name: importlib.metadata.version(name) for name in _RUNTIME_DISTRIBUTIONS
        },
        "no_dr": no_dr_record,
        "controlled": controlled_records,
    }
    (output / "worker_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
