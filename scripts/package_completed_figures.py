"""Merge the accepted web figures into the prior all-figure package without redrawing."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "results/exports/AIDRBench_Figure_Revision_Package_2026-09-02.zip"
RETURN = ROOT / "results/web_gpt_return/2026-09-06_original/AIDRBench_Figures_6_S5"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError("Use a new versioned package name.")
    files: dict[str, bytes] = {}
    preserved = []
    catalog = []
    active_artwork: dict[str, str] = {}
    replacements = {
        "panel_level_plot_data": "panel_data",
        "data_used_by_current_plot": "data",
        "supporting_or_scenario_level_data": "supporting_data",
        "configuration_and_provenance_inputs": "inputs",
        "05_PLOTTING_CODE_AND_SPECS": "05_code",
        "04_ALL_SOURCE_DATA": "04_source",
    }

    def add(path: str, data: bytes | str) -> None:
        files[path] = data.encode("utf-8") if isinstance(data, str) else data

    def add_local(source: Path, target: str) -> None:
        add(target, source.read_bytes())

    def write_json(path: str, data: object) -> None:
        add(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def write_csv(path: str, rows: list[dict[str, object]]) -> None:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        add(path, stream.getvalue())

    # Keep old scientific bytes and rendering implementations; only shorten containers.
    with zipfile.ZipFile(PREVIOUS) as archive:
        directories = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative = info.filename.split("/", 1)[1]
            parts = relative.split("/")
            destination = None
            if parts[0] in {"01_MAIN_FIGURES", "02_SUPPLEMENTARY_FIGURES"}:
                supplementary = parts[0].startswith("02")
                match = re.match(r"Supplementary_Figure_S(\d+)_|Figure_(\d+)_", parts[1])
                assert match is not None
                number = int(match.group(1) or match.group(2))
                if not supplementary and number == 6:
                    continue  # Previous community artwork is retained only in the historical ZIP.
                folder = f"02_supp/S{number:02}" if supplementary else f"01_main/F{number:02}"
                figure = f"S{number}" if supplementary else str(number)
                directories[figure] = folder
                tail = "/".join(parts[2:])
                for old, new in replacements.items():
                    tail = tail.replace(old, new)
                destination = f"{folder}/{tail}"
            elif parts[0] in {"04_ALL_SOURCE_DATA", "05_PLOTTING_CODE_AND_SPECS"}:
                destination = relative.replace(parts[0], replacements[parts[0]], 1)
            elif parts[0] == "06_PROVENANCE_AND_AUDIT":
                destination = "06_audit/previous/" + "/".join(parts[1:])
            if destination is None:
                continue
            data = archive.read(info)
            if destination.endswith(".md") and not destination.startswith(
                ("05_code/", "06_audit/")
            ):
                text = data.decode("utf-8")
                for old, new in replacements.items():
                    text = text.replace(old, new)
                data = text.encode("utf-8")
            add(destination, data)
            if "/artwork/" in destination or destination.endswith(".csv"):
                preserved.append(
                    {
                        "old_member": info.filename,
                        "new_file": destination,
                        "sha256": digest(data),
                        "byte_identical": data == archive.read(info),
                    }
                )
            if "/artwork/" in destination:
                active_artwork[Path(destination).name] = destination
        for figure, folder in directories.items():
            png = next(
                name
                for name in files
                if name.startswith(folder + "/artwork/") and name.endswith(".png")
            )
            catalog.append(
                {
                    "figure": figure,
                    "directory": folder,
                    "preview": png,
                    "origin": "previous_package_unchanged_artwork_and_data",
                }
            )

    command = files["05_code/REGENERATE_COMMANDS.sh"].decode("utf-8")
    command = command.replace("../04_ALL_SOURCE_DATA/", "../04_source/")
    command = command.replace("--figures 1 2 3 4 5 6", "--figures 1 2 3 4 5")
    add("05_code/REGENERATE_COMMANDS.sh", command)
    old_function_map = files["05_code/PLOTTING_FUNCTION_MAP.md"].decode("utf-8")
    add("06_audit/previous/PLOTTING_FUNCTION_MAP.md", old_function_map)
    current_function_map = "\n".join(
        line
        for line in old_function_map.splitlines()
        if not re.match(r"\s*(?:[-|]\s*)?(?:Figure|图)\s*6\b", line)
    )
    current_function_map += (
        "\n\n## 当前新增两图\n\n"
        "- Figure 6（经济参与）："
        "`../05_web/code/plot_figures.py::plot_figure6`。\n"
        "- Supplementary Figure S5（社区原型）："
        "`../05_web/code/plot_figures.py::plot_figure_s5`。\n"
        "- 两图当前本地修改入口：`../RUN_NEW_FIGURES.py`。\n\n"
        "历史函数 `plot_nature_mainline_figure6_reference_style` 仅对应旧社区图，"
        "不再是当前 Figure 6，也不用于产生当前 S5 原件。"
        "原函数索引保留于 `../06_audit/previous/PLOTTING_FUNCTION_MAP.md`。\n"
    )
    add("05_code/PLOTTING_FUNCTION_MAP.md", current_function_map)
    add(
        "05_code/READ_FIRST_CURRENT_SCOPE.md",
        "# 既有九图代码\n\n本目录保留此前交付的源代码和依赖锁。"
        "`REGENERATE_COMMANDS.sh` 已更新数据目录并只选择主图 1–5、S1–S4。"
        "其中 S4 的历史脚本会自动重放包内冻结示例；直接改绘无需重放，"
        "可用 S04/panel_data 的完整 40 行终值。"
        "当前经济图 6 与 S5 使用根目录 RUN_NEW_FIGURES.py，"
        "旧源码中曾名为主图 6 的社区图不再作为当前成图输出。\n",
    )

    # Accepted web bytes and their full, directly usable data/code.
    acceptance = json.loads((ROOT / "docs/figures/web_gpt_v1/acceptance_manifest.json").read_text())
    if acceptance["status"] != "accepted_web_return" or len(acceptance["reviews"]) != 3:
        raise ValueError("Web figures have not passed three reviews")
    f6_tables = [
        "fig6_fixed_site_overlay_scale_sensitivity.csv",
        "fig6_mechanism_sensitivity.csv",
        "fig6_break_even_decomposition.csv",
        "fig6_duration_break_even.csv",
    ]
    for figure, folder, key, stem, tables in [
        ("6", "01_main/F06", "figure6", "AIDRBench_Figure_6", f6_tables),
        (
            "S5",
            "02_supp/S05",
            "figure_s5",
            "AIDRBench_Figure_S5",
            [f"figure_s5_panel_{p}.csv" for p in "abcd"],
        ),
    ]:
        for extension in ("svg", "pdf", "png", "tiff"):
            name = f"{stem}.{extension}"
            data = (RETURN / "figures" / name).read_bytes()
            if digest(data) != acceptance["output_sha256"][name]:
                raise ValueError(f"Accepted artwork changed: {name}")
            add(f"{folder}/artwork/{name}", data)
            active_artwork[name] = f"{folder}/artwork/{name}"
        rows = []
        for panel, name in zip("abcd", tables, strict=True):
            data = (RETURN / f"inputs/{key}/source_data/{name}").read_bytes()
            add(f"{folder}/panel_data/{name}", data)
            parsed = list(csv.reader(io.StringIO(data.decode("utf-8"))))
            rows.append(
                {
                    "figure": figure,
                    "panel": panel,
                    "plot_data_file": name,
                    "row_count": len(parsed) - 1,
                    "columns": ";".join(parsed[0]),
                    "sha256": digest(data),
                }
            )
        write_csv(f"{folder}/PANEL_DATA_MAP.csv", rows)
        add_local(RETURN / f"inputs/{key}/README_FIRST_FOR_WEB_GPT.md", f"{folder}/PANEL_GUIDE.md")
        add(
            f"{folder}/README.md",
            f"# Figure {figure}\n\n`artwork/` 是用户确认由网页版 GPT-6 生成并通过三方验收的原件。"
            "`panel_data/` 已是各面板的完整绘图值，无需筛选、聚合或重跑实验。"
            "`PANEL_DATA_MAP.csv` 对应 a–d。\n\n修改 `../../05_web/code/plot_figures.py` 后，"
            "从包根目录运行 `python RUN_NEW_FIGURES.py`，"
            "会自动创建环境并将两图导出至新的 redrawn 子目录。"
            "仅需已有 Python 3.12/3.13，首次安装依赖需要联网。"
            "此后的本地重绘记录为本地来源，不覆盖当前网页原图。\n\n"
            "当前论文图注在 `FIGURE_LEGEND.md`；PANEL_GUIDE 内 `source_data/` 路径以 "
            f"`../../05_web/inputs/{key}/` 为根。"
            "原上传包图注保留于历史 ZIP，不应替换当前论文图注。\n",
        )
        catalog.append(
            {
                "figure": figure,
                "directory": folder,
                "preview": f"{folder}/artwork/{stem}.png",
                "origin": "accepted_web_GPT6_user_confirmed",
            }
        )
    for path in sorted(RETURN.rglob("*")):
        if path.is_file():
            relative = path.relative_to(RETURN).as_posix()
            if (
                relative.startswith(("code/", "inputs/", "original_packages/"))
                or relative == "requirements.txt"
            ):
                add_local(path, "05_web/" + relative)
            elif relative.startswith("audit/"):
                add_local(path, "06_audit/web_return/" + relative.removeprefix("audit/"))
    add(
        "05_web/README.md",
        "# 新增图件的可修改源代码\n\n请从包根目录运行 RUN_NEW_FIGURES.py，"
        "修改 code/plot_figures.py 调整图形。入口在新的输出目录重绘并准确记录本地来源。"
        "原始 code/run_all.py 是网页当次运行的代码，不建议直接在此目录执行；"
        "code/package_delivery.py 仅保留原始生成溯源，"
        "其历史正文与网页环境标签不是当前本地打包流程。\n",
    )
    for directory in ("nature_economic_v1", "nature_economic_robustness_v1"):
        for path in sorted((ROOT / "manuscript/source_data" / directory).iterdir()):
            if path.is_file():
                add_local(path, f"04_source/{directory}/{path.name}")

    catalog.sort(key=lambda x: (x["figure"].startswith("S"), int(x["figure"].lstrip("S"))))
    for source in ("nature_communications_article.md", "supplementary_information.md"):
        text = (ROOT / "manuscript" / source).read_text(encoding="utf-8")
        for name, destination in active_artwork.items():
            text = re.sub(
                r"(?<=\()\.\./docs/figures/[^)]+/" + re.escape(name) + r"(?=\))",
                "../" + destination,
                text,
            )
        add("00_manuscript/" + source, text)
    # Per-figure context excerpts also embed their own artwork. Relocate these links.
    for name in list(files):
        if name.startswith(("01_main/", "02_supp/")) and name.endswith(".md"):
            text = files[name].decode("utf-8")
            for artwork_name, destination in active_artwork.items():
                if destination.startswith(str(Path(name).parent) + "/artwork/"):
                    text = re.sub(
                        r"(?<=\()\.\./docs/figures/[^)]+/" + re.escape(artwork_name) + r"(?=\))",
                        "artwork/" + artwork_name,
                        text,
                    )
            add(name, text)
    main = (ROOT / "manuscript/nature_communications_article.md").read_text()
    supplementary = (ROOT / "manuscript/supplementary_information.md").read_text()
    for figure in catalog:
        number = int(figure["figure"].lstrip("S"))
        if figure["figure"].startswith("S"):
            match = re.search(
                rf"^### Supplementary Figure {number}[^\n]*\n(.*?)(?=^### |^## |\Z)",
                supplementary,
                re.M | re.S,
            )
            assert match is not None
            caption = re.sub(r"!\[[^]]*\]\([^)]*\)", "", match.group(1)).strip()
        else:
            match = re.search(
                rf"^### Figure {number}[^\n]*\n(.*?)(?=^### |^## |\Z)", main, re.M | re.S
            )
            assert match is not None
            caption = match.group(0).strip()
        add(figure["directory"] + "/FIGURE_LEGEND.md", caption + "\n")
    for name in (
        "AIDRBench_Nature_Communications_v0.7_web_figure_review.pdf",
        "AIDRBench_Nature_Communications_v0.6_Supplementary_Information_web_figure_review.pdf",
    ):
        add_local(ROOT / "manuscript/exports" / name, "00_manuscript/" + name)
    add_local(PREVIOUS, "07_original/previous_all_figures.zip")
    add_local(
        RETURN.parent / "AIDRBench_Figures_6_S5_Complete.zip", "07_original/web_figures_6_S5.zip"
    )
    for path in sorted((ROOT / "docs/web_gpt_return_review").glob("v1*")):
        if path.is_file():
            add_local(path, "06_audit/acceptance/" + path.name)
    for name in ("user_provenance_confirmation.md",):
        add_local(ROOT / "docs/web_gpt_return_review" / name, "06_audit/acceptance/" + name)
    add_local(
        ROOT / "docs/figures/web_gpt_v1/acceptance_manifest.json",
        "06_audit/acceptance/acceptance_manifest.json",
    )
    confirmation_file = "06_audit/acceptance/user_provenance_confirmation.md"
    portable_evidence = {
        "schema": "aidrbench.portable_acceptance_paths.v1",
        "path_base": "package_root",
        "original_acceptance_manifest": "06_audit/acceptance/acceptance_manifest.json",
        "model_confirmation": {
            "original_workspace_path": acceptance["user_confirmation_file"],
            "file": confirmation_file,
            "sha256": digest(files[confirmation_file]),
        },
        "reviews": [
            {
                "emphasis": review["emphasis"],
                "original_workspace_path": review["report"],
                "file": "06_audit/acceptance/" + Path(review["report"]).name,
                "sha256": review["sha256"],
            }
            for review in acceptance["reviews"]
        ],
        "artwork": [
            {"file": active_artwork[name], "sha256": expected}
            for name, expected in acceptance["output_sha256"].items()
        ],
        "returned_archive": {
            "file": "07_original/web_figures_6_S5.zip",
            "sha256": acceptance["received_archive_sha256"],
        },
    }
    write_json("06_audit/acceptance/package_paths.json", portable_evidence)
    for name in ("RUN_NEW_FIGURES.py", "VERIFY_PACKAGE.py", "README_FIRST.md"):
        add_local(ROOT / "docs/all_figure_handoff" / name, name)
    add(
        "RUN_NEW_FIGURES_WINDOWS.bat",
        '@echo off\r\ncd /d "%~dp0"\r\npython RUN_NEW_FIGURES.py\r\nif errorlevel 1 pause\r\n',
    )
    add(
        "RUN_NEW_FIGURES_MAC.command",
        '#!/bin/sh\ncd "$(dirname "$0")" || exit 1\npython3 RUN_NEW_FIGURES.py\n',
    )
    write_json("FIGURE_CATALOG.json", catalog)
    write_json("06_audit/PRESERVED_PREVIOUS_FILES.json", preserved)
    inventory = []
    for item in catalog:
        stream = io.StringIO(files[item["directory"] + "/PANEL_DATA_MAP.csv"].decode("utf-8"))
        for row in csv.DictReader(stream):
            inventory.append(
                {
                    "figure": item["figure"],
                    "panel": row["panel"],
                    "plot_data_file": row["plot_data_file"],
                    "directory": item["directory"],
                    "row_count": row.get("row_count", ""),
                    "sha256": row["sha256"],
                }
            )
    write_csv("ALL_PANEL_DATA_MAP.csv", inventory)
    cards = []
    for item in catalog:
        folder = html.escape(item["directory"])
        preview = html.escape(item["preview"])
        data_links = (
            " · ".join(
                f'<a href="{html.escape(path)}">{html.escape(Path(path).name)}</a>'
                for path in files
                if path.startswith(item["directory"] + "/panel_data/") and path.endswith(".csv")
            )
            or "示意面板，不含数值数据"
        )
        code = (
            "05_web/code/plot_figures.py"
            if item["figure"] in {"6", "S5"}
            else "05_code/src/aidrbench/evaluation/"
            + (
                "supplementary_figures.py"
                if item["figure"].startswith("S")
                else "nature_figures.py"
            )
        )
        links = " · ".join(
            f'<a href="{html.escape(path)}">{extension.upper()}</a>'
            for extension in ("svg", "pdf", "png", "tiff")
            for path in files
            if path.startswith(item["directory"] + "/artwork/") and path.endswith("." + extension)
        )
        cards.append(
            f'<article><h2>Figure {item["figure"]}</h2><a href="{preview}">'
            f'<img src="{preview}" alt="Figure {item["figure"]}"></a><p>{links}</p><p>'
            f'<a href="{folder}/PANEL_GUIDE.md">面板说明</a> · '
            f'<a href="{folder}/PANEL_DATA_MAP.csv">数据映射</a> · '
            f'<a href="{folder}/FIGURE_LEGEND.md">当前图注</a> · '
            f'<a href="{code}">绘图代码</a></p><p>直接绘图 CSV：{data_links}</p></article>'
        )
    add(
        "OPEN_ME.html",
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        "<title>AIDRBench 全部 11 图</title><style>"
        "body{font:16px sans-serif;max-width:1150px;margin:35px auto;color:#24313d}"
        "main{display:grid;grid-template-columns:1fr 1fr;gap:30px}"
        "article{border-top:1px solid #ccd4da;padding:15px}"
        "img{max-width:100%;max-height:480px}a{color:#245f7a}</style>"
        "<h1>AIDRBench 全部 11 图</h1><p>主图 1–5、S1–S4 沿用原包；"
        "主图 6 与 S5 为本次已验收的网页版 GPT-6 原件。"
        "每图均含完整绘图值、可编辑图件与当前图注。</p><p>"
        '<a href="README_FIRST.md">使用说明</a> · '
        '<a href="ALL_PANEL_DATA_MAP.csv">全部面板数据</a> · '
        '<a href="00_manuscript/nature_communications_article.md">当前主文</a> · '
        '<a href="00_manuscript/supplementary_information.md">当前 SI</a></p><main>'
        + "".join(cards)
        + "</main></html>",
    )
    write_json(
        "PACKAGE_SCOPE.json",
        {
            "schema": "aidrbench.completed_figure_merge.v1",
            "figures": 11,
            "old_artwork_redrawn": False,
            "web_artwork_changed": False,
            "source_previous_zip_sha256": digest(PREVIOUS.read_bytes()),
            "source_web_zip_sha256": acceptance["received_archive_sha256"],
            "model_evidence": "user_confirmation",
            "authors_and_license": "deferred_by_user",
            "builder_sha256": digest(Path(__file__).read_bytes()),
        },
    )
    checksums = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(files.items()))
    add("SHA256SUMS.txt", checksums)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".figure-merge-", dir=output.parent) as temporary:
        path = Path(temporary) / "candidate.zip"
        with zipfile.ZipFile(
            path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(
                    "AIDRBench_All_Figures/" + name, date_time=(2026, 9, 6, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (
                    0o100755 if name.endswith((".sh", ".command")) else 0o100644
                ) << 16
                archive.writestr(info, data)
        path.rename(output)
    return {
        "path": str(output),
        "sha256": digest(output.read_bytes()),
        "files": len(files),
        "bytes": output.stat().st_size,
        "active_figures": len(catalog),
        "panel_mappings": len(inventory),
        "previous_preserved_files": len(preserved),
        "all_preserved_bytes_match": all(x["byte_identical"] for x in preserved),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
