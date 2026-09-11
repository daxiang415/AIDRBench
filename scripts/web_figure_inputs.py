"""Validate accepted, unchanged web-returned artwork before manuscript insertion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def validated_web_pdf(directory: Path, kind: str, root: Path) -> Path:
    manifest = json.loads((directory / "acceptance_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "accepted_web_return" or manifest["model"] != "GPT-6":
        raise ValueError("web artwork has not been accepted under the requested model route")
    if manifest["model_evidence"] != "user_confirmation":
        raise ValueError("model evidence must accurately reflect the user's confirmation")
    if len(manifest["reviews"]) != 3 or any(
        item["verdict"] != "PASS" for item in manifest["reviews"]
    ):
        raise ValueError("three completed passing reviews are required")
    name = {"figure6": "AIDRBench_Figure_6.pdf", "s5": "AIDRBench_Figure_S5.pdf"}[kind]
    pdf = (directory / name).resolve()
    pdf.relative_to(root)
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest["output_sha256"][name]:
        raise ValueError(f"web-return PDF hash mismatch: {name}")
    return pdf
