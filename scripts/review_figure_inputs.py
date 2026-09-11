"""Validate local draft PDFs before optional insertion into review manuscripts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def validated_review_pdf(directory: Path, kind: str, root: Path) -> Path:
    manifest = json.loads((directory / "review_manifest.json").read_text(encoding="utf-8"))
    if (
        manifest["status"] != "local_review_draft_only"
        or manifest["formal_artwork_route"] != "web_gpt_required_by_user"
    ):
        raise ValueError("only explicitly labelled local review drafts may be inserted")
    pdf = (directory / f"{kind}_local_review.pdf").resolve()
    pdf.relative_to(root)
    expected = manifest["figures"][kind]["output_sha256"][pdf.name]
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != expected:
        raise ValueError(f"local draft PDF hash mismatch: {pdf.name}")
    return pdf
