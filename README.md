# AIDRBench — manuscript v0.27 / main figures R8

**当前科学稿：v0.27。** 六张正文图为2026-09-17的R8修订稿，补充图S1–S10及全部直接绘图数据已包含。2026-09-28整理为Windows可编辑的GitHub版本，科学结果未改变。

**Windows下载后先读：[WINDOWS_START_HERE.md](WINDOWS_START_HERE.md)。** 修改论文、图和研究代码均可在自己的电脑上完成。

| 内容 | 直接入口 |
| --- | --- |
| 英文正文：PDF / LaTeX | [main.pdf](paper/v0.27/latex/main.pdf) · [main.tex](paper/v0.27/latex/main.tex) |
| 英文补充材料：PDF / LaTeX | [supplement.pdf](paper/v0.27/latex/supplement.pdf) · [supplement.tex](paper/v0.27/latex/supplement.tex) |
| 中文正文与补充材料 | [正文](paper/v0.27/chinese/main_zh.md) · [补充材料](paper/v0.27/chinese/supplement_zh.md) |
| 正文六图：PPTX、SVG、CSV/Excel与代码 | [正文绘图包](paper/v0.27/figures/main/README_中文_给合作者.md) |
| 补充十图：CSV/Excel与直接重绘代码 | [补充绘图包](paper/v0.27/figures/supplement/README_中文_给合作者.md) |
| 英文Markdown协作稿 | [正文](manuscript/nature_communications_article.md) · [补充材料](manuscript/supplementary_information.md) |
| 研究代码 / 参数 / 测试 | [src/aidrbench](src/aidrbench) · [configs](configs) · [tests](tests) |
| 版本说明及验证 | [版本说明](docs/GITHUB_V027.md) · [核验记录](docs/github_v027_validation.json) |

正文18页、6主图；补充材料32页、10补充图、24补充表。作者信息、基金、贡献、利益声明、软件许可证及归档编号仍待确认；尚未向期刊提交。

## Research question

**Reliable demand-response commitments from AI data centres under service constraints.** AIDRBench connects workload composition and timing to deliverable power reductions, service-preserving scheduling and conditional participation costs.

Within the tested eight-week workload distribution, retaining task resource-time information reduced the selected, independently confirmed eight-hour offer from 2.95 to 1.47 kW. The study distinguishes insufficient available load, strict scheduling infeasibility and causal-controller failure before pricing separately qualified reference products. These results are conditional on the stated model and workload distribution.

## Editing and running

- Compile the self-contained LaTeX with XeLaTeX (MiKTeX/TeX Live), Tectonic or Overleaf.
- All current plotting coordinates are supplied as CSV and Excel. Supplementary figures render directly from these CSVs; main figures retain the author's editable PowerPoint and replacement-panel code.
- Python 3.12 is required. Install with `python -m pip install -e ".[control,analysis,dev,paper]"`. PowerShell commands are in the Windows guide.
- Editing and redraw require neither a GPU nor access to the original server.
- Bulk raw workloads, complete hourly trajectories and simulation-recovery inputs remain outside Git. Compact evidence, plotted data, research drivers and test fixtures are included. Full-scale replay needs the separately held original inputs.

The old `codex/manuscript-v025` branch remains a historical review snapshot. Older version-labelled reports are provenance records; use the links above for current editing.
