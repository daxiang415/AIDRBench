"""One-time CLI authorization guard for locked ID and OOD scenario generation."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.nature_protocol import validate_nature_mainline_protocol


@dataclass(frozen=True, slots=True)
class LockedOODAuthorization:
    """Frozen provenance captured immediately before a locked run."""

    manifest_path: Path
    manifest_sha256: str
    git_commit: str
    locked_set: str


def _document(path: Path, name: str) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be a YAML mapping")
    return {str(key): value for key, value in raw.items()}


def _locked_declaration(config_path: Path) -> tuple[str | None, Path | None]:
    config = _document(config_path, "scenario config")
    raw_scenario = config.get("scenario", {})
    if not isinstance(raw_scenario, dict):
        raise ValueError("scenario config scenario field must be a mapping")
    raw_locked_set = raw_scenario.get("locked_set")
    if raw_locked_set is None and raw_scenario.get("locked_ood") is True:
        raw_locked_set = "locked_ood"
    if raw_locked_set is not None and raw_locked_set not in {"locked_id", "locked_ood"}:
        raise ValueError("scenario.locked_set must be 'locked_id' or 'locked_ood'")
    locked_set = str(raw_locked_set) if raw_locked_set is not None else None
    raw_manifest = raw_scenario.get("preregistration_manifest")
    declared_manifest = Path(raw_manifest) if isinstance(raw_manifest, str) else None
    if locked_set is not None and declared_manifest is None:
        raise ValueError("locked config must declare scenario.preregistration_manifest")
    return locked_set, declared_manifest


def prepare_locked_ood_freeze(
    config_path: str | Path,
    *,
    output_directory: str | Path,
    preregistration_manifest: str | Path | None,
    unlock_locked_ood: bool,
    acknowledge_one_time_locked_use: bool,
) -> LockedOODAuthorization | None:
    """Authorize a locked run or return ``None`` for an ordinary config."""

    config = Path(config_path)
    locked_set, declared_manifest = _locked_declaration(config)
    if locked_set is None:
        return None
    if not unlock_locked_ood or not acknowledge_one_time_locked_use:
        raise ValueError(
            "locked scenario generation requires both --unlock-locked-ood and "
            "--acknowledge-one-time-locked-use"
        )
    if preregistration_manifest is None:
        raise ValueError("locked scenario generation requires --preregistration-manifest")
    manifest_path = Path(preregistration_manifest)
    if declared_manifest is None or manifest_path.resolve() != declared_manifest.resolve():
        raise ValueError("locked config and supplied preregistration manifest disagree")
    manifest = _document(manifest_path, "preregistration manifest")
    if manifest.get("analysis_plan_status") != "frozen":
        raise ValueError("locked analysis_plan_status must be 'frozen'")
    status_field = f"{locked_set}_status"
    if manifest.get(status_field) != "approved_for_one_time_run":
        raise ValueError(
            f"{locked_set} status must be 'approved_for_one_time_run' before first access"
        )
    report = validate_nature_mainline_protocol(manifest_path)
    if not report["structure_valid"] or not report["execution_ready"]:
        raise ValueError("locked protocol must be structurally valid and execution-ready")
    output = Path(output_directory)
    if output.exists():
        raise FileExistsError("locked output directory must not already exist")
    repository = Path(__file__).resolve().parents[3]
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise ValueError("locked generation requires a clean Git working tree")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return LockedOODAuthorization(
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        git_commit=commit,
        locked_set=locked_set,
    )


def consume_locked_ood_authorization(
    authorization: LockedOODAuthorization,
    *,
    output_directory: str | Path,
    scenario_hashes: list[str],
) -> Path:
    """Mark the authorization consumed and write an immutable run receipt."""

    output = Path(output_directory)
    receipt_path = output / f"{authorization.locked_set}_run_receipt.json"
    if receipt_path.exists():
        raise FileExistsError("locked run receipt already exists")
    manifest_text = authorization.manifest_path.read_text(encoding="utf-8")
    marker = f"{authorization.locked_set}_status: approved_for_one_time_run"
    if manifest_text.count(marker) != 1:
        raise RuntimeError("locked OOD manifest status changed during scenario generation")
    updated_manifest = manifest_text.replace(
        marker, f"{authorization.locked_set}_status: consumed", 1
    )
    temporary_manifest = authorization.manifest_path.with_suffix(".yaml.consuming")
    temporary_manifest.write_text(updated_manifest, encoding="utf-8")
    temporary_manifest.replace(authorization.manifest_path)
    receipt_path.write_text(
        json.dumps(
            {
                "protocol_path": str(authorization.manifest_path),
                "protocol_sha256_before_run": authorization.manifest_sha256,
                "git_commit": authorization.git_commit,
                "locked_set": authorization.locked_set,
                "scenario_hashes": scenario_hashes,
                "one_time_authorization_consumed": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt_path
