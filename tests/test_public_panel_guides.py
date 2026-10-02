"""Keep the supplementary figure entry points readable and linked correctly."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("number", range(1, 11))
def test_supplementary_guide_links(number):
    folder = ROOT / f"paper/v0.27/figures/supplement/S{number:02d}"
    text = (folder / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"[\u3400-\u9fff]", text)
    assert f"redraw --figures S{number}" in text
    for target in re.findall(r"\]\(([^\s)]+)\)", text):
        assert (folder / target).exists(), target
