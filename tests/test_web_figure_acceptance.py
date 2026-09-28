"""Only accepted and unchanged web artwork may enter the manuscript renderer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/web_figure_inputs.py"
SPEC = importlib.util.spec_from_file_location("web_figure_inputs", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def accepted_fixture(directory: Path) -> tuple[Path, dict[str, object]]:
    pdf = directory / "AIDRBench_Figure_6.pdf"
    pdf.write_bytes(b"accepted figure bytes")
    manifest = {
        "status": "accepted_web_return",
        "model": "GPT-6",
        "model_evidence": "user_confirmation",
        "reviews": [{"verdict": "PASS"} for _ in range(3)],
        "output_sha256": {pdf.name: hashlib.sha256(pdf.read_bytes()).hexdigest()},
    }
    (directory / "acceptance_manifest.json").write_text(json.dumps(manifest))
    return pdf, manifest


def test_accepted_artwork_must_remain_byte_identical(tmp_path: Path) -> None:
    pdf, _ = accepted_fixture(tmp_path)
    assert MODULE.validated_web_pdf(tmp_path, "figure6", tmp_path) == pdf
    pdf.write_bytes(b"changed after acceptance")
    with pytest.raises(ValueError, match="hash mismatch"):
        MODULE.validated_web_pdf(tmp_path, "figure6", tmp_path)


@pytest.mark.parametrize("verdicts", [["PASS", "PASS"], ["PASS", "PASS", "REVISE"]])
def test_incomplete_or_failed_review_cannot_be_inserted(
    tmp_path: Path, verdicts: list[str]
) -> None:
    _, manifest = accepted_fixture(tmp_path)
    manifest["reviews"] = [{"verdict": value} for value in verdicts]
    (tmp_path / "acceptance_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="three completed passing reviews"):
        MODULE.validated_web_pdf(tmp_path, "figure6", tmp_path)


def test_local_draft_cannot_be_promoted_by_renderer(tmp_path: Path) -> None:
    _, manifest = accepted_fixture(tmp_path)
    manifest["status"] = "local_review_draft_only"
    (tmp_path / "acceptance_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="has not been accepted"):
        MODULE.validated_web_pdf(tmp_path, "figure6", tmp_path)
