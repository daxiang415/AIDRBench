"""Build an event-level technical-economic ledger from paired frozen replays.

The no-DR reference is an explicit full-capacity ``no_control`` replay of the
same frozen scenario, not an inferred baseline or a fleet depreciation proxy.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import math
import multiprocessing
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import (
    RobustMPCSpecification,
    load_robust_mpc_specification,
)
from aidrbench.data.frozen_scenarios import FrozenHourlyScenario, load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.economics.specification import (
    EconomicParticipationSpecification,
    load_economic_participation_specification,
    scenario_set_sha256,
    verify_physical_input_hashes,
)
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv, HourlyDREvent
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria, derive_event_outcomes
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode

_ROOT = Path(__file__).resolve().parents[3]
_LEDGER_COLUMNS = (
    "evaluation_split",
    "scenario_id",
    "scenario_hash",
    "episode_seed",
    "event_id",
    "event_start_hour",
    "event_stop_hour",
    "recovery_stop_hour",
    "duration_h",
    "notice_h",
    "reliability_target",
    "confidence_level",
    "technical_capacity_ceiling_kw",
    "offer_fraction_of_technical_ceiling",
    "candidate_reduction_kw",
    "technical_success",
    "technical_failure_reasons",
    "delivery_ratio",
    "minimum_interval_delivery_ratio",
    "delivered_energy_kwh",
    "capped_delivered_energy_kwh",
    "shortfall_energy_kwh",
    "deferred_gpu_h",
    "recovered_within_recovery_window_gpu_h",
    "recovered_through_episode_end_gpu_h",
    "unrecovered_at_recovery_stop_gpu_h_proxy",
    "unrecovered_at_episode_end_gpu_h_proxy",
    "missed_gpu_h",
    "backlog_at_recovery_stop_gpu_h",
    "terminal_backlog_gpu_h",
    "incremental_backlog_area_within_recovery_gpu_h_h",
    "incremental_backlog_area_through_episode_end_gpu_h_h",
    "incremental_energy_within_recovery_kwh",
    "incremental_energy_through_episode_end_kwh",
    "event_peak_delta_kw",
    "recovery_peak_delta_kw",
    "checkpoint_count_or_proxy",
    "checkpoint_proxy_method",
    "paired_pcc_match_max_abs_kw",
    "controlled_work_conservation_error_gpu_h",
    "no_dr_work_conservation_error_gpu_h",
)
_INTERVAL_COLUMNS = (
    "scenario_id",
    "scenario_hash",
    "episode_seed",
    "event_id",
    "duration_h",
    "notice_h",
    "candidate_reduction_kw",
    "hour",
    "relative_hour",
    "event_active",
    "recovery_active",
    "within_recovery_window",
    "clearance_tail_active",
    "controlled_pcc_power_kw",
    "no_dr_pcc_power_kw",
    "controlled_executed_gpu_h",
    "no_dr_executed_gpu_h",
    "controlled_backlog_gpu_h",
    "no_dr_backlog_gpu_h",
    "controlled_missed_gpu_h",
    "no_dr_missed_gpu_h",
    "pcc_delta_kw",
    "execution_delta_gpu_h",
    "backlog_delta_gpu_h",
)


@dataclass(frozen=True)
class _ReplayGroupTask:
    """All offer fractions sharing one physical no-control counterfactual."""

    artifact_path: str
    scenario_id: str
    scenario_hash: str
    episode_seed: int
    controller_config: str
    duration_h: int
    notice_h: int
    event_id: int
    technical_ceiling_kw: float
    offer_fractions: tuple[float, ...]
    criteria_document: dict[str, float]
    paired_pcc_tolerance_kw: float
    work_conservation_tolerance_gpu_h: float
    include_interval_ledger: bool
    controller_config_sha256: str = ""
    replay_runtime_mode: str = "current_worktree"
    replay_git_commit: str | None = None
    replay_git_tree: str | None = None
    runtime_source_root: str | None = None

    def identity_document(self) -> dict[str, object]:
        return {
            "artifact_path": self.artifact_path,
            "scenario_id": self.scenario_id,
            "scenario_hash": self.scenario_hash,
            "episode_seed": self.episode_seed,
            "controller_config": self.controller_config,
            "duration_h": self.duration_h,
            "notice_h": self.notice_h,
            "event_id": self.event_id,
            "technical_ceiling_kw": self.technical_ceiling_kw,
            "offer_fractions": list(self.offer_fractions),
            "criteria": self.criteria_document,
            "paired_pcc_tolerance_kw": self.paired_pcc_tolerance_kw,
            "work_conservation_tolerance_gpu_h": self.work_conservation_tolerance_gpu_h,
            "include_interval_ledger": self.include_interval_ledger,
            "controller_config_sha256": self.controller_config_sha256,
            "replay_runtime_mode": self.replay_runtime_mode,
            "replay_git_commit": self.replay_git_commit,
            "replay_git_tree": self.replay_git_tree,
        }

    @property
    def task_sha256(self) -> str:
        payload = json.dumps(
            self.identity_document(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _git_state() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "working_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def _checkpoint_workspace_for_output(output: Path) -> Path:
    """Return the sole resumable-workspace path allowed for one ledger output."""

    normalized_output = output.resolve(strict=False)
    if normalized_output.name in {"", ".", ".."}:
        raise ValueError("economic ledger output must name a directory")
    return normalized_output.parent / f".{normalized_output.name}.economic-ledger-work"


def _remove_published_checkpoint_workspace_or_raise(output: Path) -> None:
    """Remove only this output's exact checkpoint workspace, including read-only snapshots.

    Certificate-runtime snapshots deliberately remove all write bits.  A normal
    ``shutil.rmtree(..., ignore_errors=True)`` therefore leaves the resumable
    workspace behind after a successful publish.  The retry handler widens
    permissions only on non-symlink descendants of the workspace derived from
    ``output``; it never chmods the parent directory or an arbitrary caller
    path.  A cleanup failure remains visible because the published ledger is
    valid but its resumable workspace needs explicit inspection.
    """

    workspace = _checkpoint_workspace_for_output(output)
    if not os.path.lexists(workspace):
        return
    root_mode = workspace.lstat().st_mode
    if stat.S_ISLNK(root_mode) or not stat.S_ISDIR(root_mode):
        raise RuntimeError(
            "refusing to clean a non-directory economic ledger checkpoint workspace: "
            f"{workspace}"
        )

    workspace_root = workspace.absolute()

    def _onerror(function: Any, path: str, _exc_info: object) -> None:
        candidate = Path(path).absolute()
        try:
            candidate.relative_to(workspace_root)
        except ValueError as error:
            raise RuntimeError(
                "economic ledger cleanup attempted to modify a path outside its exact "
                f"checkpoint workspace: {candidate}"
            ) from error

        # Deleting a read-only file requires its parent directory to be
        # writable; walk only from the failed path back to the exact workspace.
        for target in (candidate, *candidate.parents):
            if target == workspace_root.parent:
                break
            try:
                mode = target.lstat().st_mode
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(mode):
                raise RuntimeError(
                    "refusing to chmod a symbolic link while cleaning the economic "
                    f"ledger workspace: {target}"
                )
            writable_mode = mode | stat.S_IWUSR
            if stat.S_ISDIR(mode):
                writable_mode |= stat.S_IRUSR | stat.S_IXUSR
            try:
                os.chmod(target, writable_mode)
            except OSError as error:
                raise RuntimeError(
                    "could not make an exact economic ledger workspace path writable: "
                    f"{target}"
                ) from error
        function(path)

    try:
        shutil.rmtree(workspace, onerror=_onerror)
    except Exception as error:
        raise RuntimeError(
            "published economic ledger but could not clean its exact checkpoint workspace; "
            f"inspect and remove it manually: {workspace}"
        ) from error
    if os.path.lexists(workspace):
        raise RuntimeError(
            "published economic ledger but checkpoint workspace still exists after cleanup: "
            f"{workspace}"
        )


def _discover_artifacts(
    specification: EconomicParticipationSpecification,
    *,
    validation_scenario_hashes: tuple[str, ...],
    locked_id_scenario_hashes: frozenset[str],
) -> list[FrozenHourlyScenario]:
    root = Path(specification.technical.scenario_directory)
    if root.is_symlink():
        raise ValueError("economic scenario directory may not be a symbolic link")
    root = root.resolve()
    if any("locked" in part.lower() for part in root.parts):
        raise ValueError("economic screening may not resolve to a locked scenario directory")
    if not root.is_dir():
        raise FileNotFoundError(root)
    artifact_directories: list[Path] = []
    for child in sorted(root.iterdir()):
        if child.is_symlink():
            raise ValueError("economic scenario artifacts may not be symbolic links")
        resolved = child.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError("economic scenario artifact escapes the declared root") from error
        if any("locked" in part.lower() for part in resolved.parts):
            raise ValueError("economic screening may not resolve to a locked scenario artifact")
        if resolved.is_dir() and (resolved / "metadata.json").is_file():
            for payload_name in (
                "metadata.json",
                "environment_config.yaml",
                "community.parquet",
                "arrivals.parquet",
                "baseline.parquet",
            ):
                payload = resolved / payload_name
                if payload.is_symlink():
                    raise ValueError("economic frozen-scenario payloads may not be symbolic links")
                try:
                    payload.resolve().relative_to(resolved)
                except ValueError as error:
                    raise ValueError("economic scenario payload escapes its artifact") from error
            artifact_directories.append(resolved)
    artifacts = [load_frozen_hourly_scenario(path) for path in artifact_directories]
    if len(artifacts) != specification.technical.expected_scenario_count:
        raise ValueError("economic scenario count does not match the frozen protocol")
    first, last = specification.technical.expected_episode_seed_range
    expected_seeds = set(range(first, last + 1))
    if {artifact.episode_seed for artifact in artifacts} != expected_seeds:
        raise ValueError("economic scenario seeds do not match the frozen protocol")
    if len({artifact.scenario_hash for artifact in artifacts}) != len(artifacts):
        raise ValueError("economic scenarios must have unique hashes")
    observed_hashes = tuple(artifact.scenario_hash for artifact in artifacts)
    if observed_hashes != validation_scenario_hashes:
        raise ValueError(
            "economic scenarios do not match the ordered validation allowlist from selection"
        )
    if set(observed_hashes).intersection(locked_id_scenario_hashes):
        raise ValueError("economic validation scenarios overlap the locked-ID certificate set")
    observed_set_hash = scenario_set_sha256(
        [
            {
                "episode_seed": artifact.episode_seed,
                "scenario_id": artifact.scenario_id,
                "scenario_hash": artifact.scenario_hash,
            }
            for artifact in artifacts
        ]
    )
    if observed_set_hash != specification.technical.scenario_set_sha256:
        raise ValueError("economic scenario hash set does not match the frozen protocol")
    return artifacts


def _validate_frozen_power_provenance(
    artifacts: list[FrozenHourlyScenario],
    *,
    technical_provenance: Mapping[str, object],
) -> dict[str, object]:
    expected_power_model = technical_provenance.get("power_model_sha256")
    expected_calibration = technical_provenance.get("calibration_artifact_sha256")
    if not isinstance(expected_power_model, str) or not isinstance(expected_calibration, str):
        raise ValueError("validation receipt does not bind power/calibration provenance")
    calibration_paths: set[str] = set()
    for artifact in artifacts:
        power_model = artifact.metadata.get("power_model")
        hardware = artifact.config_document.get("hardware")
        if not isinstance(power_model, Mapping) or not isinstance(hardware, Mapping):
            raise ValueError("frozen validation artifact has no power-model provenance")
        if (
            power_model.get("sha256") != expected_power_model
            or power_model.get("calibration_artifact_sha256") != expected_calibration
        ):
            raise ValueError("frozen validation power model differs from its receipt")
        raw_calibration_path = hardware.get("calibration_artifact")
        if not isinstance(raw_calibration_path, str):
            raise ValueError("frozen validation config has no calibration artifact path")
        calibration_relative_path = Path(raw_calibration_path)
        if calibration_relative_path.is_absolute() or ".." in calibration_relative_path.parts:
            raise ValueError("frozen calibration artifact path must be repository-relative")
        calibration_paths.add(calibration_relative_path.as_posix())
    if len(calibration_paths) != 1:
        raise ValueError("frozen validation artifacts do not share one calibration artifact")
    calibration_repository_path = next(iter(calibration_paths))
    replay_commit = technical_provenance.get("replay_git_commit")
    if isinstance(replay_commit, str):
        calibration_raw_sha256 = _git_blob_sha256(replay_commit, calibration_repository_path)
        calibration_bytes = subprocess.run(
            ["git", "show", f"{replay_commit}:{calibration_repository_path}"],
            cwd=_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        calibration_document = yaml.safe_load(calibration_bytes)
    else:
        current_calibration = _relative_repository_path(calibration_repository_path)
        calibration_raw_sha256 = sha256_file(current_calibration)
        calibration_document = yaml.safe_load(current_calibration.read_bytes())
    if (
        not isinstance(calibration_document, dict)
        or calibration_document.get("artifact_sha256") != expected_calibration
    ):
        raise ValueError("calibration artifact does not match frozen power-model provenance")
    return {
        "calibration_artifact_path": calibration_repository_path,
        "calibration_raw_sha256": calibration_raw_sha256,
        "calibration_artifact_sha256": expected_calibration,
        "power_model_sha256": expected_power_model,
    }


def _certificate_capacities(
    specification: EconomicParticipationSpecification,
) -> dict[tuple[int, int], float]:
    path = Path(specification.technical.technical_certificate_path)
    certificate = pd.read_parquet(path)
    required = {
        "duration_h",
        "notice_h",
        "reliability_target",
        "confidence_level",
        "candidate_reduction_kw",
        "certified",
    }
    missing = sorted(required.difference(certificate.columns))
    if missing:
        raise ValueError(f"technical certificate is missing columns: {', '.join(missing)}")
    capacities: dict[tuple[int, int], float] = {}
    for duration_h in specification.technical.duration_hours:
        for notice_h in specification.technical.notice_hours:
            matches = certificate[
                (pd.to_numeric(certificate["duration_h"], errors="raise") == duration_h)
                & (pd.to_numeric(certificate["notice_h"], errors="raise") == notice_h)
                & np.isclose(
                    pd.to_numeric(certificate["reliability_target"], errors="raise"),
                    specification.technical.reliability_target,
                )
                & np.isclose(
                    pd.to_numeric(certificate["confidence_level"], errors="raise"),
                    specification.technical.confidence_level,
                )
                & certificate["certified"].astype(bool)
            ]
            if len(matches) != 1:
                raise ValueError(
                    "economic screening requires exactly one independently certified technical "
                    f"capacity for H={duration_h}, N={notice_h}"
                )
            capacity = float(matches["candidate_reduction_kw"].iloc[0])
            if not math.isfinite(capacity) or capacity <= 0.0:
                raise ValueError("technical certificate has an invalid positive capacity")
            capacities[(duration_h, notice_h)] = capacity
    return capacities


def _relative_repository_path(path: str | Path) -> Path:
    """Resolve an audited code path without allowing it to escape the repository."""

    resolved = (_ROOT / Path(path)).resolve()
    try:
        resolved.relative_to(_ROOT)
    except ValueError as error:
        raise ValueError(f"certificate provenance path escapes repository: {path}") from error
    return resolved


def _resolve_protocol_path(path: str | Path) -> Path:
    """Resolve a protocol path relative to the repository when necessary."""

    candidate = Path(path)
    return candidate.resolve() if candidate.is_absolute() else (_ROOT / candidate).resolve()


def _resolve_git_commit(commit: str) -> tuple[str, str]:
    """Resolve one locally available commit and its tree without fetching."""

    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0 or resolved.stdout.strip() != commit:
        raise ValueError(
            "certificate replay git commit is not available exactly in the local repository; "
            "fetch the repository history before running"
        )
    tree = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit}^{{tree}}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if tree.returncode != 0 or len(tree.stdout.strip()) != 40:
        raise ValueError("certificate replay git tree could not be resolved")
    return commit, tree.stdout.strip()


def _git_blob_sha256(commit: str, repository_path: str) -> str:
    blob = subprocess.run(
        ["git", "show", f"{commit}:{repository_path}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
    )
    if blob.returncode != 0:
        raise ValueError(
            f"certificate replay source is absent from git commit {commit}: {repository_path}"
        )
    return hashlib.sha256(blob.stdout).hexdigest()


def _validate_technical_certificate_provenance(
    specification: EconomicParticipationSpecification,
) -> dict[str, object]:
    """Require the replay runtime to match the fixed causal certificate exactly."""

    manifest_path = _resolve_protocol_path(specification.technical.technical_certificate_manifest)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("technical certificate manifest must be a JSON object")
    if document.get("capacity_layer") != "independent_causal_certificate":
        raise ValueError("economic screening requires an independent causal certificate manifest")
    if document.get("controller") != specification.technical.controller:
        raise ValueError("technical certificate controller does not match the economic protocol")

    summary_path = document.get("summary")
    if not isinstance(summary_path, str):
        raise ValueError("technical certificate manifest is missing its summary path")
    if _resolve_protocol_path(summary_path) != _resolve_protocol_path(
        specification.technical.technical_certificate_path
    ):
        raise ValueError("technical certificate manifest summary does not match the bound parquet")

    selection_path = _resolve_protocol_path(specification.technical.technical_selection_path)
    manifest_selection_path = document.get("selection")
    if (
        not isinstance(manifest_selection_path, str)
        or _resolve_protocol_path(manifest_selection_path) != selection_path
    ):
        raise ValueError("technical certificate does not point to the declared selection")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if not isinstance(selection, dict):
        raise ValueError("technical selection must be a JSON object")
    if (
        selection.get("selection_dataset_role") != "validation"
        or selection.get("capacity_layer") != "causal_robust_mpc_reference"
        or selection.get("controller") != specification.technical.controller
    ):
        raise ValueError("economic replay requires the declared validation-only causal selection")
    raw_validation_hashes = selection.get("validation_scenario_hashes")
    if (
        not isinstance(raw_validation_hashes, list)
        or len(raw_validation_hashes) != specification.technical.expected_scenario_count
        or not all(isinstance(item, str) and len(item) == 64 for item in raw_validation_hashes)
    ):
        raise ValueError("technical selection has an invalid validation scenario allowlist")
    validation_hashes = tuple(cast(list[str], raw_validation_hashes))
    if len(set(validation_hashes)) != len(validation_hashes):
        raise ValueError("technical selection repeats a validation scenario hash")

    provenance = document.get("controller_provenance")
    if not isinstance(provenance, dict):
        raise ValueError("technical certificate manifest is missing controller provenance")
    if (
        provenance.get("controller_config_sha256")
        != specification.technical.controller_config_sha256
    ):
        raise ValueError("technical certificate controller-config hash does not match the protocol")
    selection_provenance = selection.get("controller_provenance")
    if not isinstance(selection_provenance, dict) or selection_provenance != provenance:
        raise ValueError("technical selection and certificate controller provenance differ")

    expected_criteria = _criteria_document(specification)
    observed_criteria = document.get("criteria")
    if not isinstance(observed_criteria, dict) or set(observed_criteria) != set(expected_criteria):
        raise ValueError("technical certificate criteria do not match the economic protocol")
    for name, expected in expected_criteria.items():
        try:
            observed = float(observed_criteria[name])
        except (TypeError, ValueError) as error:
            raise ValueError(f"technical certificate criterion is not numeric: {name}") from error
        if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"technical certificate criterion does not match the protocol: {name}")
    selection_criteria = selection.get("criteria")
    if not isinstance(selection_criteria, dict) or set(selection_criteria) != set(
        expected_criteria
    ):
        raise ValueError("technical selection criteria do not match the economic protocol")
    for name, expected in expected_criteria.items():
        if not math.isclose(float(selection_criteria[name]), expected, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"technical selection criterion does not match the protocol: {name}")

    source_hashes = provenance.get("source_sha256")
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise ValueError("technical certificate has no source-hash provenance")
    observed_source_hashes: dict[str, str] = {}
    replay_git_tree: str | None = None
    certificate_commit = provenance.get("git_commit")
    if specification.technical.replay_runtime_mode == "certificate_git_commit":
        if (
            not isinstance(certificate_commit, str)
            or certificate_commit != specification.technical.replay_git_commit
        ):
            raise ValueError(
                "version-pinned replay commit does not match the technical certificate"
            )
        _resolved_commit, replay_git_tree = _resolve_git_commit(certificate_commit)
        controller_path = Path(specification.technical.controller_config)
        if controller_path.is_absolute() or ".." in controller_path.parts:
            raise ValueError("version-pinned controller configuration must be repository-relative")
        if (
            _git_blob_sha256(certificate_commit, controller_path.as_posix())
            != specification.technical.controller_config_sha256
        ):
            raise ValueError(
                "controller configuration in the pinned commit does not match the certificate"
            )
    for raw_path, expected_hash in sorted(source_hashes.items()):
        if (
            not isinstance(raw_path, str)
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
        ):
            raise ValueError("technical certificate has an invalid source-hash record")
        if specification.technical.replay_runtime_mode == "certificate_git_commit":
            assert isinstance(certificate_commit, str)
            actual_hash = _git_blob_sha256(certificate_commit, raw_path)
        else:
            source_path = _relative_repository_path(raw_path)
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            actual_hash = sha256_file(source_path)
        if actual_hash != expected_hash:
            raise ValueError(
                "selected replay runtime differs from the fixed technical certificate: "
                + raw_path
                + ". Refusing to reuse K_cert; either recertify under this runtime or run an "
                "explicitly version-pinned compatibility replay."
            )
        observed_source_hashes[raw_path] = actual_hash

    # Technical outcomes are derived by the current aggregation process after
    # the pinned runtime returns physical trajectories.  Its implementation
    # must therefore remain byte-identical to the certificate definition.
    if specification.technical.replay_runtime_mode == "certificate_git_commit":
        outcome_path = "src/aidrbench/evaluation/firm_flexibility.py"
        expected_outcome_hash = source_hashes.get(outcome_path)
        if not isinstance(expected_outcome_hash, str):
            raise ValueError("technical certificate does not bind firm_flexibility.py")
        if sha256_file(_relative_repository_path(outcome_path)) != expected_outcome_hash:
            raise ValueError(
                "current economic aggregation no longer matches the certificate's technical "
                "outcome definition; a compatibility adapter or recertification is required"
            )

    locked_hashes = document.get("locked_id_scenario_hashes")
    if not isinstance(locked_hashes, list) or not locked_hashes:
        raise ValueError("technical certificate manifest has no locked-ID scenario provenance")
    if not all(isinstance(item, str) and len(item) == 64 for item in locked_hashes):
        raise ValueError("technical certificate has invalid locked-ID scenario hashes")
    locked_hash_set = frozenset(cast(list[str], locked_hashes))
    if set(validation_hashes).intersection(locked_hash_set):
        raise ValueError("validation selection overlaps the locked-ID certificate scenarios")

    validation_receipt_path = _resolve_protocol_path(
        specification.technical.validation_scenario_receipt
    )
    validation_receipt = yaml.safe_load(validation_receipt_path.read_text(encoding="utf-8"))
    if not isinstance(validation_receipt, dict):
        raise ValueError("validation scenario receipt must be a YAML mapping")
    validation_set = validation_receipt.get("scenario_set")
    if (
        validation_receipt.get("receipt_role") != "post_generation_validation_scenario_set_receipt"
        or validation_receipt.get("locked_data_read") is not False
        or not isinstance(validation_set, dict)
        or validation_set.get("role") != "validation"
        or int(validation_set.get("scenario_count", -1))
        != specification.technical.expected_scenario_count
        or tuple(validation_set.get("episode_seed_range", ()))
        != specification.technical.expected_episode_seed_range
        or _resolve_protocol_path(str(validation_set.get("output_directory", "")))
        != _resolve_protocol_path(specification.technical.scenario_directory)
    ):
        raise ValueError("validation scenario receipt does not match the economic protocol")
    validation_integrity = validation_receipt.get("integrity_audit")
    if not isinstance(validation_integrity, dict):
        raise ValueError("validation receipt has no integrity audit")

    locked_receipt_path = _resolve_protocol_path(specification.technical.locked_id_receipt)
    locked_receipt = yaml.safe_load(locked_receipt_path.read_text(encoding="utf-8"))
    if not isinstance(locked_receipt, dict):
        raise ValueError("locked-ID receipt must be a YAML mapping")
    q_key = f"q_{specification.technical.reliability_target:.2f}".replace(".", "_")
    receipt_controller = locked_receipt.get("controller")
    receipt_selections = locked_receipt.get("selection_artifacts")
    receipt_certificates = locked_receipt.get("locked_certificate_artifacts")
    selection_receipt = (
        receipt_selections.get(q_key) if isinstance(receipt_selections, dict) else None
    )
    certificate_receipt = (
        receipt_certificates.get(q_key) if isinstance(receipt_certificates, dict) else None
    )
    if (
        locked_receipt.get("receipt_role") != "post_run_locked_id_causal_certificate_receipt"
        or locked_receipt.get("locked_ood_read") is not False
        or not isinstance(receipt_controller, dict)
        or receipt_controller.get("name") != specification.technical.controller
        or receipt_controller.get("config_sha256")
        != specification.technical.controller_config_sha256
        or not isinstance(selection_receipt, dict)
        or _resolve_protocol_path(str(selection_receipt.get("path", ""))) != selection_path
        or selection_receipt.get("sha256") != specification.technical.technical_selection_sha256
        or not isinstance(certificate_receipt, dict)
        or certificate_receipt.get("manifest_sha256")
        != specification.technical.technical_certificate_manifest_sha256
        or certificate_receipt.get("summary_sha256")
        != specification.technical.technical_certificate_sha256
    ):
        raise ValueError("locked-ID receipt does not bind the declared technical evidence chain")
    if (
        isinstance(certificate_commit, str)
        and locked_receipt.get("analysis_git_commit") != certificate_commit
    ):
        raise ValueError("locked-ID receipt git commit differs from the certificate")
    locked_set_receipt = locked_receipt.get("scenario_set")
    if not isinstance(locked_set_receipt, dict):
        raise ValueError("locked-ID receipt has no scenario-set record")
    locked_list_sha256 = hashlib.sha256(
        json.dumps(list(locked_hashes), separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if locked_set_receipt.get("scenario_hash_list_sha256") != locked_list_sha256:
        raise ValueError("locked-ID receipt scenario digest differs from the certificate")
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": specification.technical.technical_certificate_manifest_sha256,
        "controller_config_sha256": specification.technical.controller_config_sha256,
        "criteria": expected_criteria,
        "locked_id_scenario_count": len(locked_hashes),
        "locked_id_scenario_hashes": list(locked_hashes),
        "validation_scenario_hashes": list(validation_hashes),
        "technical_selection_path": str(selection_path),
        "technical_selection_sha256": specification.technical.technical_selection_sha256,
        "validation_scenario_receipt": str(validation_receipt_path),
        "validation_scenario_receipt_sha256": (
            specification.technical.validation_scenario_receipt_sha256
        ),
        "locked_id_receipt": str(locked_receipt_path),
        "locked_id_receipt_sha256": specification.technical.locked_id_receipt_sha256,
        "validation_payload_set_sha256": validation_set.get("scenario_set_sha256"),
        "power_model_sha256": validation_integrity.get("power_model_sha256"),
        "calibration_artifact_sha256": validation_integrity.get("calibration_artifact_sha256"),
        "locked_scenario_payloads_read": False,
        "locked_ood_read": False,
        "source_sha256": observed_source_hashes,
        "replay_runtime_mode": specification.technical.replay_runtime_mode,
        "replay_git_commit": specification.technical.replay_git_commit,
        "replay_git_tree": replay_git_tree,
        "pyproject_sha256": (
            _git_blob_sha256(certificate_commit, "pyproject.toml")
            if specification.technical.replay_runtime_mode == "certificate_git_commit"
            and isinstance(certificate_commit, str)
            else None
        ),
        "uv_lock_sha256": (
            _git_blob_sha256(certificate_commit, "uv.lock")
            if specification.technical.replay_runtime_mode == "certificate_git_commit"
            and isinstance(certificate_commit, str)
            else None
        ),
    }


def _environment_document(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    event_id: int,
) -> dict[str, Any]:
    """Construct a transparent replay document without mutating frozen inputs."""

    document = copy.deepcopy(artifact.config_document)
    raw_scenario = document.get("scenario")
    scenario = dict(raw_scenario) if isinstance(raw_scenario, Mapping) else {}
    scenario.update(
        {
            "frozen_path": str(artifact.directory),
            "frozen_event_ids": [event_id],
            "frozen_event_notice_hours": notice_h,
        }
    )
    scenario.pop("locked_set", None)
    scenario.pop("locked_ood", None)
    scenario.pop("preregistration_manifest", None)
    document["scenario"] = scenario
    raw_dr = document.get("dr")
    if not isinstance(raw_dr, Mapping):
        raise ValueError("frozen scenario config is missing a dr mapping")
    dr = dict(raw_dr)
    dr.update(
        {
            "source": "configured",
            "events_path": None,
            "event_duration_hours": duration_h,
            "event_notice_hours": notice_h,
            "event_reduction_kw": requested_reduction_kw,
            "event_duration_choices": None,
            "event_notice_choices": None,
            "event_reduction_fraction_range": None,
            "event_start_jitter_hours": 0,
        }
    )
    document["dr"] = dr
    return document


@lru_cache(maxsize=8)
def _controller_specification(path: str) -> RobustMPCSpecification:
    return load_robust_mpc_specification(path)


def _criteria_document(specification: EconomicParticipationSpecification) -> dict[str, float]:
    """Return the full frozen joint-success definition for a replay task.

    The economics configuration stores reliability and confidence at the
    technical layer, while the six operational thresholds are nested below
    ``technical.criteria``.  Reconstructing the criteria here avoids silently
    falling back to dataclass defaults during a paired replay.
    """

    criteria = FirmFlexibilityCriteria(
        reliability_target=specification.technical.reliability_target,
        confidence_level=specification.technical.confidence_level,
        **specification.technical.criteria,
    )
    return criteria.as_dict()


def _paired_frames(
    artifact: FrozenHourlyScenario,
    *,
    controller_config: str,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    event_id: int,
    paired_pcc_tolerance_kw: float,
    work_conservation_tolerance_gpu_h: float,
) -> tuple[pd.DataFrame, pd.DataFrame, HourlyCommunityAIDemandResponseEnv]:
    controlled, controlled_env = _controlled_frame(
        artifact,
        controller_config=controller_config,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        event_id=event_id,
    )
    no_dr = _no_control_frame(
        artifact,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        event_id=event_id,
    )
    _validate_pair(
        controlled,
        no_dr,
        paired_pcc_tolerance_kw=paired_pcc_tolerance_kw,
        work_conservation_tolerance_gpu_h=work_conservation_tolerance_gpu_h,
    )
    return controlled, no_dr, controlled_env


def _controlled_frame(
    artifact: FrozenHourlyScenario,
    *,
    controller_config: str,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    event_id: int,
) -> tuple[pd.DataFrame, HourlyCommunityAIDemandResponseEnv]:
    document = _environment_document(
        artifact,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        event_id=event_id,
    )
    controlled_env = HourlyCommunityAIDemandResponseEnv(document)
    controlled, _ = rollout_hourly_episode(
        controlled_env,
        make_hourly_controller(
            "robust_mpc",
            robust_mpc_specification=_controller_specification(controller_config),
        ),
        seed=artifact.episode_seed,
    )
    return controlled, controlled_env


def _no_control_frame(
    artifact: FrozenHourlyScenario,
    *,
    duration_h: int,
    notice_h: int,
    requested_reduction_kw: float,
    event_id: int,
) -> pd.DataFrame:
    document = _environment_document(
        artifact,
        duration_h=duration_h,
        notice_h=notice_h,
        requested_reduction_kw=requested_reduction_kw,
        event_id=event_id,
    )
    no_dr_env = HourlyCommunityAIDemandResponseEnv(document)
    no_dr, _ = rollout_hourly_episode(
        no_dr_env,
        make_hourly_controller("no_control"),
        seed=artifact.episode_seed,
    )
    return no_dr


def _validate_pair(
    controlled: pd.DataFrame,
    no_dr: pd.DataFrame,
    *,
    paired_pcc_tolerance_kw: float,
    work_conservation_tolerance_gpu_h: float,
) -> None:
    required = {
        "hour",
        "episode_seed",
        "frozen_scenario_hash",
        "baseline_pcc_power_kw",
        "pcc_power_kw",
        "action_fraction",
        "conservation_error_gpu_h",
    }
    for name, frame in (("controlled", controlled), ("no_dr", no_dr)):
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"{name} replay is missing columns: {', '.join(missing)}")
    if len(controlled) != len(no_dr) or not controlled["hour"].equals(no_dr["hour"]):
        raise ValueError("paired replays do not have an identical hourly index")
    if not controlled["episode_seed"].equals(no_dr["episode_seed"]):
        raise ValueError("paired replays do not share an episode seed")
    if not controlled["frozen_scenario_hash"].equals(no_dr["frozen_scenario_hash"]):
        raise ValueError("paired replays do not share a frozen scenario hash")
    if not np.allclose(
        pd.to_numeric(controlled["baseline_pcc_power_kw"], errors="raise"),
        pd.to_numeric(no_dr["pcc_power_kw"], errors="raise"),
        rtol=0.0,
        atol=paired_pcc_tolerance_kw,
    ):
        raise ValueError("controlled shadow baseline does not match no-control PCC replay")
    if not np.allclose(
        pd.to_numeric(no_dr["action_fraction"], errors="raise"),
        1.0,
        rtol=0.0,
        atol=1e-12,
    ):
        raise ValueError("no-control counterfactual did not execute at full fraction")
    for name, frame in (("controlled", controlled), ("no_dr", no_dr)):
        errors = pd.to_numeric(frame["conservation_error_gpu_h"], errors="raise").abs()
        if float(errors.max()) > work_conservation_tolerance_gpu_h:
            raise ValueError(f"{name} replay violates workload conservation")


def _event_windows(
    frame: pd.DataFrame,
    *,
    event_id: int,
    event_start_hour: int,
    event_stop_hour: int,
    recovery_stop_hour: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event = frame[(frame["event_id"] == event_id) & frame["event_active"].astype(bool)].copy()
    if event.empty:
        raise RuntimeError("paired ledger could not locate the declared event window")
    if (
        int(event["hour"].min()) != event_start_hour
        or int(event["hour"].max()) + 1 != event_stop_hour
    ):
        raise RuntimeError("event window does not match frozen-event metadata")
    recovery = frame[
        (frame["hour"] >= event_stop_hour) & (frame["hour"] < recovery_stop_hour)
    ].copy()
    within_recovery = frame[
        (frame["hour"] >= event_start_hour) & (frame["hour"] < recovery_stop_hour)
    ].copy()
    if len(within_recovery) != recovery_stop_hour - event_start_hour:
        raise RuntimeError("event/recovery window is incomplete")
    through_episode_end = frame[frame["hour"] >= event_start_hour].copy()
    if through_episode_end.empty:
        raise RuntimeError("event-to-episode-end window is empty")
    expected_tail_hours = int(frame["hour"].iloc[-1]) - event_start_hour + 1
    if len(through_episode_end) != expected_tail_hours:
        raise RuntimeError("event-to-episode-end window is incomplete")
    return event, recovery, within_recovery, through_episode_end


def event_ledger_from_paired_frames(
    controlled: pd.DataFrame,
    no_dr: pd.DataFrame,
    *,
    scenario_id: str,
    scenario_hash: str,
    episode_seed: int,
    event: HourlyDREvent,
    event_id: int,
    event_start_hour: int,
    event_stop_hour: int,
    recovery_stop_hour: int,
    duration_h: int,
    notice_h: int,
    reliability_target: float,
    confidence_level: float,
    technical_capacity_ceiling_kw: float,
    offer_fraction: float,
    criteria: FirmFlexibilityCriteria,
    recovery_tolerance_gpu_h: float,
    timestep_hours: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Calculate one event row and its exact interval-level plot/audit data."""

    if timestep_hours != 1.0:
        raise ValueError("economic v1 requires the current hourly timestep")
    if not 0.0 < offer_fraction <= 1.0:
        raise ValueError("offer_fraction must lie in (0, 1]")
    if len(controlled) != len(no_dr) or not controlled["hour"].equals(no_dr["hour"]):
        raise ValueError("paired event-ledger frames must share a complete hourly index")
    candidate_kw = technical_capacity_ceiling_kw * offer_fraction
    (
        controlled_event,
        controlled_recovery,
        controlled_window,
        controlled_through_end,
    ) = _event_windows(
        controlled,
        event_id=event_id,
        event_start_hour=event_start_hour,
        event_stop_hour=event_stop_hour,
        recovery_stop_hour=recovery_stop_hour,
    )
    no_dr_event, no_dr_recovery, no_dr_window, no_dr_through_end = _event_windows(
        no_dr,
        event_id=event_id,
        event_start_hour=event_start_hour,
        event_stop_hour=event_stop_hour,
        recovery_stop_hour=recovery_stop_hour,
    )
    if not controlled_window["hour"].equals(no_dr_window["hour"]):
        raise RuntimeError("paired event/recovery windows do not align")
    if not controlled_through_end["hour"].equals(no_dr_through_end["hour"]):
        raise RuntimeError("paired event-to-episode-end windows do not align")
    pcc_delta = pd.to_numeric(no_dr_event["pcc_power_kw"], errors="raise").to_numpy(
        dtype=float
    ) - pd.to_numeric(controlled_event["pcc_power_kw"], errors="raise").to_numpy(dtype=float)
    delivered = np.maximum(pcc_delta, 0.0)
    capped_delivered = np.minimum(delivered, candidate_kw)
    delivered_energy = float(delivered.sum() * timestep_hours)
    capped_delivered_energy = float(capped_delivered.sum() * timestep_hours)
    shortfall_energy = max(candidate_kw * duration_h - capped_delivered_energy, 0.0)
    executed_delta_event = pd.to_numeric(no_dr_event["executed_gpu_h"], errors="raise").to_numpy(
        dtype=float
    ) - pd.to_numeric(controlled_event["executed_gpu_h"], errors="raise").to_numpy(dtype=float)
    executed_delta_recovery_window = pd.to_numeric(
        controlled_recovery["executed_gpu_h"], errors="raise"
    ).to_numpy(dtype=float) - pd.to_numeric(
        no_dr_recovery["executed_gpu_h"], errors="raise"
    ).to_numpy(dtype=float)
    post_event_mask = controlled_through_end["hour"] >= event_stop_hour
    controlled_post_event = controlled_through_end.loc[post_event_mask]
    no_dr_post_event = no_dr_through_end.loc[no_dr_through_end["hour"] >= event_stop_hour]
    executed_delta_through_end = pd.to_numeric(
        controlled_post_event["executed_gpu_h"], errors="raise"
    ).to_numpy(dtype=float) - pd.to_numeric(
        no_dr_post_event["executed_gpu_h"], errors="raise"
    ).to_numpy(dtype=float)
    deferred = float(np.maximum(executed_delta_event, 0.0).sum())
    recovered_within_recovery = float(np.maximum(executed_delta_recovery_window, 0.0).sum())
    recovered_through_episode_end = float(np.maximum(executed_delta_through_end, 0.0).sum())
    backlog_delta_within_recovery = pd.to_numeric(
        controlled_window["backlog_gpu_h"], errors="raise"
    ).to_numpy(dtype=float) - pd.to_numeric(no_dr_window["backlog_gpu_h"], errors="raise").to_numpy(
        dtype=float
    )
    backlog_delta_through_end = pd.to_numeric(
        controlled_through_end["backlog_gpu_h"], errors="raise"
    ).to_numpy(dtype=float) - pd.to_numeric(
        no_dr_through_end["backlog_gpu_h"], errors="raise"
    ).to_numpy(dtype=float)
    incremental_backlog_area_within_recovery = float(
        np.maximum(backlog_delta_within_recovery, 0.0).sum() * timestep_hours
    )
    incremental_backlog_area_through_episode_end = float(
        np.maximum(backlog_delta_through_end, 0.0).sum() * timestep_hours
    )
    missed_delta = pd.to_numeric(controlled_through_end["missed_gpu_h"], errors="raise").to_numpy(
        dtype=float
    ) - pd.to_numeric(no_dr_through_end["missed_gpu_h"], errors="raise").to_numpy(dtype=float)
    recovery_terminal_row = controlled_window[controlled_window["hour"] == recovery_stop_hour - 1]
    no_dr_recovery_terminal_row = no_dr_window[no_dr_window["hour"] == recovery_stop_hour - 1]
    if len(recovery_terminal_row) != 1 or len(no_dr_recovery_terminal_row) != 1:
        raise RuntimeError("paired ledger could not locate the recovery terminal state")
    backlog_at_recovery_stop = max(
        float(recovery_terminal_row["backlog_gpu_h"].iloc[0])
        - float(no_dr_recovery_terminal_row["backlog_gpu_h"].iloc[0]),
        0.0,
    )
    terminal_backlog = max(
        float(controlled["backlog_gpu_h"].iloc[-1]) - float(no_dr["backlog_gpu_h"].iloc[-1]),
        0.0,
    )
    incremental_energy_within_recovery = float(
        (
            pd.to_numeric(controlled_window["pcc_power_kw"], errors="raise").to_numpy(dtype=float)
            - pd.to_numeric(no_dr_window["pcc_power_kw"], errors="raise").to_numpy(dtype=float)
        ).sum()
        * timestep_hours
    )
    incremental_energy_through_episode_end = float(
        (
            pd.to_numeric(controlled_through_end["pcc_power_kw"], errors="raise").to_numpy(
                dtype=float
            )
            - pd.to_numeric(no_dr_through_end["pcc_power_kw"], errors="raise").to_numpy(dtype=float)
        ).sum()
        * timestep_hours
    )
    outcomes = derive_event_outcomes(
        controlled,
        [event],
        recovery_tolerance_gpu_h=recovery_tolerance_gpu_h,
    )
    if len(outcomes) != 1:
        raise RuntimeError("paired ledger expected exactly one technical event outcome")
    outcome = outcomes[0]
    technical_success, failure_reasons = outcome.success(criteria)
    event_peak_delta = float(
        controlled_event["pcc_power_kw"].max() - no_dr_event["pcc_power_kw"].max()
    )
    recovery_peak_delta = (
        float(controlled_recovery["pcc_power_kw"].max() - no_dr_recovery["pcc_power_kw"].max())
        if not controlled_recovery.empty
        else 0.0
    )
    paired_pcc_match = float(
        np.abs(
            pd.to_numeric(controlled["baseline_pcc_power_kw"], errors="raise").to_numpy(dtype=float)
            - pd.to_numeric(no_dr["pcc_power_kw"], errors="raise").to_numpy(dtype=float)
        ).max()
    )
    record: dict[str, Any] = {
        "evaluation_split": "development_parameterized_screening",
        "scenario_id": scenario_id,
        "scenario_hash": scenario_hash,
        "episode_seed": episode_seed,
        "event_id": event_id,
        "event_start_hour": event_start_hour,
        "event_stop_hour": event_stop_hour,
        "recovery_stop_hour": recovery_stop_hour,
        "duration_h": duration_h,
        "notice_h": notice_h,
        "reliability_target": reliability_target,
        "confidence_level": confidence_level,
        "technical_capacity_ceiling_kw": technical_capacity_ceiling_kw,
        "offer_fraction_of_technical_ceiling": offer_fraction,
        "candidate_reduction_kw": candidate_kw,
        "technical_success": technical_success,
        # Keep the exported audit ledger explicit.  A blank CSV field is
        # routinely parsed as NA by spreadsheet tools, which would make a
        # successful event look as though its diagnostic were missing.
        "technical_failure_reasons": (
            ",".join(failure_reasons) if failure_reasons else "none_technical_success"
        ),
        "delivery_ratio": outcome.delivery_ratio,
        "minimum_interval_delivery_ratio": outcome.minimum_interval_delivery_ratio,
        "delivered_energy_kwh": delivered_energy,
        "capped_delivered_energy_kwh": capped_delivered_energy,
        "shortfall_energy_kwh": shortfall_energy,
        "deferred_gpu_h": deferred,
        "recovered_within_recovery_window_gpu_h": recovered_within_recovery,
        "recovered_through_episode_end_gpu_h": recovered_through_episode_end,
        "unrecovered_at_recovery_stop_gpu_h_proxy": max(deferred - recovered_within_recovery, 0.0),
        "unrecovered_at_episode_end_gpu_h_proxy": max(
            deferred - recovered_through_episode_end, 0.0
        ),
        "missed_gpu_h": float(np.maximum(missed_delta, 0.0).sum()),
        "backlog_at_recovery_stop_gpu_h": backlog_at_recovery_stop,
        "terminal_backlog_gpu_h": terminal_backlog,
        "incremental_backlog_area_within_recovery_gpu_h_h": (
            incremental_backlog_area_within_recovery
        ),
        "incremental_backlog_area_through_episode_end_gpu_h_h": (
            incremental_backlog_area_through_episode_end
        ),
        "incremental_energy_within_recovery_kwh": incremental_energy_within_recovery,
        "incremental_energy_through_episode_end_kwh": (incremental_energy_through_episode_end),
        "event_peak_delta_kw": event_peak_delta,
        "recovery_peak_delta_kw": recovery_peak_delta,
        "checkpoint_count_or_proxy": 0.0,
        "checkpoint_proxy_method": "not_explicit_in_model_a",
        "paired_pcc_match_max_abs_kw": paired_pcc_match,
        "controlled_work_conservation_error_gpu_h": float(
            pd.to_numeric(controlled["conservation_error_gpu_h"], errors="raise").abs().max()
        ),
        "no_dr_work_conservation_error_gpu_h": float(
            pd.to_numeric(no_dr["conservation_error_gpu_h"], errors="raise").abs().max()
        ),
    }
    if tuple(record) != _LEDGER_COLUMNS:
        raise RuntimeError("economic event ledger schema drifted from its declared order")
    interval = pd.DataFrame(
        {
            "scenario_id": scenario_id,
            "scenario_hash": scenario_hash,
            "episode_seed": episode_seed,
            "event_id": event_id,
            "duration_h": duration_h,
            "notice_h": notice_h,
            "candidate_reduction_kw": candidate_kw,
            "hour": controlled_through_end["hour"].to_numpy(dtype=int),
            "relative_hour": (
                controlled_through_end["hour"].to_numpy(dtype=int) - event_start_hour
            ),
            "event_active": controlled_through_end["event_active"].to_numpy(dtype=bool),
            "recovery_active": controlled_through_end["recovery_active"].to_numpy(dtype=bool),
            "within_recovery_window": (
                controlled_through_end["hour"].to_numpy(dtype=int) < recovery_stop_hour
            ),
            "clearance_tail_active": (
                controlled_through_end["hour"].to_numpy(dtype=int) >= recovery_stop_hour
            ),
            "controlled_pcc_power_kw": controlled_through_end["pcc_power_kw"].to_numpy(dtype=float),
            "no_dr_pcc_power_kw": no_dr_through_end["pcc_power_kw"].to_numpy(dtype=float),
            "controlled_executed_gpu_h": controlled_through_end["executed_gpu_h"].to_numpy(
                dtype=float
            ),
            "no_dr_executed_gpu_h": no_dr_through_end["executed_gpu_h"].to_numpy(dtype=float),
            "controlled_backlog_gpu_h": controlled_through_end["backlog_gpu_h"].to_numpy(
                dtype=float
            ),
            "no_dr_backlog_gpu_h": no_dr_through_end["backlog_gpu_h"].to_numpy(dtype=float),
            "controlled_missed_gpu_h": controlled_through_end["missed_gpu_h"].to_numpy(dtype=float),
            "no_dr_missed_gpu_h": no_dr_through_end["missed_gpu_h"].to_numpy(dtype=float),
            "pcc_delta_kw": (
                controlled_through_end["pcc_power_kw"].to_numpy(dtype=float)
                - no_dr_through_end["pcc_power_kw"].to_numpy(dtype=float)
            ),
            "execution_delta_gpu_h": (
                controlled_through_end["executed_gpu_h"].to_numpy(dtype=float)
                - no_dr_through_end["executed_gpu_h"].to_numpy(dtype=float)
            ),
            "backlog_delta_gpu_h": backlog_delta_through_end,
        }
    )
    if tuple(interval.columns) != _INTERVAL_COLUMNS:
        raise RuntimeError("economic interval ledger schema drifted from its declared order")
    return record, interval


