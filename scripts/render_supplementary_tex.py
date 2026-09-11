"""Render the current Markdown as a preliminary content-review TeX file.

Run from any directory; compile the resulting file with XeLaTeX or Tectonic.
Accepted web artwork is inserted unchanged. Author metadata remains pending.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from review_figure_inputs import validated_review_pdf
from web_figure_inputs import validated_web_pdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript/supplementary_information.md"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--local-figures", type=Path, help="explicitly insert hashed LOCAL REVIEW DRAFT PDFs"
)
parser.add_argument("--web-figures", type=Path, help="insert accepted, hash-verified web artwork")
parser.add_argument(
    "--current-figures", type=Path, help="insert five current data-driven supplementary PDFs"
)
args = parser.parse_args()
if args.current_figures is None and args.local_figures is None and args.web_figures is None:
    if "docs/figures/commitment_narrative_v1/artwork/" in SOURCE.read_text():
        args.current_figures = ROOT / "docs/figures/commitment_narrative_v1/artwork"
    elif "docs/figures/commitment_mechanisms_v1/artwork/" in SOURCE.read_text():
        args.current_figures = ROOT / "docs/figures/commitment_mechanisms_v1/artwork"
    elif "docs/figures/operating_tradeoffs_v1/artwork/" in SOURCE.read_text():
        args.current_figures = ROOT / "docs/figures/operating_tradeoffs_v1/artwork"
    elif "docs/figures/repeat_mechanism_v1/artwork/" in SOURCE.read_text():
        args.current_figures = ROOT / "docs/figures/repeat_mechanism_v1/artwork"
    elif "docs/figures/workload_composition_v1/artwork/" in SOURCE.read_text():
        args.current_figures = ROOT / "docs/figures/workload_composition_v1/artwork"
if args.local_figures is not None and args.web_figures is not None:
    parser.error("choose local drafts or accepted web figures")
LOCAL = args.local_figures is not None
CURRENT = args.current_figures is not None
WEB_DIRECTORY = args.web_figures or ROOT / "docs/figures/web_gpt_v1"
WEB = not LOCAL and not CURRENT and (WEB_DIRECTORY / "acceptance_manifest.json").is_file()
if args.web_figures is not None and not WEB:
    parser.error("accepted web-figure manifest is missing")
preview_pdf = (
    validated_review_pdf(args.local_figures, "s5", ROOT)
    if LOCAL
    else validated_web_pdf(WEB_DIRECTORY, "s5", ROOT)
    if WEB
    else None
)
variant = (
    "content_revision" if WEB or CURRENT else "local_figure_review" if LOCAL else "content_review"
)
VERSION = re.search(r"version (\d+\.\d+)", SOURCE.read_text())[1]
OUTPUT = (
    ROOT
    / "manuscript/exports"
    / f"AIDRBench_Nature_Communications_v{VERSION}_Supplementary_Information_{variant}.tex"
)
review_status = (
    f"Local figure review v{VERSION}; drafts only"
    if LOCAL
    else f"Content review v{VERSION}; artwork pending"
)
review_notice = (
    "Local S5 draft included for review only; formal Web-GPT artwork and release metadata pending."
    if LOCAL
    else "Content review only: Supplementary Figure S5 artwork and release metadata pending."
)

if WEB:
    review_status = f"Revised Supplementary Information v{VERSION}"
    review_notice = "Content revised; five existing supplementary figures retained pending redraw."

if CURRENT:
    review_status = f"Revised Supplementary Information v{VERSION}"
    review_notice = (
        "Current methods, supporting tables and five supplementary figures. "
        "Author metadata pending."
    )
    current_manifest = json.loads(
        (args.current_figures / "supplement_source_manifest.json").read_text()
    )
    for n in range(1, 6):
        path = args.current_figures / f"AIDRBench_Supplementary_Figure_{n}.pdf"
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != current_manifest["outputs"][path.name]["sha256"]
        ):
            raise ValueError(f"Current supplementary figure {n} differs from its receipt")


def escape_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def render_code(value: str) -> str:
    if len(value) > 32 and re.fullmatch(r"[0-9A-Za-z.-]+", value):
        chunks = [value[index : index + 4] for index in range(0, len(value), 4)]
        return r"\texttt{" + r"\allowbreak{}".join(chunks) + "}"
    return r"\nolinkurl{" + value.replace("%", r"\%") + "}"


def inline_latex(value: str) -> str:
    protected: dict[str, str] = {}

    def keep(rendered: str) -> str:
        token = f"PROTECTEDTOKEN{len(protected):04d}X"
        protected[token] = rendered
        return token

    value = value.replace("⁻¹", keep(r"\textsuperscript{−1}"))
    value = value.replace("⁻", keep(r"\textsuperscript{-}"))
    value = re.sub(r"\\\((.*?)\\\)", lambda match: keep(r"\(" + match.group(1) + r"\)"), value)
    value = re.sub(
        r"<sup>(.*?)</sup>",
        lambda match: keep(r"\textsuperscript{" + escape_text(match.group(1)) + "}"),
        value,
    )
    value = re.sub(r"`([^`]+)`", lambda match: keep(render_code(match.group(1))), value)

    def markdown_link(match: re.Match[str]) -> str:
        label = inline_latex(match.group(1))
        url = match.group(2).replace("%", r"\%")
        return keep(r"\href{" + url + "}{" + label + "}")

    value = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", markdown_link, value)

    def plain_url(match: re.Match[str]) -> str:
        url = match.group(0)
        trailing = ""
        while url and url[-1] in ".,;":
            trailing = url[-1] + trailing
            url = url[:-1]
        return keep(r"\url{" + url.replace("%", r"\%") + "}") + trailing

    value = re.sub(r"https?://[^\s]+", plain_url, value)
    value = re.sub(
        r"\*\*([^*]+)\*\*",
        lambda match: keep(r"\textbf{" + inline_latex(match.group(1)) + "}"),
        value,
    )
    value = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        lambda match: keep(r"\emph{" + inline_latex(match.group(1)) + "}"),
        value,
    )
    value = escape_text(value)
    for token, rendered in protected.items():
        value = value.replace(token, rendered)
    return value


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_widths(rows: list[list[str]]) -> list[float]:
    column_count = len(rows[0])
    maxima = []
    for column in range(column_count):
        maximum = max(len(re.sub(r"[*`]", "", row[column])) for row in rows if column < len(row))
        maxima.append(max(4.0, min(11.0, math.sqrt(maximum))))
    available = {2: 0.95, 3: 0.93, 4: 0.91, 5: 0.89, 7: 0.83, 8: 0.80, 10: 0.75}.get(
        column_count, 0.86
    )
    total = sum(maxima)
    return [available * value / total for value in maxima]


def render_table(rows: list[list[str]]) -> str:
    header = rows[0]
    body = rows[1:]
    widths = table_widths(rows)
    column_spec = (
        "@{}"
        + "".join(
            rf">{{\RaggedRight\arraybackslash}}p{{{width:.3f}\textwidth}}" for width in widths
        )
        + "@{}"
    )
    header_line = " & ".join(r"\textbf{" + inline_latex(cell) + "}" for cell in header) + r" \\"
    if header[0] == "Ledger term":
        # Keep the compact reference-input table together for direct comparison.
        table_body = "\n".join(
            " & ".join(inline_latex(cell) for cell in row) + r" \\" for row in body
        )
        return (
            "\\par\\medskip\\noindent\\begin{minipage}{\\textwidth}\\footnotesize\n"
            "\\renewcommand{\\arraystretch}{1.12}\n"
            f"\\begin{{tabular}}{{{column_spec}}}\n\\toprule\n"
            + header_line
            + "\n\\midrule\n"
            + table_body
            + "\n\\bottomrule\n\\end{tabular}\n\\end{minipage}\\par\\medskip\n"
        )
    rendered = [
        "{\\footnotesize\n",
        # Keep the short interaction table together without reducing text size.
        "\\renewcommand{\\arraystretch}{1.00}\n"
        if header[0] == "Work range"
        else "\\renewcommand{\\arraystretch}{1.12}\n",
        f"\\begin{{longtable}}{{{column_spec}}}\n",
        "\\toprule\n",
        header_line + "\n",
        "\\midrule\n",
        "\\endfirsthead\n",
        "\\toprule\n",
        header_line + "\n",
        "\\midrule\n",
        "\\endhead\n",
        rf"\midrule \multicolumn{{{len(header)}}}{{r}}{{\scriptsize continued on next page}} \\"
        + "\n",
        "\\endfoot\n",
        "\\bottomrule\n",
        "\\endlastfoot\n",
    ]
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        rendered.append(
            " & ".join(inline_latex(cell) for cell in padded[: len(header)]) + r" \\" + "\n"
        )
    rendered.extend(["\\end{longtable}\n", "}\n"])
    return "".join(rendered)


markdown = SOURCE.read_text(encoding="utf-8")
markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
lines = markdown.splitlines()

paper_title = next(line[3:].strip() for line in lines if line.startswith("## "))

preamble = rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[a4paper,top=18mm,bottom=19mm,left=18mm,right=18mm,headheight=13.6pt]{{geometry}}
\usepackage{{fontspec}}
\IfFontExistsTF{{TeX Gyre Termes}}
  {{\setmainfont{{TeX Gyre Termes}}}}
  {{\IfFontExistsTF{{Liberation Serif}}{{\setmainfont{{Liberation Serif}}}}{{}}}}
\IfFontExistsTF{{TeX Gyre Heros}}
  {{\setsansfont{{TeX Gyre Heros}}}}
  {{\IfFontExistsTF{{Liberation Sans}}{{\setsansfont{{Liberation Sans}}}}{{}}}}
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\usepackage[table]{{xcolor}}
\usepackage{{booktabs,longtable,array,ragged2e}}
\usepackage{{hyperref}}
\usepackage{{bookmark}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fancyhdr}}
\usepackage{{microtype}}
\usepackage{{float}}
\usepackage[font=small,labelfont=bf]{{caption}}
\definecolor{{AIDRBlue}}{{HTML}}{{18364A}}
\definecolor{{AIDRLink}}{{HTML}}{{245F7A}}
\definecolor{{AIDRRule}}{{HTML}}{{AAB7C0}}
\hypersetup{{colorlinks=true,linkcolor=AIDRLink,urlcolor=AIDRLink,citecolor=AIDRLink,
pdfauthor={{AIDRBench authors}},
pdftitle={{Supplementary Information: {inline_latex(paper_title)}}}}}
\urlstyle{{same}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{5pt plus 1pt minus 0.5pt}}
\setlength{{\emergencystretch}}{{3em}}
\setcounter{{secnumdepth}}{{0}}
\setcounter{{tocdepth}}{{2}}
\setlist[itemize]{{leftmargin=*,itemsep=2pt,topsep=3pt}}
\titleformat{{\section}}{{\Large\sffamily\bfseries\color{{AIDRBlue}}}}{{\thesection}}{{0.65em}}{{\phantomsection}}
\titleformat{{\subsection}}{{\large\sffamily\bfseries\color{{AIDRBlue}}}}{{\thesubsection}}{{0.55em}}{{\phantomsection}}
\titlespacing*{{\section}}{{0pt}}{{17pt}}{{6pt}}
\titlespacing*{{\subsection}}{{0pt}}{{13pt}}{{4pt}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[L]{{\small\sffamily AIDRBench Supplementary Information}}
\fancyhead[R]{{\small\sffamily {review_status}}}
\fancyfoot[C]{{\small\thepage}}
\renewcommand{{\thepage}}{{S\arabic{{page}}}}
\makeatletter
\setlength{{\@fptop}}{{0pt}}
\setlength{{\@fpsep}}{{12pt}}
\setlength{{\@fpbot}}{{0pt plus 1fil}}
\makeatother
\renewcommand{{\topfraction}}{{0.95}}
\renewcommand{{\bottomfraction}}{{0.95}}
\renewcommand{{\textfraction}}{{0.05}}
\renewcommand{{\floatpagefraction}}{{0.80}}
\title{{\sffamily\bfseries Supplementary Information\\[0.8em]\Large {inline_latex(paper_title)}}}
\author{{\sffamily [AUTHOR NAMES]}}
\date{{Working Supplementary Information v{VERSION}}}
\begin{{document}}
\maketitle
\thispagestyle{{fancy}}
\begin{{center}}\small\bfseries
{review_notice}
\end{{center}}
\clearpage
{{\small\setlength{{\parskip}}{{0pt}}\tableofcontents}}
\clearpage
"""

