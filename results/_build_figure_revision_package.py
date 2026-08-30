# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import html
import json
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from aidrbench.evaluation.figure_panel_data import (
    export_main_figure_panel_plot_data,
    export_supplementary_panel_plot_data,
)

ROOT = Path(__file__).resolve().parents[1]
STAMP = date.today().isoformat()
PACKAGE_NAME = f"AIDRBench_Figure_Revision_Package_{STAMP}"
EXPORT_ROOT = ROOT / "results" / "exports"
PACKAGE_ROOT = EXPORT_ROOT / PACKAGE_NAME
ZIP_PATH = EXPORT_ROOT / f"{PACKAGE_NAME}.zip"
SUMMARY_PATH = EXPORT_ROOT / f"{PACKAGE_NAME}_BUILD_SUMMARY.json"

MAIN_FIGURE_DIR = ROOT / "docs" / "figures" / "nature_mainline_v1"
SUPP_FIGURE_DIR = ROOT / "results" / "figures" / "nature_supplementary_v1"
SUPP_TRACKED_DIR = ROOT / "docs" / "figures" / "nature_supplementary_v1"
MAIN_SOURCE_DIR = ROOT / "manuscript" / "source_data" / "nature_mainline_v1"
SUPP_SOURCE_DIR = ROOT / "manuscript" / "source_data" / "nature_supplementary_v1"
ARTICLE_PATH = ROOT / "manuscript" / "nature_communications_article.md"
SI_PATH = ROOT / "manuscript" / "supplementary_information.md"
PANEL_MAP_PATH = ROOT / "configs" / "paper" / "nature_figure_panel_map_v1.yaml"

MAIN_SLUGS = {
    1: "Nominal_to_job_derived_gap",
    2: "Duration_reliability_and_notice",
    3: "Compute_debt_and_repeated_dispatch",
    4: "PV_hosting_utilisation_and_resource_interactions",
    5: "Sensitivity_certification_and_generalisation",
    6: "Community_profile_sensitivity",
}

MAIN_PLOT_FUNCTIONS = {
    1: "src/aidrbench/evaluation/nature_figures.py::plot_nature_mainline_figure1_reference_style",
    2: "src/aidrbench/evaluation/nature_figures_reference.py::plot_nature_mainline_figure2_reference_style",
    3: "src/aidrbench/evaluation/nature_figures_reference.py::plot_nature_mainline_figure3_reference_style",
    4: "src/aidrbench/evaluation/nature_figures_reference.py::plot_nature_mainline_figure4_reference_style",
    5: "src/aidrbench/evaluation/nature_figures_reference.py::plot_nature_mainline_figure5_reference_style",
    6: "src/aidrbench/evaluation/nature_figures_reference.py::plot_nature_mainline_figure6_reference_style",
}

SUPP_SLUGS = {
    1: "Environment_and_evidence_flow",
    2: "Four_GPU_power_calibration",
    3: "Observation_and_information_timing",
    4: "Representative_frozen_episode_transition",
}

SUPP_PLOT_FUNCTIONS = {
    1: "src/aidrbench/evaluation/supplementary_figures.py::_plot_environment_flow",
    2: "src/aidrbench/evaluation/supplementary_figures.py::_plot_calibration",
    3: "src/aidrbench/evaluation/supplementary_figures.py::_plot_observation",
    4: "src/aidrbench/evaluation/supplementary_figures.py::_plot_trajectory",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, destination: Path, *, required: bool = True) -> bool:
    if not source.exists():
        if required:
            raise FileNotFoundError(source)
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def copy_tree_files(source_root: Path, destination_root: Path, patterns: list[str]) -> None:
    for pattern in patterns:
        for source in sorted(source_root.glob(pattern)):
            if source.is_file():
                copy_file(source, destination_root / source.relative_to(source_root))


def extract_heading_block(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"Heading not found: {heading}")
    search_from = start + len(heading)
    next_heading = text.find("\n### ", search_from)
    next_section = text.find("\n## ", search_from)
    candidates = [value for value in (next_heading, next_section) if value >= 0]
    end = min(candidates) if candidates else len(text)
    return text[start:end].strip() + "\n"