def _load_certificate_worker_frame(
    output: Path,
    record: Mapping[str, object],
) -> pd.DataFrame:
    raw_name = record.get("path")
    expected_hash = record.get("sha256")
    expected_rows = record.get("row_count")
    if (
        not isinstance(raw_name, str)
        or Path(raw_name).name != raw_name
        or not isinstance(expected_hash, str)
        or len(expected_hash) != 64
        or not isinstance(expected_rows, int)
        or expected_rows <= 0
    ):
        raise RuntimeError("certificate runtime worker returned an invalid frame record")
    path = output / raw_name
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise RuntimeError("certificate runtime worker frame failed its SHA-256 check")
    frame = pd.read_parquet(path)
    if len(frame) != expected_rows:
        raise RuntimeError("certificate runtime worker frame has the wrong row count")
    return frame


def _replay_group_task_in_certificate_runtime(
    task: _ReplayGroupTask,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    """Obtain physical trajectories from the immutable certificate source tree."""

    if (
        task.runtime_source_root is None
        or task.replay_git_commit is None
        or task.replay_git_tree is None
    ):
        raise RuntimeError("certificate replay task has no prepared immutable runtime")
    source_root = Path(task.runtime_source_root).resolve()
    if not (source_root / "aidrbench/__init__.py").is_file():
        raise RuntimeError("prepared certificate replay package is absent")

    task_document: dict[str, object] = {
        "artifact_path": str(_resolve_protocol_path(task.artifact_path)),
        "scenario_id": task.scenario_id,
        "scenario_hash": task.scenario_hash,
        "episode_seed": task.episode_seed,
        "controller_config": str(source_root.parent / task.controller_config),
        "controller_config_sha256": task.controller_config_sha256,
        "duration_h": task.duration_h,
        "notice_h": task.notice_h,
        "event_id": task.event_id,
        "technical_ceiling_kw": task.technical_ceiling_kw,
        "offer_fractions": list(task.offer_fractions),
        "replay_git_commit": task.replay_git_commit,
        "replay_git_tree": task.replay_git_tree,
    }
    worker_path = _ROOT / "scripts/economic_certificate_runtime_worker.py"
    temporary_parent = source_root.parents[1]
    with tempfile.TemporaryDirectory(
        prefix=f".replay-{task.task_sha256[:12]}.",
        suffix=".tmp",
        dir=temporary_parent,
    ) as temporary_name:
        temporary = Path(temporary_name)
        input_path = temporary / "task.json"
        output = temporary / "output"
        input_path.write_text(
            json.dumps(task_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source_root)
        environment["PYTHONNOUSERSITE"] = "1"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONHASHSEED"] = "0"
        environment["OMP_NUM_THREADS"] = "1"
        environment["OPENBLAS_NUM_THREADS"] = "1"
        environment["MKL_NUM_THREADS"] = "1"
        environment["NUMEXPR_NUM_THREADS"] = "1"
        environment["AIDRBENCH_CERTIFICATE_SOURCE_ROOT"] = str(source_root)
        process = subprocess.run(
            [sys.executable, str(worker_path), str(input_path), str(output)],
            cwd=source_root.parent,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if process.returncode != 0:
            detail = process.stderr.strip() or process.stdout.strip() or "no worker output"
            raise RuntimeError(f"certificate runtime replay failed: {detail}")
        manifest_path = output / "worker_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError("certificate runtime worker did not publish a manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_identity = {
            "schema_version": 1,
            "runtime_mode": "certificate_git_commit",
            "runtime_git_commit": task.replay_git_commit,
            "runtime_git_tree": task.replay_git_tree,
            "scenario_id": task.scenario_id,
            "scenario_hash": task.scenario_hash,
            "episode_seed": task.episode_seed,
            "duration_h": task.duration_h,
            "notice_h": task.notice_h,
            "event_id": task.event_id,
            "technical_ceiling_kw": task.technical_ceiling_kw,
            "offer_fractions": list(task.offer_fractions),
            "controller_config_sha256": task.controller_config_sha256,
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "dependency_versions": _installed_dependency_versions(),
        }
        if not isinstance(manifest, dict):
            raise RuntimeError("certificate runtime worker manifest is not an object")
        for name, expected in expected_identity.items():
            if manifest.get(name) != expected:
                raise RuntimeError(f"certificate runtime worker identity mismatch: {name}")
        raw_no_dr = manifest.get("no_dr")
        raw_controlled = manifest.get("controlled")
        if not isinstance(raw_no_dr, Mapping) or not isinstance(raw_controlled, list):
            raise RuntimeError("certificate runtime worker manifest is incomplete")
        if len(raw_controlled) != len(task.offer_fractions):
            raise RuntimeError("certificate runtime worker returned an incomplete offer grid")
        no_dr = _load_certificate_worker_frame(output, raw_no_dr)
        criteria = FirmFlexibilityCriteria(**task.criteria_document)
        records: list[dict[str, Any]] = []
        intervals: list[pd.DataFrame] = []
        for offer_fraction, raw_controlled_record in zip(
            task.offer_fractions, raw_controlled, strict=True
        ):
            if not isinstance(raw_controlled_record, Mapping):
                raise RuntimeError("certificate runtime controlled record is invalid")
            if not math.isclose(
                float(raw_controlled_record.get("offer_fraction", float("nan"))),
                offer_fraction,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise RuntimeError("certificate runtime worker returned the wrong offer fraction")
            controlled = _load_certificate_worker_frame(output, raw_controlled_record)
            _validate_pair(
                controlled,
                no_dr,
                paired_pcc_tolerance_kw=task.paired_pcc_tolerance_kw,
                work_conservation_tolerance_gpu_h=task.work_conservation_tolerance_gpu_h,
            )
            raw_event = raw_controlled_record.get("event")
            if not isinstance(raw_event, Mapping):
                raise RuntimeError("certificate runtime worker omitted event metadata")
            event = HourlyDREvent(
                event_id=int(raw_event["event_id"]),
                start_hour=int(raw_event["start_hour"]),
                stop_hour=int(raw_event["stop_hour"]),
                recovery_stop_hour=int(raw_event["recovery_stop_hour"]),
                requested_reduction_kw=float(raw_event["requested_reduction_kw"]),
                source_event_id=str(raw_event["source_event_id"]),
                notice_hours=float(raw_event["notice_hours"]),
            )
            if event.event_id != task.event_id or not math.isclose(
                event.requested_reduction_kw,
                task.technical_ceiling_kw * offer_fraction,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise RuntimeError("certificate runtime worker event metadata is inconsistent")
            record, interval = event_ledger_from_paired_frames(
                controlled,
                no_dr,
                scenario_id=task.scenario_id,
                scenario_hash=task.scenario_hash,
                episode_seed=task.episode_seed,
                event=event,
                event_id=event.event_id,
                event_start_hour=event.start_hour,
                event_stop_hour=event.stop_hour,
                recovery_stop_hour=event.recovery_stop_hour,
                duration_h=task.duration_h,
                notice_h=task.notice_h,
                reliability_target=float(task.criteria_document["reliability_target"]),
                confidence_level=float(task.criteria_document["confidence_level"]),
                technical_capacity_ceiling_kw=task.technical_ceiling_kw,
                offer_fraction=offer_fraction,
                criteria=criteria,
                recovery_tolerance_gpu_h=float(raw_controlled_record["recovery_tolerance_gpu_h"]),
                timestep_hours=float(raw_controlled_record["timestep_hours"]),
            )
            records.append(record)
            if task.include_interval_ledger:
                intervals.append(interval)
        interval_ledger = (
            pd.concat(intervals, ignore_index=True)
            if intervals
            else pd.DataFrame(columns=_INTERVAL_COLUMNS)
        )
        return records, interval_ledger


def _replay_group_task(
    task: _ReplayGroupTask,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    """Replay one physical baseline and every declared offer against it."""

    if task.replay_runtime_mode == "certificate_git_commit":
        return _replay_group_task_in_certificate_runtime(task)
    if task.replay_runtime_mode != "current_worktree":
        raise ValueError(f"unsupported economic replay runtime: {task.replay_runtime_mode}")

    artifact = load_frozen_hourly_scenario(task.artifact_path)
    if (
        artifact.scenario_id != task.scenario_id
        or artifact.scenario_hash != task.scenario_hash
        or artifact.episode_seed != task.episode_seed
    ):
        raise ValueError("checkpoint task identity does not match its frozen artifact")

    # The no-control power trajectory is invariant to the requested reduction.
    # Use the fixed technical ceiling in its event metadata and reuse the one
    # physical replay for every offer fraction in this scenario/H/N/event group.
    no_dr = _no_control_frame(
        artifact,
        duration_h=task.duration_h,
        notice_h=task.notice_h,
        requested_reduction_kw=task.technical_ceiling_kw,
        event_id=task.event_id,
    )
    criteria = FirmFlexibilityCriteria(**task.criteria_document)
    records: list[dict[str, Any]] = []
    intervals: list[pd.DataFrame] = []
    for offer_fraction in task.offer_fractions:
        controlled, environment = _controlled_frame(
            artifact,
            controller_config=task.controller_config,
            duration_h=task.duration_h,
            notice_h=task.notice_h,
            requested_reduction_kw=task.technical_ceiling_kw * offer_fraction,
            event_id=task.event_id,
        )
        _validate_pair(
            controlled,
            no_dr,
            paired_pcc_tolerance_kw=task.paired_pcc_tolerance_kw,
            work_conservation_tolerance_gpu_h=task.work_conservation_tolerance_gpu_h,
        )
        events = [
            event for event in environment.event_manifest if int(event.event_id) == task.event_id
        ]
        if len(events) != 1:
            raise RuntimeError(
                f"economic replay expected exactly one event with ID {task.event_id}"
            )
        event = events[0]
        record, interval = event_ledger_from_paired_frames(
            controlled,
            no_dr,
            scenario_id=artifact.scenario_id,
            scenario_hash=artifact.scenario_hash,
            episode_seed=artifact.episode_seed,
            event=event,
            event_id=int(event.event_id),
            event_start_hour=int(event.start_hour),
            event_stop_hour=int(event.stop_hour),
            recovery_stop_hour=int(event.recovery_stop_hour),
            duration_h=task.duration_h,
            notice_h=task.notice_h,
            reliability_target=float(task.criteria_document["reliability_target"]),
            confidence_level=float(task.criteria_document["confidence_level"]),
            technical_capacity_ceiling_kw=task.technical_ceiling_kw,
            offer_fraction=offer_fraction,
            criteria=criteria,
            recovery_tolerance_gpu_h=(
                environment.config.recovery_backlog_tolerance_fraction
                * environment.power_model.flexible_capacity_gpu_h
            ),
            timestep_hours=float(environment.config.timestep_hours),
        )
        records.append(record)
        if task.include_interval_ledger:
            intervals.append(interval)
    interval_ledger = (
        pd.concat(intervals, ignore_index=True)
        if intervals
        else pd.DataFrame(columns=_INTERVAL_COLUMNS)
    )
    return records, interval_ledger


def _tree_content_sha256(root: Path) -> tuple[str, int]:
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), len(records)


def _make_snapshot_read_only(snapshot: Path) -> None:
    """Prevent replay or background tooling from mutating the extracted Git tree."""

    paths = list(snapshot.rglob("*"))
    for path in paths:
        if path.is_symlink():
            raise RuntimeError("certificate runtime snapshot contains a symbolic link")
    for path in [*paths, snapshot]:
        path.chmod(path.stat().st_mode & ~0o222)


def _validate_extracted_certificate_runtime(
    source_root: Path,
    *,
    technical_provenance: Mapping[str, object],
) -> tuple[str, int]:
    if not (source_root / "aidrbench/__init__.py").is_file():
        raise RuntimeError("certificate runtime archive has no importable aidrbench package")
    source_hashes = technical_provenance.get("source_sha256")
    if not isinstance(source_hashes, Mapping):
        raise RuntimeError("certificate runtime provenance has no source hashes")
    for repository_path, expected in source_hashes.items():
        if not isinstance(repository_path, str) or not isinstance(expected, str):
            raise RuntimeError("certificate runtime source-hash record is invalid")
        relative = Path(repository_path)
        if len(relative.parts) < 3 or relative.parts[:2] != ("src", "aidrbench"):
            raise RuntimeError(f"unsupported certificate source path: {repository_path}")
        extracted = source_root.parent / relative
        if not extracted.is_file() or sha256_file(extracted) != expected:
            raise RuntimeError(
                f"extracted certificate runtime failed SHA-256 verification: {repository_path}"
            )
    calibration_path = technical_provenance.get("calibration_artifact_path")
    calibration_raw_sha256 = technical_provenance.get("calibration_raw_sha256")
    calibration_artifact_sha256 = technical_provenance.get("calibration_artifact_sha256")
    if not all(
        isinstance(value, str)
        for value in (calibration_path, calibration_raw_sha256, calibration_artifact_sha256)
    ):
        raise RuntimeError("certificate runtime has incomplete calibration provenance")
    assert isinstance(calibration_path, str)
    assert isinstance(calibration_raw_sha256, str)
    calibration_file = source_root.parent / calibration_path
    if not calibration_file.is_file() or sha256_file(calibration_file) != calibration_raw_sha256:
        raise RuntimeError("certificate runtime calibration file failed its SHA-256 check")
    calibration_document = yaml.safe_load(calibration_file.read_text(encoding="utf-8"))
    if (
        not isinstance(calibration_document, dict)
        or calibration_document.get("artifact_sha256") != calibration_artifact_sha256
    ):
        raise RuntimeError("certificate runtime calibration artifact identity is invalid")
    return _tree_content_sha256(source_root.parent)


_PINNED_DISTRIBUTIONS = (
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


def _locked_dependency_versions(snapshot: Path) -> dict[str, str]:
    lock_path = snapshot / "uv.lock"
    document = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = document.get("package")
    if not isinstance(packages, list):
        raise RuntimeError("certificate uv.lock has no package records")
    versions: dict[str, str] = {}
    for raw in packages:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        version = raw.get("version")
        if isinstance(name, str) and isinstance(version, str):
            normalized = name.lower()
            if normalized in _PINNED_DISTRIBUTIONS:
                versions[normalized] = version
    if set(versions) != set(_PINNED_DISTRIBUTIONS):
        missing = sorted(set(_PINNED_DISTRIBUTIONS).difference(versions))
        raise RuntimeError("certificate uv.lock is missing runtime packages: " + ", ".join(missing))
    return dict(sorted(versions.items()))


def _installed_dependency_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in sorted(_PINNED_DISTRIBUTIONS)}


def _prepare_certificate_runtime(
    work: Path,
    *,
    technical_provenance: Mapping[str, object],
) -> tuple[Path, dict[str, object]]:
    """Atomically materialize the immutable package tree named by the certificate."""

    commit = technical_provenance.get("replay_git_commit")
    tree = technical_provenance.get("replay_git_tree")
    if not isinstance(commit, str) or not isinstance(tree, str):
        raise RuntimeError("version-pinned replay provenance has no git commit/tree")
    target = work / "certificate_runtime"
    marker_path = target / "runtime.json"
    if target.exists():
        if not marker_path.is_file():
            raise RuntimeError("certificate runtime directory is incomplete")
        observed_marker = json.loads(marker_path.read_text(encoding="utf-8"))
        source_root = target / "snapshot/src"
        source_tree_sha256, source_file_count = _validate_extracted_certificate_runtime(
            source_root,
            technical_provenance=technical_provenance,
        )
        dependency_versions = _locked_dependency_versions(target / "snapshot")
        if _installed_dependency_versions() != dependency_versions:
            raise RuntimeError(
                "installed solver/runtime dependencies do not match the certificate uv.lock"
            )
        pyproject_sha256 = sha256_file(target / "snapshot/pyproject.toml")
        uv_lock_sha256 = sha256_file(target / "snapshot/uv.lock")
        if pyproject_sha256 != technical_provenance.get("pyproject_sha256"):
            raise RuntimeError("certificate runtime pyproject.toml failed its SHA-256 check")
        if uv_lock_sha256 != technical_provenance.get("uv_lock_sha256"):
            raise RuntimeError("certificate runtime uv.lock failed its SHA-256 check")
        expected = {
            "schema_version": 1,
            "git_commit": commit,
            "git_tree": tree,
            "snapshot_tree_sha256": source_tree_sha256,
            "snapshot_file_count": source_file_count,
            "pyproject_sha256": pyproject_sha256,
            "uv_lock_sha256": uv_lock_sha256,
            "dependency_versions": dependency_versions,
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
        }
        if observed_marker != expected:
            raise RuntimeError("certificate runtime checkpoint does not match its source tree")
        _make_snapshot_read_only(target / "snapshot")
        return source_root, expected

    temporary = Path(tempfile.mkdtemp(prefix=".certificate-runtime.", suffix=".tmp", dir=work))
    try:
        archive_path = temporary / "runtime.tar"
        snapshot = temporary / "snapshot"
        snapshot.mkdir()
        archived = subprocess.run(
            [
                "git",
                "archive",
                "--format=tar",
                f"--output={archive_path}",
                commit,
            ],
            cwd=_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if archived.returncode != 0:
            raise RuntimeError(
                "could not archive the certificate git runtime: " + archived.stderr.strip()
            )
        with tarfile.open(archive_path, mode="r") as archive:
            members = archive.getmembers()
            for member in members:
                destination = (snapshot / member.name).resolve()
                try:
                    destination.relative_to(snapshot.resolve())
                except ValueError as error:
                    raise RuntimeError(
                        "certificate runtime archive contains an unsafe path"
                    ) from error
                if member.issym() or member.islnk() or member.isdev():
                    raise RuntimeError(
                        "certificate runtime archive contains an unsupported link/device"
                    )
            archive.extractall(snapshot, members=members, filter="data")
        archive_path.unlink()
        source_root = snapshot / "src"
        source_tree_sha256, source_file_count = _validate_extracted_certificate_runtime(
            source_root,
            technical_provenance=technical_provenance,
        )
        pyproject_sha256 = sha256_file(snapshot / "pyproject.toml")
        uv_lock_sha256 = sha256_file(snapshot / "uv.lock")
        if pyproject_sha256 != technical_provenance.get("pyproject_sha256"):
            raise RuntimeError("certificate runtime pyproject.toml failed its SHA-256 check")
        if uv_lock_sha256 != technical_provenance.get("uv_lock_sha256"):
            raise RuntimeError("certificate runtime uv.lock failed its SHA-256 check")
        dependency_versions = _locked_dependency_versions(snapshot)
        if _installed_dependency_versions() != dependency_versions:
            raise RuntimeError(
                "installed solver/runtime dependencies do not match the certificate uv.lock"
            )
        runtime_marker: dict[str, object] = {
            "schema_version": 1,
            "git_commit": commit,
            "git_tree": tree,
            "snapshot_tree_sha256": source_tree_sha256,
            "snapshot_file_count": source_file_count,
            "pyproject_sha256": pyproject_sha256,
            "uv_lock_sha256": uv_lock_sha256,
            "dependency_versions": dependency_versions,
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
        }
        _make_snapshot_read_only(snapshot)
        (temporary / "runtime.json").write_text(
            json.dumps(runtime_marker, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)
        return target / "snapshot/src", runtime_marker
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _ledger_runtime_hashes(
    *,
    replay_runtime_mode: str,
    technical_provenance: Mapping[str, object],
) -> dict[str, str]:
    """Bind resumable checkpoints to the exact replay implementation."""

    paths = {
        "economic_event_ledger.py": Path(__file__),
        "firm_flexibility.py": _ROOT / "src/aidrbench/evaluation/firm_flexibility.py",
    }
    if replay_runtime_mode == "certificate_git_commit":
        paths["certificate_runtime_worker.py"] = (
            _ROOT / "scripts/economic_certificate_runtime_worker.py"
        )
    elif replay_runtime_mode == "current_worktree":
        paths.update(
            {
                "hourly_rollout.py": _ROOT / "src/aidrbench/evaluation/hourly_rollout.py",
                "community_ai_dr_env.py": _ROOT / "src/aidrbench/envs/community_ai_dr_env.py",
                "hourly_config.py": _ROOT / "src/aidrbench/envs/hourly_config.py",
                "hourly_controller.py": _ROOT / "src/aidrbench/controllers/hourly.py",
                "robust_mpc_spec.py": _ROOT / "src/aidrbench/controllers/robust_mpc_spec.py",
            }
        )
    else:
        raise ValueError(f"unsupported economic replay runtime: {replay_runtime_mode}")
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    runtime_identity = {
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "dependency_versions": _installed_dependency_versions(),
    }
    hashes["python_and_dependencies"] = hashlib.sha256(
        json.dumps(runtime_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if replay_runtime_mode == "certificate_git_commit":
        commit = technical_provenance.get("replay_git_commit")
        tree = technical_provenance.get("replay_git_tree")
        if not isinstance(commit, str) or not isinstance(tree, str):
            raise RuntimeError("certificate replay runtime has incomplete git provenance")
        hashes["certificate_git_commit"] = hashlib.sha256(commit.encode("ascii")).hexdigest()
        hashes["certificate_git_tree"] = hashlib.sha256(tree.encode("ascii")).hexdigest()
        source_hashes = technical_provenance.get("source_sha256")
        if not isinstance(source_hashes, Mapping):
            raise RuntimeError("certificate replay runtime has no source hashes")
        for path, digest in source_hashes.items():
            if not isinstance(path, str) or not isinstance(digest, str):
                raise RuntimeError("certificate replay source-hash provenance is invalid")
            hashes[f"certificate:{path}"] = digest
    return hashes


def _reservation_document(
    *,
    physical_ledger_contract_sha256: str,
    tasks: list[_ReplayGroupTask],
    include_interval_ledger: bool,
    runtime_sha256: Mapping[str, str],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "economic_paired_ledger_checkpoint_reservation",
        "physical_ledger_contract_sha256": physical_ledger_contract_sha256,
        "runtime_sha256": dict(sorted(runtime_sha256.items())),
        "include_interval_ledger": include_interval_ledger,
        "replay_group_count": len(tasks),
        "expected_event_row_count": sum(len(task.offer_fractions) for task in tasks),
        "task_sha256": [task.task_sha256 for task in tasks],
    }


def _prepare_checkpoint_workspace(
    output: Path,
    reservation: Mapping[str, object],
) -> tuple[Path, Path]:
    """Reserve an output name or reopen an exactly matching interrupted run."""

    if output.exists():
        raise FileExistsError(
            f"economic ledger output already exists; use a new output directory: {output}"
        )
    output = output.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = _checkpoint_workspace_for_output(output)
    reservation_path = work / "reservation.json"
    if work.exists():
        if not reservation_path.is_file():
            raise RuntimeError(
                "economic ledger checkpoint workspace has no reservation; inspect it before "
                f"manual removal: {work}"
            )
        observed = json.loads(reservation_path.read_text(encoding="utf-8"))
        if observed != dict(reservation):
            raise RuntimeError(
                "economic ledger checkpoint reservation does not match the current "
                "specification/runtime; use a different output directory"
            )
    else:
        work.mkdir(parents=False, exist_ok=False)
        temporary = work / ".reservation.json.tmp"
        temporary.write_text(
            json.dumps(reservation, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, reservation_path)
    checkpoints = work / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    return work, checkpoints


def _write_group_checkpoint(
    checkpoint_root: Path,
    *,
    task: _ReplayGroupTask,
    physical_ledger_contract_sha256: str,
    records: list[dict[str, Any]],
    intervals: pd.DataFrame,
) -> None:
    """Commit a complete replay group with an atomic directory rename."""

    target = checkpoint_root / task.task_sha256
    if target.exists():
        raise FileExistsError(f"economic replay checkpoint already exists: {target}")
    if len(records) != len(task.offer_fractions):
        raise RuntimeError("economic replay group returned an incomplete event ledger")
    event_frame = pd.DataFrame.from_records(records, columns=_LEDGER_COLUMNS)
    if tuple(event_frame.columns) != _LEDGER_COLUMNS:
        raise RuntimeError("economic replay checkpoint event schema drifted")
    if tuple(intervals.columns) != _INTERVAL_COLUMNS:
        raise RuntimeError("economic replay checkpoint interval schema drifted")

    temporary = Path(
        tempfile.mkdtemp(prefix=f".{task.task_sha256}.", suffix=".tmp", dir=checkpoint_root)
    )
    event_path = temporary / "events.parquet"
    interval_path = temporary / "intervals.parquet"
    event_frame.to_parquet(event_path, index=False)
    if task.include_interval_ledger:
        intervals.to_parquet(interval_path, index=False)
    metadata: dict[str, object] = {
        "schema_version": 1,
        "task_sha256": task.task_sha256,
        "task": task.identity_document(),
        "physical_ledger_contract_sha256": physical_ledger_contract_sha256,
        "event_row_count": len(event_frame),
        "interval_row_count": len(intervals) if task.include_interval_ledger else 0,
        "events_sha256": sha256_file(event_path),
        "intervals_sha256": sha256_file(interval_path) if task.include_interval_ledger else None,
    }
    (temporary / "checkpoint.json").write_text(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)


def _load_group_checkpoint(
    checkpoint_root: Path,
    *,
    task: _ReplayGroupTask,
    physical_ledger_contract_sha256: str,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    """Validate and load one committed group; never trust partial files."""

    checkpoint = checkpoint_root / task.task_sha256
    metadata_path = checkpoint / "checkpoint.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_scalars = {
        "schema_version": 1,
        "task_sha256": task.task_sha256,
        "task": task.identity_document(),
        "physical_ledger_contract_sha256": physical_ledger_contract_sha256,
        "event_row_count": len(task.offer_fractions),
    }
    for key, expected in expected_scalars.items():
        if metadata.get(key) != expected:
            raise RuntimeError(f"economic replay checkpoint mismatch: {key}")
    event_path = checkpoint / "events.parquet"
    if not event_path.is_file() or sha256_file(event_path) != metadata.get("events_sha256"):
        raise RuntimeError("economic replay event checkpoint failed its SHA-256 check")
    event_frame = pd.read_parquet(event_path)
    if tuple(event_frame.columns) != _LEDGER_COLUMNS or len(event_frame) != len(
        task.offer_fractions
    ):
        raise RuntimeError("economic replay event checkpoint has invalid shape/schema")
    observed_fractions = tuple(
        sorted(
            pd.to_numeric(
                event_frame["offer_fraction_of_technical_ceiling"], errors="raise"
            ).tolist()
        )
    )
    if observed_fractions != tuple(sorted(task.offer_fractions)):
        raise RuntimeError("economic replay checkpoint has the wrong offer fractions")
    if (
        set(event_frame["scenario_id"].astype(str)) != {task.scenario_id}
        or set(event_frame["scenario_hash"].astype(str)) != {task.scenario_hash}
        or set(pd.to_numeric(event_frame["episode_seed"], errors="raise")) != {task.episode_seed}
    ):
        raise RuntimeError("economic replay checkpoint has the wrong scenario identity")

    if task.include_interval_ledger:
        interval_path = checkpoint / "intervals.parquet"
        if not interval_path.is_file() or sha256_file(interval_path) != metadata.get(
            "intervals_sha256"
        ):
            raise RuntimeError("economic replay interval checkpoint failed its SHA-256 check")
        intervals = pd.read_parquet(interval_path)
        if tuple(intervals.columns) != _INTERVAL_COLUMNS or len(intervals) != int(
            metadata.get("interval_row_count", -1)
        ):
            raise RuntimeError("economic replay interval checkpoint has invalid shape/schema")
    else:
        if metadata.get("intervals_sha256") is not None or metadata.get("interval_row_count") != 0:
            raise RuntimeError("event-only checkpoint contains unexpected interval metadata")
        intervals = pd.DataFrame(columns=_INTERVAL_COLUMNS)
    records = cast(list[dict[str, Any]], event_frame.to_dict(orient="records"))
    return records, intervals


def _canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _git_show_bytes(commit: str, repository_path: str) -> bytes:
    """Read one repository-relative blob from an immutable commit."""

    path = Path(repository_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("legacy migration source path must be repository-relative")
    result = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError(
            "legacy ledger migration cannot read its declared source blob from "
            f"{commit}: {path.as_posix()}"
        )
    return result.stdout


def _legacy_v1_specification_sha256(document: Mapping[str, object]) -> str:
    """Reconstruct the canonical v1 specification hash without executing old code.

    The v1 parser coerced only the two primary payment coordinates from YAML
    integers to floats for the checked-in protocol.  This deliberately narrow
    adapter is a migration gate, not a general legacy parser.
    """

    if document.get("schema_version") != 1:
        raise ValueError("ledger-manifest migration accepts only a schema-v1 specification")
    evaluation = document.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise ValueError("legacy economic specification has no evaluation mapping")
    normalized = copy.deepcopy(dict(document))
    normalized_evaluation = copy.deepcopy(dict(evaluation))
    for key in (
        "primary_capacity_payment_per_kw_year",
        "primary_performance_payment_per_mwh",
    ):
        if key not in normalized_evaluation:
            raise ValueError(f"legacy economic specification is missing {key}")
        normalized_evaluation[key] = float(normalized_evaluation[key])
    normalized["evaluation"] = normalized_evaluation
    return _canonical_json_sha256(normalized)


def _legacy_v1_physical_contract(document: Mapping[str, object]) -> dict[str, object]:
    """Extract the v1 portions that determine an actual paired replay."""

    analysis_id = document.get("analysis_id")
    analysis_role = document.get("analysis_role")
    technical = document.get("technical")
    ledger = document.get("ledger")
    if (
        not isinstance(analysis_id, str)
        or not isinstance(analysis_role, str)
        or not isinstance(technical, Mapping)
        or not isinstance(ledger, Mapping)
    ):
        raise ValueError("legacy economic specification has an invalid physical contract")
    return {
        "contract_schema_version": 1,
        "analysis_id": analysis_id,
        "analysis_role": analysis_role,
        "technical": dict(technical),
        "ledger": dict(ledger),
    }


def _legacy_v1_input_hashes(document: Mapping[str, object]) -> dict[str, str]:
    """Read the complete declared v1 input digest map from an origin config."""

    technical = document.get("technical")
    inputs = document.get("inputs")
    if not isinstance(technical, Mapping) or not isinstance(inputs, Mapping):
        raise ValueError("legacy economic specification has invalid input sections")
    mapping = {
        "controller_config": technical.get("controller_config_sha256"),
        "technical_certificate": technical.get("technical_certificate_sha256"),
        "technical_certificate_manifest": technical.get("technical_certificate_manifest_sha256"),
        "technical_selection": technical.get("technical_selection_sha256"),
        "validation_scenario_receipt": technical.get("validation_scenario_receipt_sha256"),
        "locked_id_receipt": technical.get("locked_id_receipt_sha256"),
        "cost_parameter_grid": inputs.get("cost_parameter_grid_sha256"),
        "market_archetypes": inputs.get("market_archetypes_sha256"),
        "source_register": inputs.get("source_register_sha256"),
    }
    if not all(isinstance(value, str) and len(value) == 64 for value in mapping.values()):
        raise ValueError("legacy economic specification has invalid input SHA-256 values")
    return cast(dict[str, str], mapping)


def _verify_legacy_runtime_provenance(
    *,
    legacy_manifest: Mapping[str, object],
    technical_provenance: Mapping[str, object],
) -> None:
    """Verify every recorded replay-runtime hash without rerunning scenarios."""

    origin_commit = legacy_manifest.get("git_commit")
    recorded = legacy_manifest.get("source_sha256")
    if (
        not isinstance(origin_commit, str)
        or len(origin_commit) != 40
        or not isinstance(recorded, Mapping)
        or not recorded
    ):
        raise ValueError("legacy economic ledger has incomplete git/runtime provenance")
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{origin_commit}^{{commit}}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0 or resolved.stdout.strip() != origin_commit:
        raise ValueError("legacy economic ledger origin commit is unavailable locally")

    certificate_sources = technical_provenance.get("source_sha256")
    certificate_commit = technical_provenance.get("replay_git_commit")
    certificate_tree = technical_provenance.get("replay_git_tree")
    if (
        not isinstance(certificate_sources, Mapping)
        or not isinstance(certificate_commit, str)
        or not isinstance(certificate_tree, str)
    ):
        raise ValueError("current technical provenance is incomplete for ledger migration")
    expected_origin_paths = {
        "economic_event_ledger.py": "src/aidrbench/evaluation/economic_event_ledger.py",
        "firm_flexibility.py": "src/aidrbench/evaluation/firm_flexibility.py",
        "certificate_runtime_worker.py": "scripts/economic_certificate_runtime_worker.py",
    }
    runtime_identity = {
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "dependency_versions": _installed_dependency_versions(),
    }
    for key, expected in recorded.items():
        if not isinstance(key, str) or not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("legacy economic ledger has an invalid replay-runtime hash")
        if key in expected_origin_paths:
            actual = hashlib.sha256(
                _git_show_bytes(origin_commit, expected_origin_paths[key])
            ).hexdigest()
        elif key == "python_and_dependencies":
            actual = _canonical_json_sha256(runtime_identity)
        elif key == "certificate_git_commit":
            actual = hashlib.sha256(certificate_commit.encode("ascii")).hexdigest()
        elif key == "certificate_git_tree":
            actual = hashlib.sha256(certificate_tree.encode("ascii")).hexdigest()
        elif key.startswith("certificate:"):
            source_path = key.removeprefix("certificate:")
            observed = certificate_sources.get(source_path)
            if not isinstance(observed, str):
                raise ValueError(
                    "legacy runtime references a certificate source absent from current "
                    f"technical provenance: {source_path}"
                )
            actual = observed
        else:
            raise ValueError(f"legacy economic ledger has an unknown runtime hash key: {key}")
        if actual != expected:
            raise ValueError(f"legacy economic ledger runtime hash mismatch: {key}")


def migrate_legacy_paired_ledger_manifest(
    specification_path: str | Path,
    ledger_path: str | Path,
) -> dict[str, object]:
    """Atomically republish a verified schema-v2 ledger as a v3 physical contract.

    This is intentionally a narrow, fail-closed migration for the clean v1
    economics ledger.  It verifies the immutable origin configuration, all
    event/interval and scenario identities, physical evidence chain, and every
    runtime hash before replacing only ``ledger_manifest.json``.  It never
    replays or modifies a physical trajectory.
    """

    specification = load_economic_participation_specification(specification_path)
    path = Path(ledger_path).resolve()
    if path.name != "episode_ledger.parquet" or not path.is_file():
        raise ValueError("ledger migration requires an existing episode_ledger.parquet")
    manifest_path = path.with_name("ledger_manifest.json")
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    legacy_manifest_bytes = manifest_path.read_bytes()
    legacy_manifest = json.loads(legacy_manifest_bytes)
    if not isinstance(legacy_manifest, dict):
        raise ValueError("legacy economic ledger manifest must be a mapping")
    if legacy_manifest.get("schema_version") != 2:
        raise ValueError("ledger-manifest migration accepts only the legacy schema-v2 manifest")
    if "physical_ledger_contract_sha256" in legacy_manifest:
        raise ValueError("economic ledger manifest is already migrated to a physical contract")
    origin_commit = legacy_manifest.get("git_commit")
    raw_specification_path = legacy_manifest.get("specification_path")
    if not isinstance(origin_commit, str) or len(origin_commit) != 40:
        raise ValueError("legacy economic ledger has no immutable origin git commit")
    if not isinstance(raw_specification_path, str):
        raise ValueError("legacy economic ledger has no origin specification path")
    origin_bytes = _git_show_bytes(origin_commit, raw_specification_path)
    origin_document = yaml.safe_load(origin_bytes)
    if not isinstance(origin_document, Mapping):
        raise ValueError("legacy origin economic specification must be a YAML mapping")
    if _legacy_v1_specification_sha256(origin_document) != legacy_manifest.get(
        "specification_sha256"
    ):
        raise ValueError("legacy economic ledger specification hash fails origin verification")
    origin_contract = _legacy_v1_physical_contract(origin_document)
    if _canonical_json_sha256(origin_contract) != specification.physical_ledger_contract_sha256:
        raise ValueError(
            "legacy physical replay contract differs from the requested current protocol"
        )
    if origin_contract != specification.physical_ledger_contract():
        # JSON canonical equality above covers list/tuple representation; this
        # guard detects semantic fields not normalized by Python equality.
        origin_json = json.dumps(origin_contract, sort_keys=True, separators=(",", ":"))
        current_json = json.dumps(
            specification.physical_ledger_contract(), sort_keys=True, separators=(",", ":")
        )
        if origin_json != current_json:
            raise ValueError("legacy physical contract document differs from current protocol")

    legacy_input_hashes = legacy_manifest.get("input_sha256")
    if not isinstance(legacy_input_hashes, Mapping):
        raise ValueError("legacy economic ledger has no complete input hash map")
    expected_legacy_inputs = _legacy_v1_input_hashes(origin_document)
    if dict(legacy_input_hashes) != expected_legacy_inputs:
        raise ValueError("legacy economic ledger input hashes fail origin verification")
    current_physical_input_hashes = verify_physical_input_hashes(specification)
    expected_physical = {
        key: expected_legacy_inputs[key] for key in current_physical_input_hashes
    }
    if current_physical_input_hashes != expected_physical:
        raise ValueError("current physical inputs differ from the verified legacy replay")

    event_hash = sha256_file(path)
    if event_hash != legacy_manifest.get("event_ledger_sha256"):
        raise ValueError("legacy economic event ledger fails its SHA-256 verification")
    event_frame = pd.read_parquet(path)
    if tuple(event_frame.columns) != _LEDGER_COLUMNS or len(event_frame) != legacy_manifest.get(
        "event_row_count"
    ):
        raise ValueError("legacy economic event ledger has an invalid schema or row count")
    scenario_records = (
        event_frame.loc[:, ["episode_seed", "scenario_id", "scenario_hash"]]
        .drop_duplicates()
        .sort_values("episode_seed", kind="stable")
        .to_dict(orient="records")
    )
    scenario_hashes = [str(record["scenario_hash"]) for record in scenario_records]
    if (
        len(scenario_records) != legacy_manifest.get("scenario_count")
        or scenario_hashes != legacy_manifest.get("scenario_hashes")
        or scenario_set_sha256(scenario_records) != legacy_manifest.get("scenario_set_sha256")
        or scenario_set_sha256(scenario_records) != specification.technical.scenario_set_sha256
    ):
        raise ValueError("legacy economic ledger scenario provenance fails verification")
    interval_hash = legacy_manifest.get("interval_ledger_sha256")
    interval_path = path.with_name("interval_ledger.parquet")
    if interval_hash is None:
        if interval_path.exists() or legacy_manifest.get("interval_row_count") != 0:
            raise ValueError("legacy event-only ledger has inconsistent interval metadata")
    else:
        if not isinstance(interval_hash, str) or not interval_path.is_file():
            raise ValueError("legacy economic ledger interval artifact is missing")
        if sha256_file(interval_path) != interval_hash:
            raise ValueError("legacy economic interval ledger fails its SHA-256 verification")
        interval_frame = pd.read_parquet(interval_path)
        if (
            tuple(interval_frame.columns) != _INTERVAL_COLUMNS
            or len(interval_frame) != legacy_manifest.get("interval_row_count")
        ):
            raise ValueError("legacy economic interval ledger has an invalid schema or row count")

    technical_provenance = _validate_technical_certificate_provenance(specification)
    legacy_technical = legacy_manifest.get("technical_provenance")
    if not isinstance(legacy_technical, Mapping):
        raise ValueError("legacy economic ledger is missing technical provenance")
    for key in (
        "manifest_sha256",
        "controller_config_sha256",
        "technical_selection_sha256",
        "validation_scenario_receipt_sha256",
        "locked_id_receipt_sha256",
        "validation_scenario_hashes",
        "locked_id_scenario_hashes",
        "source_sha256",
        "replay_runtime_mode",
        "replay_git_commit",
        "replay_git_tree",
    ):
        if legacy_technical.get(key) != technical_provenance.get(key):
            raise ValueError(f"legacy economic ledger technical provenance mismatch: {key}")
    _verify_legacy_runtime_provenance(
        legacy_manifest=legacy_manifest,
        technical_provenance=technical_provenance,
    )

    migrated = dict(legacy_manifest)
    migrated["legacy_input_sha256"] = dict(expected_legacy_inputs)
    migrated.pop("input_sha256", None)
    migrated["schema_version"] = 3
    migrated["legacy_manifest_sha256"] = hashlib.sha256(legacy_manifest_bytes).hexdigest()
    migrated["legacy_manifest_schema_version"] = 2
    migrated["legacy_specification_sha256"] = legacy_manifest["specification_sha256"]
    migrated["physical_ledger_contract"] = specification.physical_ledger_contract()
    migrated["physical_ledger_contract_sha256"] = specification.physical_ledger_contract_sha256
    migrated["physical_input_sha256"] = current_physical_input_hashes
    migrated["manifest_migration"] = {
        "kind": "legacy_v2_to_physical_contract_v3",
        "verification": (
            "origin_specification_hash+physical_contract+physical_inputs+event_interval_"
            "hashes+scenario_set+technical_provenance+runtime_hashes"
        ),
        "economic_input_hashes_excluded_from_replay_contract": True,
        "trajectory_replay_performed": False,
    }
    temporary = manifest_path.with_name(f".{manifest_path.name}.migrate.tmp")
    if temporary.exists():
        raise FileExistsError(
            "refusing to overwrite existing ledger manifest staging file: "
            f"{temporary}"
        )
    temporary.write_text(
        json.dumps(migrated, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, manifest_path)
    return {
        "ledger_manifest": str(manifest_path),
        "ledger_manifest_sha256": sha256_file(manifest_path),
        "legacy_manifest_sha256": migrated["legacy_manifest_sha256"],
        "physical_ledger_contract_sha256": specification.physical_ledger_contract_sha256,
        "trajectory_replay_performed": False,
    }


def build_paired_event_ledger(
    specification_path: str | Path,
    output_directory: str | Path,
) -> dict[str, object]:
    """Replay the declared development set and write exact paired economic data."""

    # Capture this once, before a checkpoint workspace or final staging
    # directory can make an otherwise clean invocation appear dirty.
    run_git_state = _git_state()
    specification = load_economic_participation_specification(specification_path)
    physical_input_hashes = verify_physical_input_hashes(specification)
    technical_provenance = _validate_technical_certificate_provenance(specification)
    validation_hashes = technical_provenance.get("validation_scenario_hashes")
    locked_hashes = technical_provenance.get("locked_id_scenario_hashes")
    if not isinstance(validation_hashes, list) or not isinstance(locked_hashes, list):
        raise RuntimeError("technical evidence chain has no scenario allowlists")
    artifacts = _discover_artifacts(
        specification,
        validation_scenario_hashes=tuple(cast(list[str], validation_hashes)),
        locked_id_scenario_hashes=frozenset(cast(list[str], locked_hashes)),
    )
    technical_provenance = {
        **technical_provenance,
        **_validate_frozen_power_provenance(
            artifacts,
            technical_provenance=technical_provenance,
        ),
    }
    capacities = _certificate_capacities(specification)
    criteria_document = _criteria_document(specification)
    output = Path(output_directory).resolve(strict=False)
    tasks: list[_ReplayGroupTask] = []
    for duration_h in specification.technical.duration_hours:
        for notice_h in specification.technical.notice_hours:
            ceiling = capacities[(duration_h, notice_h)]
            for artifact in artifacts:
                tasks.append(
                    _ReplayGroupTask(
                        artifact_path=str(artifact.directory),
                        scenario_id=artifact.scenario_id,
                        scenario_hash=artifact.scenario_hash,
                        episode_seed=artifact.episode_seed,
                        controller_config=specification.technical.controller_config,
                        duration_h=duration_h,
                        notice_h=notice_h,
                        event_id=specification.technical.event_id,
                        technical_ceiling_kw=ceiling,
                        offer_fractions=specification.technical.offer_fractions,
                        criteria_document=criteria_document,
                        paired_pcc_tolerance_kw=(specification.ledger.paired_pcc_tolerance_kw),
                        work_conservation_tolerance_gpu_h=(
                            specification.ledger.work_conservation_tolerance_gpu_h
                        ),
                        include_interval_ledger=(specification.ledger.include_interval_ledger),
                        controller_config_sha256=(specification.technical.controller_config_sha256),
                        replay_runtime_mode=specification.technical.replay_runtime_mode,
                        replay_git_commit=specification.technical.replay_git_commit,
                        replay_git_tree=cast(
                            str | None, technical_provenance.get("replay_git_tree")
                        ),
                    )
                )
    if len({task.task_sha256 for task in tasks}) != len(tasks):
        raise RuntimeError("economic replay groups do not have unique checkpoint identities")
    runtime_hashes = _ledger_runtime_hashes(
        replay_runtime_mode=specification.technical.replay_runtime_mode,
        technical_provenance=technical_provenance,
    )
    reservation = _reservation_document(
        physical_ledger_contract_sha256=specification.physical_ledger_contract_sha256,
        tasks=tasks,
        include_interval_ledger=specification.ledger.include_interval_ledger,
        runtime_sha256=runtime_hashes,
    )
    work, checkpoint_root = _prepare_checkpoint_workspace(output, reservation)
    runtime_snapshot: dict[str, object] | None = None
    if specification.technical.replay_runtime_mode == "certificate_git_commit":
        runtime_source_root, runtime_snapshot = _prepare_certificate_runtime(
            work,
            technical_provenance=technical_provenance,
        )
        tasks = [replace(task, runtime_source_root=str(runtime_source_root)) for task in tasks]
    pending = [
        task
        for task in tasks
        if not (checkpoint_root / task.task_sha256 / "checkpoint.json").is_file()
    ]
    reused_checkpoint_count = len(tasks) - len(pending)
    computed_checkpoint_count = 0
    if specification.technical.workers == 1:
        try:
            for task in pending:
                records, intervals = _replay_group_task(task)
                _write_group_checkpoint(
                    checkpoint_root,
                    task=task,
                    physical_ledger_contract_sha256=specification.physical_ledger_contract_sha256,
                    records=records,
                    intervals=intervals,
                )
                computed_checkpoint_count += 1
        except Exception as error:
            raise RuntimeError(
                "economic replay group failed; completed groups are checkpointed under "
                f"{work} and the identical command will resume"
            ) from error
    elif pending:
        errors: list[Exception] = []
        with ProcessPoolExecutor(
            max_workers=min(specification.technical.workers, len(pending)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            futures = {executor.submit(_replay_group_task, task): task for task in pending}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    records, intervals = future.result()
                    _write_group_checkpoint(
                        checkpoint_root,
                        task=task,
                        physical_ledger_contract_sha256=specification.physical_ledger_contract_sha256,
                        records=records,
                        intervals=intervals,
                    )
                    computed_checkpoint_count += 1
                except Exception as error:  # preserve every other successful checkpoint
                    errors.append(error)
        if errors:
            raise RuntimeError(
                f"{len(errors)} economic replay group(s) failed; completed groups are "
                f"checkpointed under {work} and the identical command will resume"
            ) from errors[0]

    event_rows: list[dict[str, Any]] = []
    interval_frames: list[pd.DataFrame] = []
    for task in tasks:
        records, intervals = _load_group_checkpoint(
            checkpoint_root,
            task=task,
            physical_ledger_contract_sha256=specification.physical_ledger_contract_sha256,
        )
        event_rows.extend(records)
        if specification.ledger.include_interval_ledger:
            interval_frames.append(intervals)
    ledger = pd.DataFrame.from_records(event_rows, columns=_LEDGER_COLUMNS)
    expected_event_rows = sum(len(task.offer_fractions) for task in tasks)
    if len(ledger) != expected_event_rows:
        raise RuntimeError("economic ledger task accounting is incomplete")
    interval_ledger = (
        pd.concat(interval_frames, ignore_index=True)
        if interval_frames
        else pd.DataFrame(columns=_INTERVAL_COLUMNS)
    )
    ledger = ledger.sort_values(
        ["duration_h", "notice_h", "offer_fraction_of_technical_ceiling", "episode_seed"],
        kind="stable",
    ).reset_index(drop=True)
    interval_ledger = interval_ledger.sort_values(
        ["duration_h", "notice_h", "candidate_reduction_kw", "episode_seed", "hour"],
        kind="stable",
    ).reset_index(drop=True)
    if (
        _ledger_runtime_hashes(
            replay_runtime_mode=specification.technical.replay_runtime_mode,
            technical_provenance=technical_provenance,
        )
        != runtime_hashes
    ):
        raise RuntimeError(
            "economic replay source changed while the ledger was running; refusing to publish"
        )
    if specification.technical.replay_runtime_mode == "certificate_git_commit":
        _source_root, final_runtime_snapshot = _prepare_certificate_runtime(
            work,
            technical_provenance=technical_provenance,
        )
        if final_runtime_snapshot != runtime_snapshot:
            raise RuntimeError(
                "certificate runtime snapshot changed while the ledger was running; "
                "refusing to publish"
            )
    if verify_physical_input_hashes(specification) != physical_input_hashes:
        raise RuntimeError(
            "economic replay input changed while the ledger was running; refusing to publish"
        )
    staging = Path(tempfile.mkdtemp(prefix=".final.", suffix=".tmp", dir=work))
    ledger_path = staging / "episode_ledger.parquet"
    interval_path = staging / "interval_ledger.parquet"
    manifest_path = staging / "ledger_manifest.json"
    ledger.to_parquet(ledger_path, index=False)
    if specification.ledger.include_interval_ledger:
        interval_ledger.to_parquet(interval_path, index=False)
    manifest: dict[str, object] = {
        "schema_version": 3,
        "analysis_id": specification.analysis_id,
        "analysis_role": specification.analysis_role,
        "interpretation": (
            "paired development replay for parameterized operator-economics screening; "
            "not an independently locked economic certificate"
        ),
        "metric_time_basis": {
            "recovered_within_recovery_window_gpu_h": (
                "event_stop_hour <= hour < recovery_stop_hour"
            ),
            "recovered_through_episode_end_gpu_h": ("event_stop_hour <= hour <= episode_end_hour"),
            "incremental_backlog_area_within_recovery_gpu_h_h": (
                "event_start_hour <= hour < recovery_stop_hour"
            ),
            "incremental_backlog_area_through_episode_end_gpu_h_h": (
                "event_start_hour <= hour <= episode_end_hour"
            ),
            "incremental_energy_within_recovery_kwh": (
                "event_start_hour <= hour < recovery_stop_hour"
            ),
            "incremental_energy_through_episode_end_kwh": (
                "event_start_hour <= hour <= episode_end_hour"
            ),
            "missed_gpu_h": "event_start_hour <= hour <= episode_end_hour",
            "interval_ledger": "event_start_hour <= hour <= episode_end_hour",
        },
        "metric_definition": {
            "deferred_gpu_h": (
                "sum(max(no_dr_executed_gpu_h - controlled_executed_gpu_h, 0)) during the event"
            ),
            "recovered_*_gpu_h": (
                "gross catch-up: sum(max(controlled_executed_gpu_h - "
                "no_dr_executed_gpu_h, 0)) over the named post-event horizon; cascading "
                "rescheduling means this need not equal event-only deferred_gpu_h"
            ),
            "incremental_backlog_area_*_gpu_h_h": (
                "sum(max(controlled_backlog_gpu_h - no_dr_backlog_gpu_h, 0) * "
                "timestep_hours) over the named horizon"
            ),
            "incremental_energy_*_kwh": (
                "signed sum((controlled_pcc_power_kw - no_dr_pcc_power_kw) * "
                "timestep_hours) over the named horizon"
            ),
        },
        "specification_path": str(specification_path),
        # Retain the complete protocol hash as provenance only.  Evaluation
        # compatibility is intentionally gated by the physical contract below,
        # so a changed market or cost grid does not invalidate this replay.
        "specification_sha256": specification.sha256,
        "physical_ledger_contract": specification.physical_ledger_contract(),
        "physical_ledger_contract_sha256": specification.physical_ledger_contract_sha256,
        "physical_input_sha256": physical_input_hashes,
        "scenario_count": len(artifacts),
        "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
        "scenario_set_sha256": specification.technical.scenario_set_sha256,
        "technical_capacity_ceiling_kw": {
            f"H{duration_h}_N{notice_h}": capacity
            for (duration_h, notice_h), capacity in sorted(capacities.items())
        },
        "event_row_count": len(ledger),
        "interval_row_count": len(interval_ledger),
        "event_ledger_sha256": sha256_file(ledger_path),
        "interval_ledger_sha256": sha256_file(interval_path)
        if specification.ledger.include_interval_ledger
        else None,
        "replay_execution": {
            "replay_group_count": len(tasks),
            "logical_no_control_replay_count": len(tasks),
            "logical_controlled_replay_count": expected_event_rows,
            "reused_group_checkpoint_count": reused_checkpoint_count,
            "computed_group_checkpoint_count_this_invocation": computed_checkpoint_count,
            "checkpoint_commit": "atomic_directory_rename",
            "final_publish": "atomic_directory_rename",
        },
        "source_sha256": runtime_hashes,
        "technical_provenance": {
            **technical_provenance,
            "runtime_snapshot": runtime_snapshot,
        },
        **run_git_state,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(staging, output)
    _remove_published_checkpoint_workspace_or_raise(output)
    ledger_path = output / "episode_ledger.parquet"
    interval_path = output / "interval_ledger.parquet"
    manifest_path = output / "ledger_manifest.json"
    return {
        "episode_ledger": str(ledger_path),
        "interval_ledger": str(interval_path)
        if specification.ledger.include_interval_ledger
        else None,
        "ledger_manifest": str(manifest_path),
        "event_row_count": len(ledger),
        "interval_row_count": len(interval_ledger),
        "technical_capacity_ceiling_kw": manifest["technical_capacity_ceiling_kw"],
    }
