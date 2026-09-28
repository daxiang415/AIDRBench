# Windows：下载、修改 v0.27 论文和代码

这份仓库包含当前科学稿 **v0.27**、2026-09-17 正文图 **R8**、10张补充图及直接绘图数据。正文18页，补充材料32页、24张补充表。作者、基金、利益声明、许可证和归档编号仍待作者确认。

## 1. 下载到 Windows

只想打开和修改文件：GitHub页面选择 **Code → Download ZIP**，解压到例如 `C:\research\AIDRBench`。无需连接原来的Linux服务器。

想长期修改并同步回GitHub：安装Git和Python 3.12，打开PowerShell：

```powershell
git clone https://github.com/daxiang415/AIDRBench.git
cd AIDRBench
git switch -c my-paper-edits
```

也可以用GitHub Desktop克隆。下载ZIP适合直接改文件；`git clone`还会保留版本历史，便于后续提交。

## 2. 修改论文：打开这些文件

| 要修改什么 | 文件 |
| --- | --- |
| 英文正文及排版 | [paper/v0.27/latex/main.tex](paper/v0.27/latex/main.tex) |
| 英文补充材料及排版 | [paper/v0.27/latex/supplement.tex](paper/v0.27/latex/supplement.tex) |
| 当前PDF | [正文](paper/v0.27/latex/main.pdf)、[补充材料](paper/v0.27/latex/supplement.pdf) |
| 中文逐段阅读稿 | [正文](paper/v0.27/chinese/main_zh.md)、[补充材料](paper/v0.27/chinese/supplement_zh.md) |
| 英文Markdown协作稿 | [正文](manuscript/nature_communications_article.md)、[补充材料](manuscript/supplementary_information.md) |

**投稿排版建议直接改 `main.tex` / `supplement.tex`。** Markdown与中文稿是并行的阅读、协作版本，修改TeX不会自动翻译或回写Markdown，修改Markdown也不会自动覆盖投稿TeX。

本地编译：安装MiKTeX或TeX Live，并确保命令行能找到 `xelatex`。在仓库根目录运行：

```powershell
py -3.12 paper/v0.27/latex/BUILD.py --engine xelatex
```

也可以把整个 `paper/v0.27/latex` 文件夹上传Overleaf，选择 **XeLaTeX**，分别以 `main.tex` 或 `supplement.tex` 为主文件。参考文献已写在TeX中，无需另建BibTeX库。`figures`文件夹必须一同保留。

如果从英文Markdown生成排版审阅稿，可运行以下命令；生成文件进入 `manuscript/exports`，不会覆盖上述投稿TeX：

```powershell
$env:PYTHONUTF8 = "1"
py -3.12 scripts/render_review_tex.py
py -3.12 scripts/render_supplementary_tex.py
```

## 3. 修改图：每张图的数据已配好

- **正文六图**：[paper/v0.27/figures/main](paper/v0.27/figures/main/README_中文_给合作者.md)。`03_EDITABLE`内为校正PPTX和SVG；`02_PANEL_DATA/F01`–`F06`内为CSV/Excel。11个修订面板为嵌入SVG，其余为原生PowerPoint对象。
- **补充十图**：[paper/v0.27/figures/supplement](paper/v0.27/figures/supplement/README_中文_给合作者.md)。`S01`–`S10`每图一个文件夹，含参考图、CSV/Excel与横轴、纵轴和误差条说明。
- 正文图1的SVG引用同目录 `Figure_1_assets` 内的配套素材；单独复制SVG时需要连这个文件夹一起复制。PDF、PNG和PPTX可直接使用。
- S1为流程示意图；定量图无需再筛选旧源表、换算单位或计算区间。

用Python改图，先在PowerShell设置UTF-8并安装依赖。每次打开新的终端，重新设置下面的环境变量：

```powershell
$env:PYTHONUTF8 = "1"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[paper]"
```

直接重绘补充图（输出到`MY_REDRAW`，不覆盖参考图）：

```powershell
.\.venv\Scripts\python.exe paper/v0.27/figures/supplement/DRAW_SUPPLEMENT.py
```

只重绘某张：在最后加 `--figures S5`。程序读取的是对应文件夹中的CSV；Excel是同值副本，修改Excel后需将对应工作表另存为同名CSV。

重建正文修订面板和PPTX：

```powershell
.\.venv\Scripts\python.exe scripts/rebuild_main_figures.py --panels-only
```

可用PowerPoint打开 `paper/v0.27/figures/main/rebuild/corrected/AIDRBench_Figures_R8_corrected.pptx` 修改并导出。若需自动生成完整PDF，安装LibreOffice，再省略 `--panels-only`；脚本会查找PATH及Windows常见安装目录。

**改图后，论文不会自动采用它。** 确认新图后，把最终单张PDF复制到 `paper/v0.27/latex/figures/`，保留对应文件名，再编译论文。补充图CSV脚本提供同数据模板，其布局可以与正式参考图不同。

## 4. 修改并验证研究代码

核心库在 `src/aidrbench`，参数在 `configs`，测试在 `tests`。v0.27扩展的原研究驱动和冻结协议保留在 `manuscript/revisions` 的七个研究目录中。安装完整计算、分析和测试依赖：

完整测试包含按历史Git提交重放的检查，请在 **Git克隆的目录** 中运行，并保留完整历史；GitHub的Download ZIP不含Git历史。ZIP仍可用于编辑论文、编辑代码和全部当前图件的重绘。

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pip install -e ".[control,analysis,dev,paper]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe scripts/check_v027_checkout.py
```

常规代码测试、论文编译和现成数据重绘均不需要GPU。GPU功率实测脚本需要相应NVIDIA硬件和测量环境，不能在没有GPU的电脑上照搬运行。

仓库包含全部直接绘图数据、紧凑的结果账本、功率校准数据和测试样例；**不包含几十GB的生产原始轨迹、逐小时完整模拟与恢复输入**。修改论文、图和库代码不需要那些大文件；完整生产规模实验重放仍需另行取得原数据。原研究协议中指向Linux服务器的路径是历史记录，不是Windows绘图入口。

## 5. 保存改动

使用Git克隆的目录中，完成修改并检查后：

```powershell
git status
git add paper/v0.27/latex/main.tex
git commit -m "Revise manuscript text"
git push -u origin my-paper-edits
```

按实际改动添加其他文件，再创建Pull Request合并。`.venv`、重绘临时输出和原始大数据已被忽略，不要把它们提交。首次克隆的交付文件清单可用 `python scripts/check_v027_checkout.py --hashes` 核对；有意修改后哈希变化是正常现象。
