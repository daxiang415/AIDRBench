"""Verify all current numbered figures/tables and render pages for visual QA."""

import hashlib
import json
import re
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
report = {}
for stem, suffix, nfig in [
    ("main", "content_revision", 6),
    ("supplement", "Supplementary_Information_content_revision", 5),
]:
    path = ROOT / "manuscript/exports" / f"AIDRBench_Nature_Communications_v0.20_{suffix}.pdf"
    doc = fitz.open(path)
    texts = [page.get_text() for page in doc]
    text = "\n".join(texts)
    assert "\ufffd" not in text
    assert not re.search(r"[\u4e00-\u9fff]", text)
    prefix = r"Figure\s+" if stem == "main" else r"Supplementary\s+Figure\s+"
    for number in range(1, nfig + 1):
        assert re.search(prefix + str(number) + r"\s*\|", text), (stem, number)
    if stem == "supplement":
        for number in range(1, 10):
            assert re.search(r"Supplementary\s+Table\s+" + str(number) + r"\s*\|", text), number
    clipped = []
    thumbs = []
    for index, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    if x0 < -1 or y0 < -1 or x1 > page.rect.width + 1 or y1 > page.rect.height + 1:
                        clipped.append(
                            {"page": index + 1, "text": span["text"], "bbox": span["bbox"]}
                        )
        pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7))
        im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        im.thumbnail((315, 446))
        thumbs.append(im)
    assert not clipped, (stem, clipped)
    columns = 4
    rows = (len(thumbs) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * 325, rows * 470), "#dddddd")
    draw = ImageDraw.Draw(canvas)
    for i, im in enumerate(thumbs):
        x, y = (i % columns) * 325, (i // columns) * 470
        canvas.paste(im, (x, y + 20))
        draw.text((x + 8, y + 3), f"{stem} page {i + 1}", fill="black")
    canvas.save(HERE / f"{stem}_pdf_contact.png")
    report[stem] = dict(
        status="PASS",
        pages=len(doc),
        file=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        figures=nfig,
        numbered_tables=9 if stem == "supplement" else 0,
        no_text_outside_page=True,
    )
(HERE / "pdf_validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