def extract_between(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"Start marker not found: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        end = len(text)
    return text[start:end].strip() + "\n"


def main_figure_context(article: str, figure: int) -> str:
    boundaries = {
        1: (
            "### Nominal load flexibility overstates job-derived firm capacity",
            "### Duration and reliability shape firm flexibility whereas notice alone may not",
        ),
        2: (
            "### Duration and reliability shape firm flexibility whereas notice alone may not",
            "### Compute debt limits repeated dispatch before power delivery collapses",
        ),
        3: (
            "### Compute debt limits repeated dispatch before power delivery collapses",
            "### Job-feasible scheduling expands photovoltaic hosting without relying on deadline misses",
        ),
        4: (
            "### Job-feasible scheduling expands photovoltaic hosting without relying on deadline misses",
            "### Independent evaluation defines robustness and generalisation boundaries",
        ),
        5: (
            "### Independent evaluation defines robustness and generalisation boundaries",
            "We then isolated the community-profile component",
        ),
        6: (
            "We then isolated the community-profile component",
            "![Figure 5]",
        ),
    }
    start, end = boundaries[figure]
    block = extract_between(article, start, end)
    if figure == 6 and not block.startswith("###"):
        block = "### Community-profile sensitivity and system-value dependence\n\n" + block
    return block


def supplementary_mentions(si_text: str, figure: int) -> str:
    paragraphs = [p.strip() for p in si_text.split("\n\n") if p.strip()]
    needles = (
        f"Supplementary Fig. {figure}",
        f"Supplementary Figure {figure}",
        f"supplementary Fig. {figure}",
        f"supplementary figure {figure}",
    )
    selected = [paragraph for paragraph in paragraphs if any(needle in paragraph for needle in needles)]
    return "\n\n".join(selected).strip() + ("\n" if selected else "")


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def relative_posix(path: Path) -> str:
    return path.relative_to(PACKAGE_ROOT).as_posix()


def panel_figure_specification(
    panel_map: dict[str, Any],
    figure_label: str,
) -> dict[str, Any]:
    collection_name = "supplementary_figures" if figure_label.startswith("S") else "figures"
    collection = panel_map.get(collection_name)
    if not isinstance(collection, dict):
        raise ValueError(f"panel map is missing {collection_name}")
    specification = collection.get(figure_label)
    if not isinstance(specification, dict):
        raise ValueError(f"panel map is missing figure {figure_label}")
    return specification


def write_panel_bundle(
    figure_folder: Path,
    *,
    figure_label: str,
    panel_map: dict[str, Any],
    panel_records: dict[str, dict[str, Any]],
    panel_data_root: Path,
) -> dict[str, int]:
    specification = panel_figure_specification(panel_map, figure_label)
    panels = specification.get("panels")
    if not isinstance(panels, dict) or not panels:
        raise ValueError(f"figure {figure_label} has no panel specifications")

    guide_lines = [
        f"# Figure {figure_label} panel-by-panel guide",
        "",
        f"**Figure title:** {specification.get('title', '')}",
        "",
        "Read the artwork first, then use the matching panel CSV below. Every quantitative panel file contains the exact post-filter or post-aggregation values drawn by the renderer. Conceptual panels are explicitly marked as having no numerical plot data.",
        "",
    ]
    map_path = figure_folder / "PANEL_DATA_MAP.csv"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    quantitative_count = 0
    copied: set[str] = set()
    with map_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "figure",
                "panel",
                "kind",
                "plot_data_file",
                "row_count",
                "columns",
                "source_tables",
                "selection",
                "transformation",
                "question",
                "encoding",
                "statistic",
                "interpretation",
                "boundary",
                "sha256",
            ]
        )
        for panel, raw_panel in panels.items():
            if not isinstance(raw_panel, dict):
                raise ValueError(f"figure {figure_label} panel {panel} must be a mapping")
            plot_data = raw_panel.get("plot_data")
            record: dict[str, Any] | None = None
            if plot_data is not None:
                if not isinstance(plot_data, str) or plot_data not in panel_records:
                    raise ValueError(
                        f"figure {figure_label} panel {panel} lacks exact plot data: {plot_data}"
                    )
                record = panel_records[plot_data]
                if str(record.get("figure")) != figure_label:
                    raise ValueError(
                        f"panel data figure mismatch: {plot_data} belongs to {record.get('figure')}"
                    )
                if plot_data not in copied:
                    copy_file(
                        panel_data_root / plot_data,
                        figure_folder / "panel_level_plot_data" / plot_data,
                    )
                    copied.add(plot_data)
                quantitative_count += 1

            row_count = "" if record is None else record.get("row_count", "")
            columns = "" if record is None else ";".join(record.get("columns", []))
            source_tables = (
                "" if record is None else ";".join(record.get("source_tables", []))
            )
            selection = "not applicable" if record is None else str(record.get("selection", ""))
            transformation = (
                "not applicable" if record is None else str(record.get("transformation", ""))
            )
            digest = "" if record is None else str(record.get("output_sha256", ""))
            writer.writerow(
                [
                    figure_label,
                    panel,
                    raw_panel.get("kind", ""),
                    plot_data or "NO_NUMERIC_DATA",
                    row_count,
                    columns,
                    source_tables,
                    selection,
                    transformation,
                    raw_panel.get("question", ""),
                    raw_panel.get("encoding", ""),
                    raw_panel.get("statistic", ""),
                    raw_panel.get("interpretation", ""),
                    raw_panel.get("boundary", ""),
                    digest,
                ]
            )

            guide_lines.extend(
                [
                    f"## Panel {panel}",
                    "",
                    f"- **Chart type:** {raw_panel.get('kind', '')}",
                    f"- **Question:** {raw_panel.get('question', '')}",
                    f"- **How to read it:** {raw_panel.get('encoding', '')}",
                    f"- **Statistic / sample:** {raw_panel.get('statistic', '')}",
                    f"- **Interpretation:** {raw_panel.get('interpretation', '')}",
                    f"- **Do not infer:** {raw_panel.get('boundary', '')}",
                ]
            )
            if record is None:
                guide_lines.extend(
                    [
                        "- **Numerical plot data:** none; this is an explanatory schematic.",
                        "",
                    ]
                )
            else:
                guide_lines.extend(
                    [
                        f"- **Exact plotted CSV:** `panel_level_plot_data/{plot_data}`",
                        f"- **Rows:** {record.get('row_count')}",
                        f"- **Source table(s):** {', '.join(record.get('source_tables', []))}",
                        f"- **Row selection:** {record.get('selection', '')}",
                        f"- **Transformation:** {record.get('transformation', '')}",
                        f"- **Columns:** {', '.join(record.get('columns', []))}",
                        f"- **CSV SHA-256:** `{record.get('output_sha256', '')}`",
                        "",
                    ]
                )
    write_text(figure_folder / "PANEL_GUIDE.md", "\n".join(guide_lines).strip() + "\n")
    return {
        "panel_count": len(panels),
        "quantitative_panel_count": quantitative_count,
        "unique_panel_data_files": len(copied),
    }


