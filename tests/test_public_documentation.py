"""Reader-facing documentation links and research-file integrity."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    "README.md",
    "WINDOWS_START_HERE.md",
    "MAINLINE_FILES.md",
    "docs/README.md",
    "docs/getting-started.md",
    "docs/GITHUB_V027.md",
    "docs/figures.md",
    "docs/paper-packaging.md",
    "docs/nature-mainline-figure-preview.md",
    "docs/nature-supplementary-figure-preview.md",
    "manuscript/README.md",
    "paper/v0.27/latex/README.md",
    "paper/v0.27/figures/main/README.md",
    "paper/v0.27/figures/supplement/README.md",
)


def targets(text: str) -> list[str]:
    return re.findall(r"\]\(([^\s)]+)\)", text) + re.findall(
        r'(?:src|href)="([^"]+)"', text
    )


def test_public_documentation_targets_exist():
    for relative in PUBLIC_DOCS:
        source = ROOT / relative
        text = source.read_text(encoding="utf-8")
        assert not re.search(r"[\u3400-\u9fff]", text), relative
        for target in targets(text):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = (source.parent / unquote(url.path)).resolve()
            assert path.is_relative_to(ROOT), (relative, target)
            assert path.exists(), (relative, target)
            if url.fragment and path.suffix == ".md":
                headings = re.findall(
                    r"^#{1,6}\s+(.+)$", path.read_text(encoding="utf-8"), re.M
                )
                anchors = {
                    re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                    for heading in headings
                }
                assert unquote(url.fragment) in anchors, (relative, target)


def test_homepage_links_to_reference_pdfs():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    links = targets(text)
    assert "paper/v0.27/latex/main.pdf" in links
    assert "paper/v0.27/latex/supplement.pdf" in links
    assert not any(urlsplit(link).path.endswith(".tex") for link in links)
    assert "docs/assets/aidrbench-mascot.webp" in links


def test_public_guides_focus_on_reproduction():
    for relative in PUBLIC_DOCS:
        text = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "edit the manuscript" not in text, relative
        assert "edit the paper" not in text, relative
        assert "pending user information" not in text, relative
