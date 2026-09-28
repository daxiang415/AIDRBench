from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import aidrbench.evaluation.economic_event_ledger as ledger_module
from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario
from aidrbench.data.splits import sha256_file
from aidrbench.economics.specification import load_economic_participation_specification
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.economic_event_ledger import (
    _load_group_checkpoint,
    _prepare_certificate_runtime,
    _prepare_checkpoint_workspace,
    _replay_group_task,
    _ReplayGroupTask,
    _reservation_document,
    _validate_frozen_power_provenance,
    _validate_technical_certificate_provenance,
    _write_group_checkpoint,
)
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FROZEN_EXAMPLE = (
    _REPOSITORY_ROOT / "data/examples/nature_supplementary_validation_v1/hourly_seed_20000"
)
_CONTROLLER_CONFIG = str(_REPOSITORY_ROOT / "configs/controller/nature_robust_mpc_v1.yaml")


@pytest.fixture
def portable_certificate_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Relocate exact metadata fixtures while retaining production validation."""
    specification = load_economic_participation_specification(
        _REPOSITORY_ROOT / "configs/economics/economic_participation_v1.yaml"
    )
    technical = specification.technical
    fixture_root = _REPOSITORY_ROOT / "data/examples/economic_certificate_provenance_v1"
    original_resolve = ledger_module._resolve_protocol_path
    aliases = {}
    for path, expected in (
        (technical.technical_certificate_manifest, technical.technical_certificate_manifest_sha256),
        (technical.technical_selection_path, technical.technical_selection_sha256),
    ):
        fixture = fixture_root / Path(path).name
        assert sha256_file(fixture) == expected
        aliases[original_resolve(path)] = fixture

    def resolve(path: str) -> Path:
        original = original_resolve(path)
        return aliases.get(original, original)

    monkeypatch.setattr(ledger_module, "_resolve_protocol_path", resolve)


def _real_group(*, offer_fractions: tuple[float, ...] = (1.0,)) -> _ReplayGroupTask:
    artifact = load_frozen_hourly_scenario(_FROZEN_EXAMPLE)
    return _ReplayGroupTask(
        artifact_path=str(_FROZEN_EXAMPLE),
        scenario_id=artifact.scenario_id,
        scenario_hash=artifact.scenario_hash,
        episode_seed=artifact.episode_seed,
        controller_config=_CONTROLLER_CONFIG,
        duration_h=4,
        notice_h=0,
        event_id=0,
        technical_ceiling_kw=39.6505,
        offer_fractions=offer_fractions,
        criteria_document=FirmFlexibilityCriteria().as_dict(),
        paired_pcc_tolerance_kw=1e-8,
        work_conservation_tolerance_gpu_h=1e-6,
        include_interval_ledger=True,
    )


def test_real_frozen_replay_includes_clearance_tail_and_reuses_no_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _real_group(offer_fractions=(0.5, 1.0))
    original_no_control = ledger_module._no_control_frame
    original_controlled = ledger_module._controlled_frame
    no_control_calls = 0

    def counted_no_control(*args: object, **kwargs: object) -> pd.DataFrame:
        nonlocal no_control_calls
        no_control_calls += 1
        return original_no_control(*args, **kwargs)  # type: ignore[arg-type]

    def controlled_with_pre_event_miss(
        *args: object, **kwargs: object
    ) -> tuple[pd.DataFrame, HourlyCommunityAIDemandResponseEnv]:
        frame, environment = original_controlled(*args, **kwargs)  # type: ignore[arg-type]
        event_start = int(environment.event_manifest[0].start_hour)
        frame.loc[frame["hour"] < event_start, "missed_gpu_h"] += 123.0
        return frame, environment

    monkeypatch.setattr(ledger_module, "_no_control_frame", counted_no_control)
    monkeypatch.setattr(ledger_module, "_controlled_frame", controlled_with_pre_event_miss)
    records, intervals = _replay_group_task(task)

    assert no_control_calls == 1
    assert len(records) == 2
    assert intervals["candidate_reduction_kw"].nunique() == 2
    for record in records:
        assert (
            record["recovered_through_episode_end_gpu_h"]
            >= record["recovered_within_recovery_window_gpu_h"]
        )
        assert (
            record["incremental_backlog_area_through_episode_end_gpu_h_h"]
            >= record["incremental_backlog_area_within_recovery_gpu_h_h"]
        )
        assert record["backlog_at_recovery_stop_gpu_h"] > 0.0
        assert record["terminal_backlog_gpu_h"] == pytest.approx(0.0, abs=1e-8)
        assert record["missed_gpu_h"] == pytest.approx(0.0, abs=1e-8)

        candidate = float(record["candidate_reduction_kw"])
        trace = intervals[np.isclose(intervals["candidate_reduction_kw"], candidate)]
        nominal = trace[trace["within_recovery_window"]]
        clearance_tail = trace[trace["clearance_tail_active"]]
        post_event = trace[trace["relative_hour"] >= task.duration_h]
        nominal_recovery = nominal[nominal["relative_hour"] >= task.duration_h]

        assert not clearance_tail.empty
        assert int(trace["relative_hour"].max()) == 100
        assert record["incremental_energy_within_recovery_kwh"] == pytest.approx(
            float(nominal["pcc_delta_kw"].sum()), abs=1e-9
        )
        assert record["incremental_energy_through_episode_end_kwh"] == pytest.approx(
            float(trace["pcc_delta_kw"].sum()), abs=1e-9
        )
        assert record["incremental_energy_through_episode_end_kwh"] == pytest.approx(
            float(nominal["pcc_delta_kw"].sum()) + float(clearance_tail["pcc_delta_kw"].sum()),
            abs=1e-9,
        )
        assert record["incremental_backlog_area_within_recovery_gpu_h_h"] == pytest.approx(
            float(nominal["backlog_delta_gpu_h"].clip(lower=0.0).sum())
        )
        assert record["incremental_backlog_area_through_episode_end_gpu_h_h"] == pytest.approx(
            float(trace["backlog_delta_gpu_h"].clip(lower=0.0).sum())
        )
        assert record["recovered_within_recovery_window_gpu_h"] == pytest.approx(
            float(nominal_recovery["execution_delta_gpu_h"].clip(lower=0.0).sum())
        )
        assert record["recovered_through_episode_end_gpu_h"] == pytest.approx(
            float(post_event["execution_delta_gpu_h"].clip(lower=0.0).sum())
        )


def test_group_checkpoints_resume_only_under_identical_reservation(tmp_path: Path) -> None:
    task = _real_group()
    records, intervals = _replay_group_task(task)
    reservation = _reservation_document(
        physical_ledger_contract_sha256="a" * 64,
        tasks=[task],
        include_interval_ledger=True,
        runtime_sha256={"ledger": "b" * 64},
    )
    output = tmp_path / "ledger"
    work, checkpoints = _prepare_checkpoint_workspace(output, reservation)
    _write_group_checkpoint(
        checkpoints,
        task=task,
        physical_ledger_contract_sha256="a" * 64,
        records=records,
        intervals=intervals,
    )

    resumed_work, resumed_checkpoints = _prepare_checkpoint_workspace(output, reservation)
    loaded_records, loaded_intervals = _load_group_checkpoint(
        resumed_checkpoints,
        task=task,
        physical_ledger_contract_sha256="a" * 64,
    )
    assert resumed_work == work
    assert loaded_records[0]["scenario_hash"] == task.scenario_hash
    pd.testing.assert_frame_equal(loaded_intervals, intervals, check_dtype=False)

    event_checkpoint = resumed_checkpoints / task.task_sha256 / "events.parquet"
    with event_checkpoint.open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(RuntimeError, match="SHA-256"):
        _load_group_checkpoint(
            resumed_checkpoints,
            task=task,
            physical_ledger_contract_sha256="a" * 64,
        )

    mismatched = dict(reservation)
    mismatched["physical_ledger_contract_sha256"] = "c" * 64
    with pytest.raises(RuntimeError, match="reservation does not match"):
        _prepare_checkpoint_workspace(output, mismatched)

    (tmp_path / "already-published").mkdir()
    with pytest.raises(FileExistsError, match="output already exists"):
        _prepare_checkpoint_workspace(tmp_path / "already-published", reservation)


def test_published_ledger_cleanup_removes_read_only_certificate_runtime(tmp_path: Path) -> None:
    output = tmp_path / "ledger"
    workspace = ledger_module._checkpoint_workspace_for_output(output)
    snapshot = workspace / "certificate_runtime" / "snapshot" / "src"
    snapshot.mkdir(parents=True)
    read_only_file = snapshot / "pinned.py"
    read_only_file.write_text("immutable runtime\n", encoding="utf-8")
    for path in [*snapshot.rglob("*"), snapshot]:
        path.chmod(path.stat().st_mode & ~0o222)

    ledger_module._remove_published_checkpoint_workspace_or_raise(output)

    assert not workspace.exists()


def test_published_ledger_cleanup_reports_failure_for_exact_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "ledger"
    workspace = ledger_module._checkpoint_workspace_for_output(output)
    workspace.mkdir()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    observed_path: Path | None = None

    def refuse_cleanup(path: Path, **_kwargs: object) -> None:
        nonlocal observed_path
        observed_path = path
        raise PermissionError("deliberate cleanup failure")

    monkeypatch.setattr(ledger_module.shutil, "rmtree", refuse_cleanup)
    with pytest.raises(RuntimeError, match="could not clean its exact checkpoint workspace"):
        ledger_module._remove_published_checkpoint_workspace_or_raise(output)

    assert observed_path == workspace
    assert workspace.exists()
    assert unrelated.exists()


def test_ledger_manifest_captures_git_state_before_workspace_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specification = load_economic_participation_specification(
        _REPOSITORY_ROOT / "configs/economics/economic_participation_v1.yaml"
    )
    specification = replace(
        specification,
        technical=replace(
            specification.technical,
            replay_runtime_mode="current_worktree",
            replay_git_commit=None,
            duration_hours=(4,),
            notice_hours=(0,),
            workers=1,
        ),
    )
    output = tmp_path / "published_ledger"
    workspace = ledger_module._checkpoint_workspace_for_output(output)
    expected_git_state = {"git_commit": "b" * 40, "working_tree_dirty": False}
    input_hashes = {"declared_input": "c" * 64}
    calls = 0

    def capture_git_state() -> dict[str, object]:
        nonlocal calls
        calls += 1
        assert not output.exists()
        assert not workspace.exists()
        return expected_git_state

    monkeypatch.setattr(
        ledger_module, "load_economic_participation_specification", lambda _path: specification
    )
    monkeypatch.setattr(ledger_module, "verify_physical_input_hashes", lambda _spec: input_hashes)
    monkeypatch.setattr(
        ledger_module,
        "_validate_technical_certificate_provenance",
        lambda _spec: {"validation_scenario_hashes": [], "locked_id_scenario_hashes": []},
    )
    monkeypatch.setattr(ledger_module, "_discover_artifacts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        ledger_module, "_validate_frozen_power_provenance", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr(ledger_module, "_certificate_capacities", lambda _spec: {(4, 0): 1.0})
    monkeypatch.setattr(ledger_module, "_criteria_document", lambda _spec: {})
    monkeypatch.setattr(
        ledger_module, "_ledger_runtime_hashes", lambda **_kwargs: {"runtime": "d" * 64}
    )
    monkeypatch.setattr(ledger_module, "_git_state", capture_git_state)

    summary = ledger_module.build_paired_event_ledger("unused.yaml", output)
    manifest = json.loads(Path(str(summary["ledger_manifest"])).read_text(encoding="utf-8"))

    assert calls == 1
    assert manifest["git_commit"] == expected_git_state["git_commit"]
    assert manifest["working_tree_dirty"] is False
    assert not workspace.exists()


@pytest.mark.usefixtures("portable_certificate_files")
def test_certificate_git_runtime_replays_real_validation_scenario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A Windows-style Git setting must not rewrite the hash-bound archive.
    config_index = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(config_index + 1))
    monkeypatch.setenv(f"GIT_CONFIG_KEY_{config_index}", "core.autocrlf")
    monkeypatch.setenv(f"GIT_CONFIG_VALUE_{config_index}", "true")
    specification = load_economic_participation_specification(
        _REPOSITORY_ROOT / "configs/economics/economic_participation_v1.yaml"
    )
    provenance = _validate_technical_certificate_provenance(specification)
    artifact = load_frozen_hourly_scenario(_FROZEN_EXAMPLE)
    provenance = {
        **provenance,
        **_validate_frozen_power_provenance([artifact], technical_provenance=provenance),
    }
    work = tmp_path / "runtime-work"
    work.mkdir()
    source_root, runtime_marker = _prepare_certificate_runtime(
        work,
        technical_provenance=provenance,
    )
    task = replace(
        _real_group(),
        technical_ceiling_kw=39.65054527809973,
        controller_config="configs/controller/nature_robust_mpc_v1.yaml",
        controller_config_sha256=specification.technical.controller_config_sha256,
        replay_runtime_mode="certificate_git_commit",
        replay_git_commit=specification.technical.replay_git_commit,
        replay_git_tree=str(provenance["replay_git_tree"]),
        runtime_source_root=str(source_root),
    )
    records, intervals = _replay_group_task(task)

    assert runtime_marker["git_commit"] == specification.technical.replay_git_commit
    assert runtime_marker["git_tree"] == "07c7d6ab0f8e486e05ae93af7bbf52481e352a1d"
    assert len(records) == 1
    record = records[0]
    assert record["technical_success"] is True
    assert record["technical_failure_reasons"] == "none_technical_success"
    assert record["minimum_interval_delivery_ratio"] == pytest.approx(0.9711699, abs=1e-6)
    assert record["backlog_at_recovery_stop_gpu_h"] == pytest.approx(862.6787, abs=1e-3)
    assert record["terminal_backlog_gpu_h"] == pytest.approx(0.0, abs=1e-8)
    assert record["incremental_energy_through_episode_end_kwh"] == pytest.approx(0.0, abs=1e-4)
    assert len(intervals) == 101

    pinned_environment = source_root / "aidrbench/envs/community_ai_dr_env.py"
    pinned_environment.chmod(pinned_environment.stat().st_mode | 0o200)
    with pinned_environment.open("a", encoding="utf-8") as stream:
        stream.write("\n# deliberate test tamper\n")
    with pytest.raises(RuntimeError, match="SHA-256 verification"):
        _prepare_certificate_runtime(work, technical_provenance=provenance)


@pytest.mark.usefixtures("portable_certificate_files")
def test_certificate_git_runtime_rejects_commit_not_named_by_certificate() -> None:
    specification = load_economic_participation_specification(
        _REPOSITORY_ROOT / "configs/economics/economic_participation_v1.yaml"
    )
    mismatched = replace(
        specification,
        technical=replace(specification.technical, replay_git_commit="0" * 40),
    )
    with pytest.raises(ValueError, match="does not match the technical certificate"):
        _validate_technical_certificate_provenance(mismatched)
