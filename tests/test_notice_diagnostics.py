from types import SimpleNamespace

import pandas as pd

from aidrbench.evaluation.notice_diagnostics import (
    _eligible_pre_execution_work_gpu_h,
)


def test_eligible_pre_execution_excludes_completed_historical_work() -> None:
    snapshot = SimpleNamespace(
        work_groups=(
            (0, 20, "training", 100.0),
            (11, 16, "training", 4.0),
            (12, 14, "training", 7.0),
            (14, 16, "offline_inference", 3.0),
        )
    )
    frame = pd.DataFrame(
        {
            "hour": [10],
            "decision_remaining_by_deadline_gpu_h": [
                (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
            ],
        }
    )

    eligible = _eligible_pre_execution_work_gpu_h(
        snapshot,
        frame,
        notice_start=10,
        event_start=16,
    )

    # Residual buckets due at/after hour 16 contribute 7 + 8. Of the newly
    # released work, only jobs whose deadline reaches hour 16 contribute 4 + 3.
    # The old 100 GPU-hour job is not double-counted merely because it once
    # had a long deadline.
    assert eligible == 22.0


def test_eligible_pre_execution_is_zero_without_notice() -> None:
    snapshot = SimpleNamespace(work_groups=((0, 20, "training", 100.0),))
    frame = pd.DataFrame(
        {
            "hour": [16],
            "decision_remaining_by_deadline_gpu_h": [(100.0,)],
        }
    )

    assert (
        _eligible_pre_execution_work_gpu_h(
            snapshot,
            frame,
            notice_start=16,
            event_start=16,
        )
        == 0.0
    )
