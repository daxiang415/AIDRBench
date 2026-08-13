from __future__ import annotations

import pandas as pd
import pytest

from aidrbench.evaluation.envelopes import compare_static_envelopes


def test_static_envelope_comparison_reports_overcommitment() -> None:
    certificates = pd.DataFrame(
        {
            "controller": ["mpc"],
            "duration_h": [4],
            "certified_reduction_kw": [20.0],
            "dc_peak_kw": [100.0],
        }
    )

    comparison, summary = compare_static_envelopes(
        certificates,
        static_fractions=(0.20, 0.30),
    )

    static_30 = comparison.loc[comparison["static_fraction"] == 0.30].iloc[0]
    assert static_30["bias_kw"] == pytest.approx(10.0)
    assert static_30["static_overcommits"]
    assert summary.loc[summary["static_fraction"] == 0.30, "false_commitment_probability"].iloc[
        0
    ] == pytest.approx(1.0)
