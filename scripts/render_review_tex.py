"""Render the current Markdown as a preliminary content-review TeX file.

Run from any directory; compile the resulting file with XeLaTeX or Tectonic.
Accepted web artwork is inserted unchanged. Author metadata remains pending.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from review_figure_inputs import validated_review_pdf
from web_figure_inputs import validated_web_pdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript/nature_communications_article.md"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--local-figures", type=Path, help="explicitly insert hashed LOCAL REVIEW DRAFT PDFs"
)
parser.add_argument("--web-figures", type=Path, help="insert accepted, hash-verified web artwork")
parser.add_argument(
    "--current-figures", type=Path, help="insert all six current data-driven PDF figures"
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
    validated_review_pdf(args.local_figures, "figure6", ROOT)
    if LOCAL
    else validated_web_pdf(WEB_DIRECTORY, "figure6", ROOT)
    if WEB
    else None
)
variant = (
    "content_revision" if WEB or CURRENT else "local_figure_review" if LOCAL else "content_review"
)
VERSION = re.search(r"version (\d+\.\d+)", SOURCE.read_text())[1]
OUTPUT = ROOT / f"manuscript/exports/AIDRBench_Nature_Communications_v{VERSION}_{variant}.tex"
review_status = (
    f"Local figure review v{VERSION}; drafts only"
    if LOCAL
    else f"Content review v{VERSION}; artwork pending"
)
review_notice = (
    "Local Figure 6 draft included for review only; "
    "formal Web-GPT artwork and author metadata pending."
    if LOCAL
    else "Content review only: Figure 6 artwork and author metadata pending."
)

if WEB:
    review_status = f"Revised manuscript v{VERSION}"
    review_notice = (
        "Content revised; six existing figures retained pending redraw. Author metadata pending."
    )

if CURRENT:
    review_status = f"Revised manuscript v{VERSION}"
    review_notice = (
        "Six current data-driven figures; service, timing and cost evidence updated. "
        "Author metadata pending."
    )
    current_manifest = json.loads((args.current_figures / "source_manifest.json").read_text())
    for n in range(1, 7):
        pdf = args.current_figures / f"AIDRBench_Figure_{n}.pdf"
        if (
            hashlib.sha256(pdf.read_bytes()).hexdigest()
            != current_manifest["outputs"][pdf.name]["sha256"]
        ):
            raise ValueError(f"Current figure {n} differs from its render receipt")


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


def inline_latex(value: str) -> str:
    protected: dict[str, str] = {}

    def keep(rendered: str) -> str:
        token = f"PROTECTEDTOKEN{len(protected):04d}X"
        protected[token] = rendered
        return token

    value = re.sub(r"\\\((.*?)\\\)", lambda m: keep(r"\(" + m.group(1) + r"\)"), value)
    value = re.sub(
        r"<sup>(.*?)</sup>",
        lambda m: keep(r"\textsuperscript{" + escape_text(m.group(1)) + "}"),
        value,
    )
    value = re.sub(
        r"`([^`]+)`",
        lambda m: keep(r"\nolinkurl{" + m.group(1).replace("%", r"\%") + "}"),
        value,
    )

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
        r"\*\*([^*]+)\*\*", lambda m: keep(r"\textbf{" + inline_latex(m.group(1)) + "}"), value
    )
    value = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        lambda m: keep(r"\emph{" + inline_latex(m.group(1)) + "}"),
        value,
    )
    value = escape_text(value)
    for token, rendered in protected.items():
        value = value.replace(token, rendered)
    return value


markdown = SOURCE.read_text(encoding="utf-8")
markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
lines = markdown.splitlines()
title_line = next(line for line in lines if line.startswith("# "))
title = inline_latex(title_line[2:].strip())
figure_titles = {
    match.group(1): match.group(0)[4:]
    for line in lines
    if (match := re.fullmatch(r"### Figure (\d+) \| .+", line.strip()))
}
if set(figure_titles) != {str(number) for number in range(1, 7)}:
    raise ValueError("the main article must define exactly six figure titles")


def figure_page(number: str, graphic: str) -> str:
    """Keep current artwork compact; preserve historical full-page variants."""

    return (
        ("\\begin{figure}[htbp]\n\\centering\n" if CURRENT else "\\begin{figure}[p]\n\\centering\n")
        + (
            "\\begin{minipage}{\\textwidth}\n"
            if CURRENT
            else "\\begin{minipage}[t][0.99\\textheight][t]{\\textwidth}\n"
        )
        + "\\setlength{\\parskip}{0pt}\n"
        f"\\pdfbookmark[1]{{{inline_latex(figure_titles[number])}}}{{main-figure-{number}}}\n"
        "{\\fontsize{10}{12}\\selectfont\\sffamily\\bfseries\\color{AIDRBlue} "
        + inline_latex(figure_titles[number])
        + "\\par}\\vspace{4pt}\n\\centering\n"
        + graphic
        + "\n\\end{minipage}\n\\end{figure}\n"
    )


preamble = rf"""\documentclass[10pt,a4paper]{{article}}
\usepackage[a4paper,top=18mm,bottom=19mm,left=19mm,right=19mm,headheight=13.6pt]{{geometry}}
\usepackage{{fontspec}}
\IfFontExistsTF{{TeX Gyre Termes}}
  {{\setmainfont{{TeX Gyre Termes}}}}{{\setmainfont{{Liberation Serif}}}}
