from __future__ import annotations

from pathlib import Path

import pytest

from aidrbench.evaluation.locked_ood import prepare_locked_ood_freeze

ROOT = Path(__file__).resolve().parents[1]


def test_ordinary_scenario_does_not_require_locked_authorization(tmp_path: Path) -> None:
    authorization = prepare_locked_ood_freeze(
        ROOT / "configs/env/nature_mainline_development.yaml",
        output_directory=tmp_path / "ordinary",
        preregistration_manifest=None,
        unlock_locked_ood=False,
        acknowledge_one_time_locked_use=False,
    )

    assert authorization is None


def test_locked_scenario_fails_before_data_access_without_explicit_acknowledgements(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="requires both"):
        prepare_locked_ood_freeze(
            ROOT / "configs/env/nature_mainline_locked_ood.yaml",
            output_directory=tmp_path / "locked",
            preregistration_manifest=None,
            unlock_locked_ood=False,
            acknowledge_one_time_locked_use=False,
        )


def test_locked_scenario_cannot_run_without_one_time_status_authorization(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="locked_ood status"):
        prepare_locked_ood_freeze(
            ROOT / "configs/env/nature_mainline_locked_ood.yaml",
            output_directory=tmp_path / "locked",
            preregistration_manifest=(
                ROOT / "data/manifests/nature_mainline_protocol_v1.yaml"
            ),
            unlock_locked_ood=True,
            acknowledge_one_time_locked_use=True,
        )