def inventory_role(relative: Path) -> str:
    path = relative.as_posix()
    if path.startswith("00_MANUSCRIPT/"):
        return "authoritative manuscript text or manuscript-level guide"
    if path.startswith("01_MAIN_FIGURES/"):
        return "main-figure artwork, panel guide, exact panel data, upstream data, or manifest"
    if path.startswith("02_SUPPLEMENTARY_FIGURES/"):
        return "supplementary-figure artwork, panel guide, exact panel data, input, or manifest"
    if path.startswith("03_PANEL_LEVEL_PLOT_DATA/"):
        return "central copy of exact post-filter or post-aggregation panel values"
    if path.startswith("04_ALL_SOURCE_DATA/"):
        return "complete upstream manuscript Source Data or its specification"
    if path.startswith("05_PLOTTING_CODE_AND_SPECS/"):
        return "standalone plotting source, dependency lock, configuration, or reproduction input"
    if path.startswith("06_PROVENANCE_AND_AUDIT/"):
        return "protocol, source provenance, result receipt, or repository state"
    if path == "OPEN_ME.html":
        return "browser index for all figures and panel guides"
    if path in {"README_FIRST.md", "START_HERE.md"}:
        return "root package instructions"
    if path == "FIGURE_DATA_MAP.csv":
        return "figure-to-upstream-source-data map"
    if path == "FILE_INVENTORY.csv":
        return "inventory of every package member except the checksum file"
    if path == "VERIFY_PACKAGE.py":
        return "stdlib-only checksum and panel-data verifier"
    if path == "SHA256SUMS.txt":
        return "SHA-256 integrity list for all preceding package members"
    return "package support file"


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build() -> dict[str, Any]:
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)

    article = ARTICLE_PATH.read_text(encoding="utf-8")
    si_text = SI_PATH.read_text(encoding="utf-8")
    source_manifest = json.loads((MAIN_SOURCE_DIR / "source_data_manifest.json").read_text(encoding="utf-8"))
    panel_map = yaml.safe_load(PANEL_MAP_PATH.read_text(encoding="utf-8"))
    if not isinstance(panel_map, dict):
        raise ValueError("figure panel map must be a mapping")

    panel_data_root = PACKAGE_ROOT / "03_PANEL_LEVEL_PLOT_DATA"
    main_panel_data_root = panel_data_root / "main_figures"
    supplementary_panel_data_root = panel_data_root / "supplementary_figures"
    main_panel_manifest = export_main_figure_panel_plot_data(
        MAIN_SOURCE_DIR,
        main_panel_data_root,
    )
    supplementary_panel_manifest = export_supplementary_panel_plot_data(
        SUPP_SOURCE_DIR,
        ROOT / "configs" / "paper" / "nature_supplementary_figures_v1.yaml",
        supplementary_panel_data_root,
        repository_root=ROOT,
    )
    main_panel_records = {
        str(record["output"]): record for record in main_panel_manifest["panels"]
    }
    supplementary_panel_records = {
        str(record["output"]): record
        for record in supplementary_panel_manifest["panels"]
    }
    declared_panel_outputs = {
        str(panel["plot_data"])
        for collection_name in ("figures", "supplementary_figures")
        for figure in panel_map[collection_name].values()
        for panel in figure["panels"].values()
        if panel.get("plot_data") is not None
    }
    produced_panel_outputs = set(main_panel_records) | set(supplementary_panel_records)
    if declared_panel_outputs != produced_panel_outputs:
        raise ValueError(
            "panel guide and exact plot-data outputs differ: "
            f"declared-only={sorted(declared_panel_outputs - produced_panel_outputs)}, "
            f"produced-only={sorted(produced_panel_outputs - declared_panel_outputs)}"
        )
    copy_file(PANEL_MAP_PATH, panel_data_root / PANEL_MAP_PATH.name)

    git_commit = git_value("rev-parse", "HEAD")
    git_status = git_value("status", "--short", "--branch")

    # 00 - manuscript master files
    manuscript_dir = PACKAGE_ROOT / "00_MANUSCRIPT"
    manuscript_files = [
        "nature_communications_article.md",
        "supplementary_information.md",
        "terminology-ledger.md",
        "results-evidence-allocation.md",
        "submission-readiness.md",
        "README.md",
    ]
    for filename in manuscript_files:
        copy_file(ROOT / "manuscript" / filename, manuscript_dir / filename)

    all_legends = article[article.find("## Figure Legends") :].strip() + "\n"
    write_text(manuscript_dir / "FIGURE_LEGENDS_1_TO_6.md", all_legends)
    write_text(
        manuscript_dir / "README_FIRST.md",
        """# 文稿主文件说明

- **当前权威主文稿**：`nature_communications_article.md`，已经包含主图 Figure 1-6。
- **当前权威补充材料**：`supplementary_information.md`，包含 Supplementary Figure S1-S4。
- 本图稿包不包含旧版 review PDF，避免第三方把不含 Figure 6 的历史文件误认为当前母版。
- 每张图对应的正文段落和图注，已经再次复制到各自图文件夹中，修改绘图时无需反复查找全文。
""",
    )

    # Main figures
    main_rows: list[dict[str, Any]] = []
    main_summaries: list[dict[str, Any]] = []
    for figure, slug in MAIN_SLUGS.items():
        figure_folder = PACKAGE_ROOT / "01_MAIN_FIGURES" / f"Figure_{figure:02d}_{slug}"
        artwork_dir = figure_folder / "artwork"
        exact_data_dir = figure_folder / "data_used_by_current_plot"
        supporting_dir = figure_folder / "supporting_or_scenario_level_data"
        manifest_dir = figure_folder / "manifests"

        manifest_path = MAIN_FIGURE_DIR / f"figure_{figure}_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        copy_file(manifest_path, manifest_dir / manifest_path.name)

        for output in manifest["outputs"]:
            source = MAIN_FIGURE_DIR / output["path"]
            actual_hash = sha256(source)
            if actual_hash != output["sha256"]:
                raise ValueError(f"Figure {figure} artwork hash mismatch: {source}")
            copy_file(source, artwork_dir / source.name)

        exact_ids = set(manifest.get("source_tables", []))
        associated_tables = [table for table in source_manifest["tables"] if figure in table.get("figures", [])]
        table_subset: list[dict[str, Any]] = []
        for table in associated_tables:
            table_id = table["table_id"]
            source = MAIN_SOURCE_DIR / table["output"]
            actual_hash = sha256(source)
            if actual_hash != table["output_sha256"]:
                raise ValueError(f"Source Data hash mismatch: {source}")
            exact = table_id in exact_ids
            destination_dir = exact_data_dir if exact else supporting_dir
            copy_file(source, destination_dir / source.name)
            record = {
                "figure": figure,
                "table_id": table_id,
                "filename": table["output"],
                "used_by_current_plot": exact,
                "panels": table.get("panels", []),
                "row_count": table.get("row_count"),
                "columns": table.get("columns", []),
                "output_sha256": table.get("output_sha256"),
                "original_inputs": table.get("inputs", []),
            }
            table_subset.append(record)
            main_rows.append(record)

        missing_exact = exact_ids.difference({table["table_id"] for table in associated_tables})
        if missing_exact:
            raise ValueError(f"Figure {figure} exact source tables missing from Source Data manifest: {missing_exact}")

        json_dump(manifest_dir / "figure_data_manifest_subset.json", table_subset)
        context = main_figure_context(article, figure)
        legend = extract_heading_block(article, f"### Figure {figure} |")
        write_text(figure_folder / "MANUSCRIPT_CONTEXT.md", context)
        write_text(figure_folder / "FIGURE_LEGEND.md", legend)
        panel_bundle_summary = write_panel_bundle(
            figure_folder,
            figure_label=str(figure),
            panel_map=panel_map,
            panel_records=main_panel_records,
            panel_data_root=main_panel_data_root,
        )

        readme_lines = [
            f"# Figure {figure}: {slug.replace('_', ' ')}",
            "",
            f"**当前绘图函数**：`{MAIN_PLOT_FUNCTIONS[figure]}`",
            "",
            f"**当前核心结论**：{manifest.get('core_conclusion', '')}",
            "",
            "## 文件结构",
            "",
            "- `artwork/`：当前 SVG、PDF、TIFF、PNG。SVG/PDF 适合结构修改，TIFF/PNG 用于投稿与快速检查。",
            "- `PANEL_GUIDE.md`：逐面板说明问题、坐标/颜色/符号、统计单位、解释边界、筛选与转换。",
            "- `PANEL_DATA_MAP.csv`：机器可读的一对一 panel-data 映射。",
            "- `panel_level_plot_data/`：每个定量面板实际绘制的最终 CSV，不需要查看者自行猜测筛选或聚合。",
            "- `data_used_by_current_plot/`：renderer 读取的上游 CSV，可能包含比最终面板更多的组别或观测。",
            "- `supporting_or_scenario_level_data/`：属于本图但当前 renderer 没有直接读取的更细粒度表。",
            "- `MANUSCRIPT_CONTEXT.md`：正文中解释本图结果的段落。",
            "- `FIGURE_LEGEND.md`：当前图注。",
            "- `manifests/`：图件 hash、数据表、panel、列名和原始输入追踪。",
            "",
            "## 当前图直接使用的数据",
            "",
        ]
        exact_records = [record for record in table_subset if record["used_by_current_plot"]]
        for record in exact_records:
            panels = ", ".join(record["panels"]) or "未单列"
            readme_lines.append(
                f"- `{record['filename']}` - panels: {panels}; rows: {record['row_count']}"
            )
        supporting_records = [record for record in table_subset if not record["used_by_current_plot"]]
        if supporting_records:
            readme_lines.extend(["", "## 可用于重新设计的更细粒度数据", ""])
            for record in supporting_records:
                panels = ", ".join(record["panels"]) or "supporting"
                readme_lines.append(
                    f"- `{record['filename']}` - panels/source role: {panels}; rows: {record['row_count']}"
                )
        if manifest.get("claim_boundaries"):
            readme_lines.extend(["", "## 不能在改图时改变的解释边界", ""])
            readme_lines.extend(f"- {boundary}" for boundary in manifest["claim_boundaries"])
        write_text(figure_folder / "README.md", "\n".join(readme_lines).strip() + "\n")

        main_summaries.append(
            {
                "figure": figure,
                "folder": relative_posix(figure_folder),
                "artwork_files": len(manifest["outputs"]),
                "exact_plot_tables": len(exact_records),
                "supporting_tables": len(supporting_records),
                "plot_function": MAIN_PLOT_FUNCTIONS[figure],
                "core_conclusion": manifest.get("core_conclusion", ""),
                **panel_bundle_summary,
            }
        )

    # Supplementary figures
    supp_summaries: list[dict[str, Any]] = []
    for figure, slug in SUPP_SLUGS.items():
        figure_folder = PACKAGE_ROOT / "02_SUPPLEMENTARY_FIGURES" / f"Supplementary_Figure_S{figure}_{slug}"
        artwork_dir = figure_folder / "artwork"
        data_dir = figure_folder / "data_used_by_current_plot"
        input_dir = figure_folder / "configuration_and_provenance_inputs"
        manifest_dir = figure_folder / "manifests"

        manifest_path = SUPP_TRACKED_DIR / f"supplementary_figure_{figure}_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        copy_file(manifest_path, manifest_dir / manifest_path.name)

        artwork_count = 0
        for output in manifest.get("outputs", []):
            source = SUPP_FIGURE_DIR / output["path"]
            if not source.exists():
                source = SUPP_TRACKED_DIR / output["path"]
            actual_hash = sha256(source)
            if actual_hash != output["sha256"]:
                raise ValueError(f"Supplementary Figure S{figure} artwork hash mismatch: {source}")
            copy_file(source, artwork_dir / source.name)
            artwork_count += 1

        # Copy all four available formats even if the tracked manifest was generated from a subset.
        for extension in ("svg", "pdf", "tiff", "png"):
            source = SUPP_FIGURE_DIR / f"supplementary_figure_{figure}.{extension}"
            if source.exists() and not (artwork_dir / source.name).exists():
                copy_file(source, artwork_dir / source.name)
                artwork_count += 1

        data_records: list[dict[str, Any]] = []
        for item in manifest.get("source_data", []):
            source = SUPP_SOURCE_DIR / item["path"]
            actual_hash = sha256(source)
            if actual_hash != item["sha256"]:
                raise ValueError(f"Supplementary Source Data hash mismatch: {source}")
            copy_file(source, data_dir / source.name)
            data_records.append(item)

        for source_item in manifest.get("sources", []):
            declared_path = Path(source_item["path"])
            source = declared_path if declared_path.is_absolute() else ROOT / declared_path
            actual_hash = sha256(source)
            if actual_hash != source_item["sha256"]:
                raise ValueError(f"Supplementary source hash mismatch: {source}")
            try:
                destination_relative = source.relative_to(ROOT)
            except ValueError:
                destination_relative = Path(source.name)
            copy_file(source, input_dir / destination_relative)

        if figure == 4:
            copy_file(
                SUPP_SOURCE_DIR / "representative_trajectory_metadata.json",
                data_dir / "representative_trajectory_metadata.json",
                required=False,
            )

        legend = extract_heading_block(si_text, f"### Supplementary Figure {figure} |")
        mentions = supplementary_mentions(si_text, figure)
        write_text(figure_folder / "FIGURE_LEGEND.md", legend)
        write_text(
            figure_folder / "SUPPLEMENTARY_TEXT_CONTEXT.md",
            mentions or "No additional explicit in-text mention was found beyond the figure legend.\n",
        )
        panel_bundle_summary = write_panel_bundle(
            figure_folder,
            figure_label=f"S{figure}",
            panel_map=panel_map,
            panel_records=supplementary_panel_records,
            panel_data_root=supplementary_panel_data_root,
        )

        readme_lines = [
            f"# Supplementary Figure S{figure}: {slug.replace('_', ' ')}",
            "",
            f"**当前绘图函数**：`{SUPP_PLOT_FUNCTIONS[figure]}`",
            "",
            f"**当前核心结论**：{manifest.get('core_conclusion', '')}",
            "",
            "- `artwork/`：当前可用 SVG、PDF、TIFF、PNG。",
            "- `PANEL_GUIDE.md`：逐面板说明图形含义、统计单位、筛选、转换和解释边界。",
            "- `PANEL_DATA_MAP.csv`：机器可读的一对一 panel-data 映射。",
            "- `panel_level_plot_data/`：面板最终绘制值；结构示意面板明确标记为无数值数据。",
            "- `data_used_by_current_plot/`：本图导出的上游 CSV/JSON，可能包含最终显示窗口之外的记录。",
            "- `configuration_and_provenance_inputs/`：生成本图所读取的协议、配置或 source manifest。",
            "- `FIGURE_LEGEND.md`：当前补充图图注。",
            "- `SUPPLEMENTARY_TEXT_CONTEXT.md`：补充材料中与本图直接相关的文字。",
            "- `manifests/`：输出和输入 hash。",
        ]
        write_text(figure_folder / "README.md", "\n".join(readme_lines).strip() + "\n")
        supp_summaries.append(
            {
                "figure": f"S{figure}",
                "folder": relative_posix(figure_folder),
                "artwork_files": artwork_count,
                "plot_data_files": len(data_records) + (1 if figure == 4 else 0),
                "configuration_inputs": len(manifest.get("sources", [])),
                "plot_function": SUPP_PLOT_FUNCTIONS[figure],
                "core_conclusion": manifest.get("core_conclusion", ""),
                **panel_bundle_summary,
            }
        )

    # Complete Source Data copies
    all_data_dir = PACKAGE_ROOT / "04_ALL_SOURCE_DATA"
    copy_tree_files(MAIN_SOURCE_DIR, all_data_dir / "main_figures_1_to_6", ["*.csv", "*.json", "README.md"])
    copy_tree_files(SUPP_SOURCE_DIR, all_data_dir / "supplementary_figures_S1_to_S4", ["*.csv", "*.json", "README.md"])
    copy_file(
        ROOT / "configs" / "paper" / "nature_source_data_v1.yaml",
        all_data_dir / "source_data_specifications" / "nature_source_data_v1.yaml",
    )
    copy_file(
        ROOT / "configs" / "paper" / "nature_supplementary_figures_v1.yaml",
        all_data_dir / "source_data_specifications" / "nature_supplementary_figures_v1.yaml",
    )

    # Plotting implementation and specifications
    plotting_dir = PACKAGE_ROOT / "05_PLOTTING_CODE_AND_SPECS"
    code_files = [
        "src/aidrbench/evaluation/nature_figures.py",
        "src/aidrbench/evaluation/nature_figures_reference.py",
        "src/aidrbench/evaluation/supplementary_figures.py",
        "src/aidrbench/evaluation/source_data.py",
        "src/aidrbench/evaluation/figure_panel_data.py",
        "src/aidrbench/cli.py",
        "configs/paper/nature_source_data_v1.yaml",
        "configs/paper/nature_supplementary_figures_v1.yaml",
        "configs/paper/nature_figure_panel_map_v1.yaml",
        "docs/paper-packaging.md",
        "README.md",
        "pyproject.toml",
        "uv.lock",
    ]
    for relative in code_files:
        copy_file(ROOT / relative, plotting_dir / relative)
    copy_tree_files(
        ROOT / "src" / "aidrbench",
        plotting_dir / "src" / "aidrbench",
        ["**/*.py"],
    )
    supplementary_reproduction_files = [
        "data/manifests/nature_mainline_protocol_v1.yaml",
        "data/manifests/sources.yaml",
        "configs/env/nature_mainline_validation.yaml",
        "configs/controller/nature_robust_mpc_v1.yaml",
        "data/calibration/rtx6000pro_4gpu_v1.yaml",
        "data/calibration/rtx6000pro_4gpu_v1_fit/run_gpu_means.parquet",
    ]
    for relative in supplementary_reproduction_files:
        copy_file(ROOT / relative, plotting_dir / relative)
    copy_tree_files(
        ROOT / "data" / "examples" / "nature_supplementary_validation_v1",
        plotting_dir / "data" / "examples" / "nature_supplementary_validation_v1",
        ["**/*"],
    )
    copy_file(Path(__file__), plotting_dir / "package_builder.py")
    write_text(
        plotting_dir / "REGENERATE_COMMANDS.sh",
        """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Keep all generated state inside the extracted package so the command also
# works when the reader's home directory or global uv cache is read-only.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$SCRIPT_DIR/.uv-cache}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$SCRIPT_DIR/.venv}"

# The extracted package contains the full Python source and figure-specific inputs.
uv run --frozen --extra analysis --extra control aidrbench paper figures \\
  --source-data ../04_ALL_SOURCE_DATA/main_figures_1_to_6 \\
  --output reproduced/main_figures \\
  --figures 1 2 3 4 5 6 \\
  --formats svg pdf tiff png

uv run --frozen --extra analysis --extra control aidrbench paper supplementary-figures \\
  --specification configs/paper/nature_supplementary_figures_v1.yaml \\
  --output reproduced/supplementary_figures \\
  --figures 1 2 3 4 \\
  --formats svg pdf tiff png
""",
    )
    function_map = [
        "# 绘图函数索引",
        "",
        *[f"- Figure {figure}: `{function}`" for figure, function in MAIN_PLOT_FUNCTIONS.items()],
        *[f"- Supplementary Figure S{figure}: `{function}`" for figure, function in SUPP_PLOT_FUNCTIONS.items()],
        "",
    ]
    write_text(plotting_dir / "PLOTTING_FUNCTION_MAP.md", "\n".join(function_map))

    # Provenance and audits
    provenance_dir = PACKAGE_ROOT / "06_PROVENANCE_AND_AUDIT"
    provenance_files = [
        "MAINLINE_FILES.md",
        "README.md",
        "manuscript/submission-readiness.md",
        "docs/reproducibility-environment.md",
        "data/manifests/nature_mainline_protocol_v1.yaml",
        "data/manifests/sources.yaml",
        "data/manifests/nature_mainline_locked_id_results_v1.yaml",
        "data/manifests/nature_mainline_locked_ood_results_v1.yaml",
        "data/manifests/nature_mainline_community_profile_sensitivity_results_v1.yaml",
    ]
    for relative in provenance_files:
        copy_file(ROOT / relative, provenance_dir / relative)
    write_text(
        provenance_dir / "GIT_STATE.txt",
        f"commit: {git_commit}\n\nstatus:\n{git_status}\n",
    )
    panel_completeness = {
        "schema_version": "aidrbench.figure_panel_completeness.v1",
        "main_figures": main_summaries,
        "supplementary_figures": supp_summaries,
        "totals": {
            "figures": len(main_summaries) + len(supp_summaries),
            "panels": sum(item["panel_count"] for item in main_summaries + supp_summaries),
            "quantitative_panel_mappings": sum(
                item["quantitative_panel_count"] for item in main_summaries + supp_summaries
            ),
            "schematic_panel_mappings": sum(
                item["panel_count"] - item["quantitative_panel_count"]
                for item in main_summaries + supp_summaries
            ),
            "unique_exact_panel_csvs": len(main_panel_records)
            + len(supplementary_panel_records),
        },
    }
    json_dump(provenance_dir / "PANEL_COMPLETENESS_REPORT.json", panel_completeness)

    # Global figure/data map
    map_path = PACKAGE_ROOT / "FIGURE_DATA_MAP.csv"
    with map_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "figure",
                "table_id",
                "filename",
                "used_by_current_plot",
                "panels",
                "row_count",
                "columns",
                "output_sha256",
                "original_input_paths",
            ]
        )
        for record in main_rows:
            writer.writerow(
                [
                    record["figure"],
                    record["table_id"],
                    record["filename"],
                    record["used_by_current_plot"],
                    ";".join(record["panels"]),
                    record["row_count"],
                    ";".join(record["columns"]),
                    record["output_sha256"],
                    ";".join(item["path"] for item in record["original_inputs"]),
                ]
            )

    # Human-readable root README
    root_readme = [
        "# AIDRBench 全部图稿修改包",
        "",
        f"生成日期：{STAMP}",
        f"项目 commit：`{git_commit}`",
        "",
        "这个包把当前文稿、主图 Figure 1-6、补充图 S1-S4、每个面板最终绘制值、上游 Source Data、图注、正文上下文、绘图代码和 provenance 分开整理。陌生查看者不需要猜测筛选、聚合、坐标、颜色或统计单位。",
        "",
        "## 最重要的目录",
        "",
        "- `00_MANUSCRIPT/`：当前权威 Markdown 文稿；不包含会混淆查看者的旧版 review PDF。",
        "- `01_MAIN_FIGURES/`：每张主图独立文件夹，含逐面板 guide 和最终绘制 CSV。",
        "- `02_SUPPLEMENTARY_FIGURES/`：每张补充图独立文件夹，结构同上。",
        "- `03_PANEL_LEVEL_PLOT_DATA/`：全部定量面板最终实际绘制的数据及哈希清单。",
        "- `04_ALL_SOURCE_DATA/`：29 张主图上游 Source Data 表及补充图完整导出数据。",
        "- `05_PLOTTING_CODE_AND_SPECS/`：完整 aidrbench Python 源码、绘图规范、依赖锁和独立生成命令。",
        "- `06_PROVENANCE_AND_AUDIT/`：协议、输入来源、locked receipts 与当前 git 状态。",
        "- `06_PROVENANCE_AND_AUDIT/PANEL_COMPLETENESS_REPORT.json`：全部图和面板的数量核对结果。",
        "- `OPEN_ME.html`：用浏览器快速查看全部图和数据入口。",
        "- `FIGURE_DATA_MAP.csv`：Figure 与上游 Source Data 的总映射。",
        "- 每张图的 `PANEL_DATA_MAP.csv`：panel 与最终绘制 CSV 的一对一映射。",
        "- `FILE_INVENTORY.csv`：包内文件用途总表。",
        "",
        "## 数据目录含义",
        "",
        "- `panel_level_plot_data/` 是面板最终值；核对图上数字时优先使用。",
        "- `data_used_by_current_plot/` 是绘图函数读取的上游表，可能包含最终面板未显示的组别或时间段。",
        "- `supporting_or_scenario_level_data/` 是同一图对应的更细粒度表，适合改成分布图、散点图、箱线图或重新计算摘要。",
        "- 未打包 Alibaba/NREL 第三方原始大文件；其 URL、版本、路径和 SHA-256 均保留在 provenance manifests 中。",
        "",
        "## 当前已知版本边界",
        "",
        "- 主文稿 Markdown 已包含 Figure 6。",
        "- 旧版 review PDF 已从图稿包移除，避免与当前 Figure 1-6 混淆。",
        "- 所有当前主图和补充图均保留 SVG/PDF/TIFF/PNG，其中 SVG/PDF 最适合结构修改。",
        "",
    ]
    write_text(PACKAGE_ROOT / "README_FIRST.md", "\n".join(root_readme))

    # HTML browser index
    html_parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>AIDRBench Figure Revision Package</title>",
        "<style>body{font-family:Arial,sans-serif;max-width:1280px;margin:32px auto;padding:0 24px;color:#222}h1,h2{font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:24px}.card{border:1px solid #ddd;padding:16px;border-radius:8px}.card img{width:100%;height:auto;border:1px solid #eee}.meta{font-size:14px;line-height:1.5}a{color:#1756a9}</style>",
        "</head><body>",
        "<h1>AIDRBench Figure Revision Package</h1>",
        f"<p>Commit <code>{html.escape(git_commit)}</code>; generated {STAMP}.</p>",
        "<p><a href='START_HERE.md'>Start here</a> | <a href='README_FIRST.md'>Package details</a> | <a href='FILE_INVENTORY.csv'>File inventory</a> | <a href='FIGURE_DATA_MAP.csv'>Upstream data map</a></p>",
        "<h2>Main Figures</h2><div class='grid'>",
    ]
    for summary in main_summaries:
        figure = summary["figure"]
        folder = summary["folder"]
        manifest = json.loads((PACKAGE_ROOT / folder / "manifests" / f"figure_{figure}_manifest.json").read_text(encoding="utf-8"))
        png_name = next(output["path"] for output in manifest["outputs"] if output["format"] == "png")
        image_path = f"{folder}/artwork/{png_name}"
        html_parts.extend(
            [
                "<div class='card'>",
                f"<h3>Figure {figure}</h3>",
                f"<a href='{image_path}'><img src='{image_path}' alt='Figure {figure}'></a>",
                f"<p class='meta'>{html.escape(summary['core_conclusion'])}</p>",
                f"<p><a href='{folder}/PANEL_GUIDE.md'>panel guide</a> | <a href='{folder}/PANEL_DATA_MAP.csv'>panel-data map</a> | <a href='{folder}/FIGURE_LEGEND.md'>legend</a> | <a href='{folder}/MANUSCRIPT_CONTEXT.md'>manuscript context</a></p>",
                f"<p class='meta'>Panels: {summary['panel_count']}; quantitative panels: {summary['quantitative_panel_count']}; exact panel CSVs: {summary['unique_panel_data_files']}; upstream tables: {summary['exact_plot_tables']}; supporting tables: {summary['supporting_tables']}</p>",
                "</div>",
            ]
        )
    html_parts.append("</div><h2>Supplementary Figures</h2><div class='grid'>")
    for summary in supp_summaries:
        figure_label = summary["figure"]
        figure_number = int(figure_label[1:])
        folder = summary["folder"]
        image_path = f"{folder}/artwork/supplementary_figure_{figure_number}.png"
        html_parts.extend(
            [
                "<div class='card'>",
                f"<h3>Supplementary Figure {figure_label}</h3>",
                f"<a href='{image_path}'><img src='{image_path}' alt='Supplementary Figure {figure_label}'></a>",
                f"<p class='meta'>{html.escape(summary['core_conclusion'])}</p>",
                f"<p><a href='{folder}/PANEL_GUIDE.md'>panel guide</a> | <a href='{folder}/PANEL_DATA_MAP.csv'>panel-data map</a> | <a href='{folder}/FIGURE_LEGEND.md'>legend</a></p>",
                f"<p class='meta'>Panels: {summary['panel_count']}; quantitative panels: {summary['quantitative_panel_count']}; exact panel CSVs: {summary['unique_panel_data_files']}</p>",
                "</div>",
            ]
        )
    html_parts.append("</div></body></html>")
    write_text(PACKAGE_ROOT / "OPEN_ME.html", "".join(html_parts))

    write_text(
        PACKAGE_ROOT / "START_HERE.md",
        """# Start here

This package is arranged for a reader who has not seen the manuscript or plotting code.

1. Open `OPEN_ME.html` and choose a figure.
2. Open that figure's `PANEL_GUIDE.md` to learn the question, axes, colour/marker meaning, sample/statistic, interpretation and claim boundary for every panel.
3. Open the matching file under `panel_level_plot_data/`; it contains the exact post-filter or post-aggregation values drawn in that panel.
4. Use `data_used_by_current_plot/` only when you need the fuller upstream table, and `supporting_or_scenario_level_data/` for scenario-level redesign.
5. Run `python VERIFY_PACKAGE.py` from the package root to verify every checksum and every quantitative panel-data link.
6. To regenerate all artwork from the extracted package, run `bash 05_PLOTTING_CODE_AND_SPECS/REGENERATE_COMMANDS.sh`; this uses the bundled source tree, inputs and locked dependencies.

Conceptual panels are explicitly labelled `NO_NUMERIC_DATA` in each `PANEL_DATA_MAP.csv`. No old review PDF is included.
""",
    )
    write_text(
        PACKAGE_ROOT / "VERIFY_PACKAGE.py",
        """from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


errors: list[str] = []
checksum_count = 0
for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    path = ROOT / relative
    checksum_count += 1
    if not path.is_file():
        errors.append(f"missing checksum member: {relative}")
    elif sha256(path) != expected:
        errors.append(f"checksum mismatch: {relative}")

quantitative_panels = 0
schematic_panels = 0
for map_path in sorted(ROOT.glob("0[12]_*FIGURES/**/PANEL_DATA_MAP.csv")):
    with map_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            output = row["plot_data_file"]
            if output == "NO_NUMERIC_DATA":
                schematic_panels += 1
                continue
            quantitative_panels += 1
            panel_path = map_path.parent / "panel_level_plot_data" / output
            if not panel_path.is_file():
                errors.append(f"missing panel plot data: {panel_path.relative_to(ROOT)}")
            elif sha256(panel_path) != row["sha256"]:
                errors.append(f"panel-data mismatch: {panel_path.relative_to(ROOT)}")

if errors:
    raise SystemExit("\\n".join(errors))
print(
    f"PASS: {checksum_count} checksums; "
    f"{quantitative_panels} quantitative panel mappings; "
    f"{schematic_panels} schematic panel mappings"
)
""",
    )

    inventory_path = PACKAGE_ROOT / "FILE_INVENTORY.csv"
    inventory_members = sorted(path for path in PACKAGE_ROOT.rglob("*") if path.is_file())
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "bytes", "sha256", "role"])
        for path in inventory_members:
            relative = path.relative_to(PACKAGE_ROOT)
            writer.writerow(
                [relative.as_posix(), path.stat().st_size, sha256(path), inventory_role(relative)]
            )
        writer.writerow(
            ["FILE_INVENTORY.csv", "self", "see SHA256SUMS.txt", inventory_role(Path("FILE_INVENTORY.csv"))]
        )
        writer.writerow(
            ["SHA256SUMS.txt", "generated last", "not self-listed", inventory_role(Path("SHA256SUMS.txt"))]
        )

    # Hash every package member before zipping.
    package_files = sorted(path for path in PACKAGE_ROOT.rglob("*") if path.is_file())
    checksum_lines = [f"{sha256(path)}  {relative_posix(path)}" for path in package_files]
    write_text(PACKAGE_ROOT / "SHA256SUMS.txt", "\n".join(checksum_lines) + "\n")

    # Zip with a single top-level folder.
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACKAGE_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=f"{PACKAGE_NAME}/{path.relative_to(PACKAGE_ROOT).as_posix()}")

    summary = {
        "package_name": PACKAGE_NAME,
        "package_directory": str(PACKAGE_ROOT),
        "zip_path": str(ZIP_PATH),
        "zip_sha256": sha256(ZIP_PATH),
        "zip_bytes": ZIP_PATH.stat().st_size,
        "git_commit": git_commit,
        "git_status": git_status,
        "main_figures": main_summaries,
        "supplementary_figures": supp_summaries,
        "main_source_data_tables": len(source_manifest["tables"]),
        "package_file_count": sum(1 for path in PACKAGE_ROOT.rglob("*") if path.is_file()),
    }
    json_dump(SUMMARY_PATH, summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