\IfFontExistsTF{{TeX Gyre Heros}}
  {{\setsansfont{{TeX Gyre Heros}}}}{{\setsansfont{{Liberation Sans}}}}
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{hyperref}}
\usepackage{{bookmark}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{fancyhdr}}
\usepackage{{microtype}}
\usepackage{{float}}
\definecolor{{AIDRBlue}}{{HTML}}{{18364A}}
\definecolor{{AIDRLink}}{{HTML}}{{245F7A}}
\hypersetup{{colorlinks=true,linkcolor=AIDRLink,urlcolor=AIDRLink,citecolor=AIDRLink,
pdfauthor={{AIDRBench authors}},
pdftitle={{{title}}}}}
\urlstyle{{same}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{5.5pt plus 1pt minus 0.5pt}}
\setlength{{\emergencystretch}}{{2em}}
\setlist[enumerate]{{leftmargin=*,itemsep=4pt,topsep=4pt}}
\setlist[itemize]{{leftmargin=*,itemsep=2pt,topsep=3pt}}
\titleformat{{\section}}{{\Large\sffamily\bfseries\color{{AIDRBlue}}}}{{}}{{0pt}}{{}}
\titleformat{{\subsection}}{{\large\sffamily\bfseries\color{{AIDRBlue}}}}{{}}{{0pt}}{{}}
\titlespacing*{{\section}}{{0pt}}{{17pt}}{{6pt}}
\titlespacing*{{\subsection}}{{0pt}}{{12pt}}{{4pt}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[L]{{\small\sffamily AIDRBench manuscript review}}
\fancyhead[R]{{\small\sffamily {review_status}}}
\fancyfoot[C]{{\small\thepage}}
\makeatletter
\setlength{{\@fptop}}{{0pt}}
\setlength{{\@fpsep}}{{12pt}}
\setlength{{\@fpbot}}{{0pt plus 1fil}}
\makeatother
\renewcommand{{\topfraction}}{{0.95}}
\renewcommand{{\bottomfraction}}{{0.95}}
\renewcommand{{\textfraction}}{{0.05}}
\renewcommand{{\floatpagefraction}}{{0.80}}
\title{{\sffamily\bfseries {title}}}
\author{{\sffamily [AUTHOR NAMES AND AFFILIATIONS]}}
\date{{Working manuscript v{VERSION}}}
\begin{{document}}
\maketitle
\thispagestyle{{fancy}}
\begin{{center}}\small\bfseries
{review_notice}
\end{{center}}
"""

output: list[str] = [preamble]
in_math = False
math_lines: list[str] = []
in_references = False
in_itemize = False
suppress_author_placeholder = False


def close_itemize() -> None:
    global in_itemize
    if in_itemize:
        output.append("\\end{itemize}\n")
        in_itemize = False


for line in lines:
    stripped = line.strip()
    if line == title_line:
        continue
    if suppress_author_placeholder:
        if stripped == "[AUTHOR NAMES AND AFFILIATIONS]" or not stripped:
            continue
        suppress_author_placeholder = False
    if stripped == r"\[":
        in_math = True
        math_lines = []
        continue
    if stripped == r"\]" and in_math:
        output.append("\\begin{equation*}\n" + "\n".join(math_lines) + "\n\\end{equation*}\n")
        in_math = False
        math_lines = []
        continue
    if in_math:
        math_lines.append(line)
        continue

    image = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped)
    if image:
        if image.group(1) == "Figure 6" and not CURRENT:
            continue
        close_itemize()
        image_path = (
            "../../" + (SOURCE.parent / image.group(2)).resolve().relative_to(ROOT).as_posix()
        )
        figure_number = re.fullmatch(r"Figure (\d+)", image.group(1)).group(1)
        graphic = (
            "\\includegraphics[width=\\textwidth,height=0.86\\textheight,keepaspectratio]"
            f"{{\\detokenize{{{image_path}}}}}"
        )
        if CURRENT:
            formal = args.current_figures / f"AIDRBench_Figure_{figure_number}.pdf"
            image_path = "../../" + formal.resolve().relative_to(ROOT).as_posix()
            graphic = (
                "\\makebox[\\textwidth][c]{\\includegraphics[width=183mm]"
                f"{{\\detokenize{{{image_path}}}}}}}"
            )
        elif figure_number == "1":
            formal = ROOT / "docs/figure1_revision/v3/artwork/AIDRBench_Figure_1.pdf"
            receipt = json.loads((formal.parent / "render_receipt.json").read_text())
            if (
                hashlib.sha256(formal.read_bytes()).hexdigest()
                != receipt["outputs"][formal.name]["sha256"]
            ):
                raise ValueError("Formal Figure 1 does not match its generation receipt")
            image_path = "../../" + formal.relative_to(ROOT).as_posix()
            graphic = (
                "\\makebox[\\textwidth][c]{\\includegraphics[width=183mm]"
                f"{{\\detokenize{{{image_path}}}}}}}"
            )
        output.append(figure_page(figure_number, graphic))
        continue

    if stripped.startswith("## "):
        close_itemize()
        if in_references:
            output.append("\\end{enumerate}}\n")
            in_references = False
        heading = stripped[3:]
        if heading == "Discussion" and not CURRENT:
            if preview_pdf is not None:
                image_path = "../../" + preview_pdf.relative_to(ROOT).as_posix()
                graphic = (
                    f"\\makebox[\\textwidth][c]{{\\includegraphics[width=183mm]{{\\detokenize{{{image_path}}}}}}}"
                    if WEB
                    else (
                        "\\includegraphics[width=\\textwidth,height=0.86\\textheight,keepaspectratio]"
                        f"{{\\detokenize{{{image_path}}}}}"
                    )
                )
                output.append(figure_page("6", graphic))
            else:
                output.append(
                    "\\begin{quote}\\small\\bfseries Figure 6: formal Web-GPT artwork pending. "
                    "The economic results and legend below are current.\\end{quote}\n"
                )
        if heading == "Authors":
            suppress_author_placeholder = True
            continue
        if heading == "Figure Legends":
            output.append("\\clearpage\n")
        output.append(f"\\section*{{{inline_latex(heading)}}}\n")
        if heading == "Figure Legends" and CURRENT:
            output.append("\\small\\setlength{\\parskip}{3pt}\n")
        if heading == "References":
            output.append(
                "{\\small\n\\begin{enumerate}[label=\\arabic*.,leftmargin=*,itemsep=2.5pt]\n"
            )
            in_references = True
        continue

    if stripped.startswith("### "):
        close_itemize()
        if stripped.startswith("### Figure 6 |") and not CURRENT:
            # Keep the complete economics legend on its own review page.
            output.append("\\clearpage\n")
        output.append(f"\\subsection*{{{inline_latex(stripped[4:])}}}\n")
        continue

    if in_references:
        reference = re.match(r"\d+\.\s+(.*)", stripped)
        if reference:
            output.append("\\item " + inline_latex(reference.group(1)) + "\n")
        continue

    if stripped.startswith("- "):
        if not in_itemize:
            output.append("\\begin{itemize}\n")
            in_itemize = True
        output.append("\\item " + inline_latex(stripped[2:]) + "\n")
        continue
    close_itemize()

    if not stripped:
        output.append("\n")
        continue
    output.append(inline_latex(stripped) + "\n\n")

close_itemize()
if in_references:
    output.append("\\end{enumerate}}\n")
output.append("\\end{document}\n")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(output), encoding="utf-8")
print(OUTPUT)
