"""Audit PDF glyph sizes, canvas bounds and the complete eleven-figure receipt."""

import hashlib
import json
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ART = ROOT / "docs/figures/workload_composition_v1/artwork"
rows = []
for prefix, count, manifest_name in [
    ("AIDRBench_Figure_", 6, "source_manifest.json"),
    ("AIDRBench_Supplementary_Figure_", 5, "supplement_source_manifest.json"),
]:
    manifest = json.loads((ART / manifest_name).read_text())
    for n in range(1, count + 1):
        stem = prefix + str(n)
        pdf = ART / f"{stem}.pdf"
        doc = fitz.open(pdf)
        assert len(doc) == 1
        page = doc[0]
        sizes = []
        spans = []
        assert abs(page.rect.width - 7.205 * 72) < 0.1
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    spans.append(span)
                    sizes.append(span["size"])
                    x0, y0, x1, y1 = span["bbox"]
                    assert (
                        x0 >= -0.5
                        and y0 >= -0.5
                        and x1 <= page.rect.width + 0.5
                        and y1 <= page.rect.height + 0.5
                    ), (stem, span)
        assert min(sizes) >= 6.49, (stem, min(sizes))
        text = page.get_text()
        assert "\ufffd" not in text
        for ext in ["pdf", "svg", "png", "tiff"]:
            file = ART / f"{stem}.{ext}"
            assert (
                hashlib.sha256(file.read_bytes()).hexdigest()
                == manifest["outputs"][file.name]["sha256"]
            )
        rows.append(
            dict(
                figure=stem,
                min_visible_font_pt=min(sizes),
                text_spans=len(spans),
                page_width_mm=page.rect.width / 72 * 25.4,
                editable_formats=["pdf", "svg"],
                all_four_output_hashes_match=True,
            )
        )
report = dict(
    status="PASS",
    figures=rows,
    figure_count=len(rows),
    visual_review="recorded separately after viewing all eleven PNG figures",
)
(HERE / "figure_validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