output: list[str] = [preamble]
in_body = False
in_math = False
math_lines: list[str] = []
in_itemize = False
pending_image: tuple[str, str] | None = None
current_section = ""
figure_index = 0


def close_itemize() -> None:
    global in_itemize
    if in_itemize:
        output.append("\\end{itemize}\n")
        in_itemize = False


def flush_image(caption: str | None = None) -> None:
    global pending_image
    if pending_image is None:
        return
    alt, path = pending_image
    output.append("\\begin{figure}[H]\n\\centering\n")
    if CURRENT or (WEB and preview_pdf is not None and path.endswith(preview_pdf.name)):
        output.append(
            f"\\makebox[\\textwidth][c]{{\\includegraphics[width=183mm]{{\\detokenize{{{path}}}}}}}\n"
        )
    else:
        output.append(
            f"\\includegraphics[width=\\textwidth,height=0.68\\textheight,keepaspectratio]{{\\detokenize{{{path}}}}}\n"
        )
    if caption:
        output.append("\\caption*{" + inline_latex(caption) + "}\n")
    elif alt:
        output.append("\\caption*{" + inline_latex(alt) + "}\n")
    output.append("\\end{figure}\n")
    pending_image = None


index = 0
while index < len(lines):
    line = lines[index]
    stripped = line.strip()

    if stripped in {"## Reader guide", "## Supplementary Notes", "## Supplementary Methods"}:
        in_body = True
    if not in_body:
        index += 1
        continue

    if stripped == r"\[":
        in_math = True
        math_lines = []
        index += 1
        continue
    if stripped == r"\]" and in_math:
        output.append("\\begin{equation*}\n" + "\n".join(math_lines) + "\n\\end{equation*}\n")
        in_math = False
        math_lines = []
        index += 1
        continue
    if in_math:
        math_lines.append(line)
        index += 1
        continue

    image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped)
    if image_match:
        if image_match.group(1) == "Supplementary Figure 5" and not CURRENT:
            index += 1
            continue
        close_itemize()
        resolved = (SOURCE.parent / image_match.group(2)).resolve()
        if CURRENT:
            number = re.fullmatch(r"Supplementary Figure (\d+)", image_match.group(1)).group(1)
            resolved = (
                args.current_figures / f"AIDRBench_Supplementary_Figure_{number}.pdf"
            ).resolve()
        relative = resolved.relative_to(ROOT).as_posix()
        pending_image = (image_match.group(1), "../../" + relative)
        index += 1
        continue

    if pending_image is not None and stripped:
        flush_image(stripped)
        index += 1
        continue

    if stripped.startswith("| "):
        close_itemize()
        table_lines: list[str] = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            table_lines.append(lines[index].strip())
            index += 1
        table_rows = [split_table_row(item) for item in table_lines]
        if len(table_rows) >= 2 and is_separator_row(table_rows[1]):
            table_rows.pop(1)
        output.append(render_table(table_rows))
        continue

    if stripped.startswith("## "):
        close_itemize()
        flush_image()
        current_section = stripped[3:]
        if current_section in {
            "Supplementary Methods",
            "Supplementary Figures",
            "Supplementary Tables",
        }:
            output.append("\\clearpage\n")
        output.append("\\section{" + inline_latex(current_section) + "}\n")
        index += 1
        continue

    if stripped.startswith("### "):
        close_itemize()
        flush_image()
        heading = stripped[4:]
        if current_section == "Supplementary Figures":
            figure_index += 1
            if figure_index > 1:
                output.append("\\clearpage\n")
        elif current_section == "Supplementary Tables":
            if heading.startswith(
                (
                    "Supplementary Table 4",
                    "Supplementary Table 7",
                    "Supplementary Table 10",
                    "Supplementary Table 11",
                    "Supplementary Table 13",
                    "Supplementary Table 14",
                    "Supplementary Table 20",
                )
            ):
                output.append("\\clearpage\n")
            else:
                output.append("\\pagebreak[2]\n")
        # The titleformat hook places the anchor after any heading page break.
        output.append("\\subsection{" + inline_latex(heading) + "}\n")
        if heading.startswith("Supplementary Figure 5") and not CURRENT:
            if preview_pdf is not None:
                pending_image = (
                    "Accepted Web-GPT S5"
                    if WEB
                    else "Local S5 draft; formal Web-GPT artwork pending",
                    "../../" + preview_pdf.relative_to(ROOT).as_posix(),
                )
            else:
                output.append(
                    "\\begin{quote}\\small\\bfseries Formal Web-GPT artwork pending. "
                    "The exact panel data and current legend are available.\\end{quote}\n"
                )
        index += 1
        continue

    if stripped.startswith("#### "):
        close_itemize()
        output.append("\\subsubsection{" + inline_latex(stripped[5:]) + "}\n")
        index += 1
        continue

    if stripped.startswith("- ") or re.match(r"\s+- ", line):
        if not in_itemize:
            output.append("\\begin{itemize}\n")
            in_itemize = True
        output.append("\\item " + inline_latex(stripped[2:]) + "\n")
        index += 1
        continue
    close_itemize()

    if not stripped:
        output.append("\n")
        index += 1
        continue
    if stripped.startswith("Inputs are directly recorded in "):
        output.append("{\\RaggedRight " + inline_latex(stripped) + "\\par}\n\n")
    else:
        output.append(inline_latex(stripped) + "\n\n")
    index += 1

close_itemize()
flush_image()
output.append("\\end{document}\n")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(output), encoding="utf-8")
print(OUTPUT)
