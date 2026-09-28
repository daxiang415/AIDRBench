# v0.27 / 正文图 R8：LaTeX 投稿与阅读包

本包已把作者提供的 `figure0915.zip` 六张正文图核对、订正并排入正文。论文科学版本仍为 v0.27；本轮只修改图件、图注中的配色/线型说明及相关排版。

- `main.pdf`：新版英文正文，包含六张主图。
- `main.tex`：与上述 PDF 对应的正文源码。
- `supplement.pdf` / `supplement.tex`：完整补充材料；科学内容沿用上一版。
- `figures/`：六张新主图及十张原补充图，均为 PDF。
- `图件核对与修改说明.md`：逐图说明修正内容和依据。
- `FILE_MANIFEST.csv` / `SHA256SUMS.txt`：交付文件校验清单。

## 编译

将本文件夹全部上传到 Overleaf，选用 XeLaTeX；正文选择 `main.tex` 为主文件，补充材料选择 `supplement.tex`。引用已包含在 TeX 内，不需额外 BibTeX 文件。

本地运行 `python BUILD.py --engine xelatex`；也支持 `python BUILD.py --engine /path/to/tectonic`。验证下载完整性：`python VERIFY_DELIVERY.py`。修改或重新编译后文件哈希会改变，届时旧哈希只用于校验交付原件。

作者、单位、通讯邮箱、基金、作者贡献、利益声明、许可证和正式归档信息仍保留原待确认状态。本包是供作者核对和投稿操作的材料，尚未向期刊提交。
