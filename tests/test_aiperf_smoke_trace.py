from __future__ import annotations

import csv
from pathlib import Path

import pytest

from aidrbench.calibration.aiperf import make_burstgpt_smoke_trace


def _write_trace(path: Path) -> None:
    path.write_text(
        "Timestamp,Model,Request tokens,Response tokens,Total tokens,Log Type\n"
        "5,ChatGPT,100,20,120,Conversation log\n"
        "7,ChatGPT,0,20,20,Conversation log\n"
        "45,GPT-4,200,30,230,Conversation log\n"
        "105,GPT-4,300,40,340,Conversation log\n",
        encoding="utf-8",
    )


def test_smoke_trace_filters_and_compresses_relative_timestamps(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    output = tmp_path / "smoke.csv"
    _write_trace(source)

    summary = make_burstgpt_smoke_trace(source, output, requests=3, time_scale=20.0)
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["Timestamp"] for row in rows] == ["0", "2", "5"]
    assert [row["Request tokens"] for row in rows] == ["100", "200", "300"]
    assert summary["original_span_seconds"] == 100.0
    assert summary["replay_span_seconds"] == 5.0
    assert bool(summary["smoke_only"])
    assert summary["source_sha256"] != summary["output_sha256"]


def test_smoke_trace_requires_enough_valid_rows(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_trace(source)

    with pytest.raises(ValueError, match="only 3 valid rows"):
        make_burstgpt_smoke_trace(source, tmp_path / "smoke.csv", requests=4)


def test_smoke_trace_never_overwrites_source(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_trace(source)

    with pytest.raises(ValueError, match="must differ"):
        make_burstgpt_smoke_trace(source, source)
