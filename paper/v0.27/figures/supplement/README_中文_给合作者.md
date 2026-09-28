# 给合作者：补充图 S1–S10，直接取数与重绘

交付：2026-09-17。对应论文 v0.27 的当前补充材料，共10张补充图。与当前LaTeX包中的10张补充图PDF逐文件相同；正文六张图的R8改版没有改变这些补充图的科学数据。本包只整理补充图，正文六图请使用同日R8正文绘图包。

## 从这里开始

1. 先打开 [全部补充图_参考图.pdf](全部补充图_参考图.pdf) 对照图号。
2. 进入 `S01`–`S10` 对应文件夹。每张图的参考PDF、PNG、可编辑SVG、Excel、逐面板CSV、中文作图说明都在同一处。
3. 用Origin或Excel改画：打开 `Sxx_READY.xlsx`，先看第一个“使用说明”工作表，再按面板名选工作表。中文README已逐列指明X、Y、误差和分组。**数据已经筛选、换算完成，不用重新求均值、置信区间、百分比或年度成本。**
4. 想只拿一个Excel：[全部补充图_直接绘图.xlsx](全部补充图_直接绘图.xlsx) 收录全部37张面板表，第一张工作表是索引和说明。无公式、宏或外部链接。

| 图号与中文说明 | 图的内容 | 直接绘图Excel |
| --- | --- | --- |
| [S1](S01/README_中文.md) | 生产记录与功率测量进入响应资格检验、光伏分析和经济核算的流程 | [S01_READY.xlsx](S01/S01_READY.xlsx) |
| [S2](S02/README_中文.md) | 训练与离线推理的 GPU 板卡功率测量、参数拟合和留出验证 | [S02_READY.xlsx](S02/S02_READY.xlsx) |
| [S3](S03/README_中文.md) | 重复响应报价的局部网格筛选、供给与期限失败，以及早期周序列对照 | [S03_READY.xlsx](S03/S03_READY.xlsx) |
| [S4](S04/README_中文.md) | 可延期工作比例、GPU 分配与刚性功率假设下的光伏收益和固定请求交付 | [S04_READY.xlsx](S04/S04_READY.xlsx) |
| [S5](S05/README_中文.md) | 等待与漏期成本估值、接入费用对四小时和八小时响应服务选择的影响 | [S05_READY.xlsx](S05/S05_READY.xlsx) |
| [S6](S06/README_中文.md) | 利用率、任务期限、GPU 分配与调用安排变化下的响应交付和按期完成情况 | [S06_READY.xlsx](S06/S06_READY.xlsx) |
| [S7](S07/README_中文.md) | 有无储能时刚性与灵活调度的光伏接纳容量、弃光电量和电网购电量 | [S07_READY.xlsx](S07/S07_READY.xlsx) |
| [S8](S08/README_中文.md) | 硬件经济寿命、工作价值、等待成本与场站费用对单次响应参与门槛的影响 | [S08_READY.xlsx](S08/S08_READY.xlsx) |
| [S9](S09/README_中文.md) | 参考工作负载与八个观测周分布下的报价选择及独立交付资格检验 | [S09_READY.xlsx](S09/S09_READY.xlsx) |
| [S10](S10/README_中文.md) | 数据中心峰值功率分解、节点固定开销敏感性与光伏求解精度核验 | [S10_READY.xlsx](S10/S10_READY.xlsx) |

## Python直接画：程序读取的就是交给你的CSV

使用Python 3.12或以上，首次安装：

```bash
python -m pip install -r requirements.txt
```

在解压后的包根目录运行：

```bash
python DRAW_SUPPLEMENT.py
```

会把全部10张图的PDF、SVG、300 dpi PNG写入 `MY_REDRAW`，不改动参考图。Windows安装好依赖后也可双击 `一键重绘_Windows.bat`。只画某张或额外导出600 dpi TIFF：

```bash
python DRAW_SUPPLEMENT.py --figures S5
python DRAW_SUPPLEMENT.py --figures S3 S9 --tiff
```

也可以进入任一Sxx目录运行 `python redraw.py`。程序仅依赖本包中的CSV、列映射和轴设置，不读取项目旧源表、不运行模拟。改 `DRAW_SUPPLEMENT.py` 顶部的 `STYLE`、`COLORS` 可调整字体、配色和字号；图例、线型与布局在同一脚本中。

**参考PDF是论文采用的图稿；CSV程序输出的是同数据重绘模板，版式不保证像素一致。** 这次没有用模板替换论文图。用Illustrator修改参考SVG，可以保留原布局。Excel与CSV是同一数据的两种副本；代码读取CSV，若在Excel改数，需要将对应工作表另存为同名CSV。通常只应调整视觉样式。

## 几个已经替你处理好的细节

- CSV保留原始输出精度，Excel已逐单元格核对。`PLOT_ASSIGNMENTS.csv`逐系列给出X/Y、区间端点、堆叠起点或热图列。
- `pct`已是百分数，`pp`已是百分点，`fraction`是0–1概率；不再乘100。S5c的净收益已经换算为千美元。
- `error_minus`与`error_plus`是直接填入Origin/Excel的误差长度；`lower`与`upper`是区间端点。单侧下界只向下画，上误差为0。
- S6四个面板分别是8行×3列矩阵，色标0–300，表示300次中的次数。四种指标分别画，不相加。
- S5d三种费用各有一张CSV，包含拐点，直接连接表中坐标；不需要推算价格公式。
- S8a是预留硬件余量的经济寿命假设，不能改标为“需求响应造成的显卡磨损”。
- **S1是概念流程图**：CSV给文字和画布坐标；没有实测数据或误差条。可直接编辑SVG或运行CSV模板。
- 各图完整中英文图注附在README末尾，另集中提供 `FIGURE_LEGENDS_EN.md` / `FIGURE_LEGENDS_ZH.md`。图注中的样本层级、单位和比较条件请保留。

## 交回什么

每张完成的图交回PDF、SVG或原生可编辑文件，以及修改后的绘图脚本。若数据没有变，直接保留本包CSV；若有任何数值调整，单独列出修改原因，避免只在图上手改。

## 核对记录

`audit/PANEL_VERIFICATION.json`核对CSV与原图实际绘图坐标；`audit/CSV_RENDER_VERIFICATION.json`核对新脚本生成的全部定量系列；`audit/DELIVERY_VALIDATION.json`记录Excel、当前LaTeX图稿和文件校验。运行 `python VERIFY_DELIVERY.py` 可检查交付文件是否完整。科学模拟没有重跑，科学结果未变。
