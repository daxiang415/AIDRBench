"""Move current reader entry points to the completed v0.24 release."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def main():
    package=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip';assert package.exists() or (ROOT/"results/exports/AIDRBench_Figures_v13/CURRENT_VERSION.json").exists()
    p=ROOT/'README.md';text=p.read_text();history=text[text.index('## 历史研究设计与开发记录'):];history=history.replace('当前结果以文首 v0.23','当前结果以文首 v0.24',1)
    p.write_text('''# AIDRBench：工作时序、服务承诺与参与成本

当前英文正文与补充材料 **v0.24**，中文逐段稿 **v18**，完整绘图恢复包 **v13**。

- [正文中文](docs/chinese_reader/v18/main_zh.md) · [补充材料中文](docs/chinese_reader/v18/supplement_zh.md)
- [正文 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.24_content_revision.pdf) · [补充 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.24_Supplementary_Information_content_revision.pdf)
- [六张主图](docs/nature-mainline-figure-preview.md) · [五张补充图](docs/nature-supplementary-figure-preview.md)
- [全部图片、现成数据与恢复包](results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip) · [详细结果与修改理由](manuscript/revisions/commitment_mechanisms_2026-09-10/RESULTS_AND_REASONS_ZH.md)
- [权威文件与恢复入口](MAINLINE_FILES.md)

本版局部加密后，参考四/八小时重复报价为 **5.60/4.42 kW**，两种服务标准选值相同；零漏期确认 **297/300、296/300**。原“严格标准必然使参考报价降至 2.95 kW”的概括已撤回。

八周配对测试保持工作周总量相同，将提交次数权重替换为实际任务资源时间权重后，固定 **2.95 kW 的原序成功数由 80/80 降至 31/80**，后者全部 49 次失败触及即时供给不足；无响应基线全部可行。完整未来信息对照区分即时不足、严格时间窗不可行和因果控制差距。

早期 PI 仅为累计条件下的放松规划界限，现已更正标签；新可行性使用每个工作组自身的释放—期限时间窗。参考等待价格下，四/八小时无固定费门槛为 **183.30/330.11 美元/报价 kW·年**，价格结果不能用于外部测试失败的工作负载。

新增 3,040 次完整重放、656,640 小时行、720 份冻结输入和 38 项可行性诊断。图 3、6、S3、S5 重绘，图 2、5 更正标签；全套六主图、五补充图与 21 张补充表完整交付。没有启动子智能体。作者信息、基金、许可证与公开归档仍待用户决定。

'''+history)
    p=ROOT/'MAINLINE_FILES.md';history=p.read_text().split('## Archived baseline documentation: v0.19 and earlier',1)[1]
    p.write_text('''# AIDRBench formal mainline

## Current v0.24, 2026-09-10

- English: `manuscript/nature_communications_article.md`, `manuscript/supplementary_information.md`.
- Chinese: `docs/chinese_reader/v18/`, exactly aligned by paragraph.
- PDFs: v0.24 files in `manuscript/exports/`; six main figures, five supplementary figures, 21 supplementary tables.
- New complete data: `manuscript/source_data/nature_commitment_mechanisms_v1/`; 3,040 trajectories, 656,640 hourly rows, 720 frozen scenarios, 38 resolved fixed-request PI diagnoses, complete task-resource-time reconstruction.
- Current artwork: `docs/figures/commitment_mechanisms_v1/artwork/`, PNG/PDF/SVG/TIFF for all eleven.
- Complete handoff: `results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip`.
- Protocols, audit, detailed Chinese rationale and text changes: `manuscript/revisions/commitment_mechanisms_2026-09-10/`.

## Authority and scientific correction

The local refinement uses new development 988000–988099 and confirmation 989000–989299, fixed before execution in `refinement_protocol.json` and `refinement_selection.json`. Both standards select the same four/eight-hour offers, 5.603331/4.423682 kW. The earlier reference zero-loss derating is not a stable physical result. Task resource-time tests use new 990000-series realizations with frozen `workload_protocol.json`; they do not select new offers or certify production reliability.

The earlier cumulative release/deadline PI formulation is a relaxation for crossing job windows. Its existing numeric tables are retained as relaxed planning statistics, not guaranteed job-feasible capacities. New exact-window diagnostics use per-group execution edges and every original electrical criterion, including the actual event-peak rebound denominator. A verified PI schedule does not prove causal realizability. Earlier causal queue ledgers and the separate edge-based PV optimizer are unaffected by this interpretation correction.

The new study preserves all older data: five-workload `nature_workload_composition_v1`, recovery `nature_repeat_mechanism_v1`, structural/timing `nature_operating_tradeoffs_v1`. Their frozen protocols and code hashes must not be retroactively changed. Earlier samples must not be pooled with the new confirmation.

## Direct recovery and plotting

The complete v13 package runs `RUN_ALL_FIGURES.py` from ready CSV tables. `04_code/commitment_mechanisms/replay_one.py` restores any new trajectory from relative frozen inputs and compares 92 numerical columns; `replay_pi.py` reproduces exact-window feasibility using the inherited packaged structural inputs. Old absolute paths are provenance only, not dependencies of these entry points. Original complete sources and historical manuscript versions are preserved in the package.

## Collaboration and remaining scope

Do not start sub-agents or delegated reviews unless explicitly asked. Local Python plotting is authorised; historical web-only figure instructions are superseded. Do not fill author names, affiliations, contributions, funding, licence or public archive DOI without the user's information. No publication, repository upload or commit has been performed for this revision.

Statistical qualifications are pointwise and scenario-specific. Eight observed weeks × ten synthetic realisations are not 80 independent weeks. Task resource-time is allocated work, not measured busy-GPU activity; deadlines and permissions remain synthetic and no application pause/checkpoint/restart was measured. Economic price boundaries apply to the reference distribution only, with independent annual series rather than a continuous operating year.

## Archived baseline documentation: v0.19 and earlier'''+history)
    (ROOT/'docs/chinese_reader/README.md').write_text('# 中文阅读稿\n\n当前 [v18](v18/README.md)，对应英文正文/SI v0.24。\n\n- [正文中文](v18/main_zh.md)\n- [补充中文](v18/supplement_zh.md)\n- [正文中英对照](v18/main_bilingual.md)\n- [补充中英对照](v18/supplement_bilingual.md)\n\n六主图、五补充图、21 张补充表。v1–v17 为历史阅读稿。\n')
    (ROOT/'docs/paper-packaging.md').write_text('''# 当前论文 v0.24 与完整绘图包 v13

[完整包](../results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip) 含全部现成绘图数据、完整小时轨迹、冻结输入、英文正文/SI、中文 v18 和十一张 PNG/PDF/SVG/TIFF 图片。

解压后运行 `python RUN_ALL_FIGURES.py`；已有依赖加 `--use-current-python`。每张图目录提供图注和面板数据映射；图 3、6、S3、S5 的新 CSV 在对应 ready_data/。不需预处理原始数据或重新模拟。

新增数据在 `03_data/commitment_mechanisms/`，保留 3,040 次完整重放、656,640 小时行、720 份冻结输入、38 个 PI 诊断和原始任务资源时间重建。前版全部数据仍在原目录，不覆盖旧 ZIP。

直接回放：包内 `04_code/commitment_mechanisms/replay_one.py`；严格工作组 PI：`replay_pi.py`。详细命令见包内 README_FIRST.md。新科学判断、旧 PI 放松解释更正、数字核查与验证记录在 `05_audit/commitment_mechanisms_v024/`。

本版主参考四/八小时报价 5.60/4.42 kW；资源时间时序测试揭示固定报价不能直接适用。无实测暂停/恢复与全年连续运行主张。作者、基金、许可证和 DOI 仍待确认。
''')
    for stem,name,tag,n in [('main','nature-mainline-figure-preview.md','Figure',6),('supplement','nature-supplementary-figure-preview.md','Supplementary Figure',5)]:
        rows=json.loads((ROOT/f'docs/chinese_reader/v18/{stem}_aligned_blocks.json').read_text())['blocks'];parts=['# Current v0.24 figures','Six main figures and five supplementary figures. Complete ready-data/replay handoff: v13.']
        for i in range(1,n+1):
            index=next(j for j,r in enumerate(rows) if r['en'].startswith(f'### {tag} {i} |'));caption=rows[index+1]['en'] if stem=='main' else rows[index+2]['en']
            parts.extend([rows[index]['en'].replace('### ','## ',1),f'![{tag} {i}](figures/commitment_mechanisms_v1/artwork/AIDRBench_{tag.replace(" ","_")}_{i}.png)',caption])
        (ROOT/'docs'/name).write_text('\n\n'.join(parts)+'\n')
    for path in ['docs/all_figure_handoff/README_FIRST.md','docs/figure_recovery/README.md']:
        p=ROOT/path;old=p.read_text();p.write_text('# 当前完整交付 v13\n\n[全部十一图、现成数据和完整恢复包](../../results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip)。对应英文正文/SI v0.24、中文 v18。新增局部加密、严格 PI 与任务资源时间对照，全部当前图和图注已同步。\n\n根目录 RUN_ALL_FIGURES.py 直接重绘。commitment_mechanisms/replay_one.py 和 replay_pi.py 保存恢复能力。以下内容保留历史记录。\n\n---\n\n'+old)
    p=ROOT/'manuscript/results-evidence-allocation.md';p.write_text('# Current v0.24 evidence allocation\n\n'+(HERE/'CONTENT_PLAN.md').read_text()+'\nDetailed version-specific source and rationale: `revisions/commitment_mechanisms_2026-09-10/RESULTS_AND_REASONS_ZH.md`.\n')
    p=ROOT/'manuscript/terminology-ledger.md';old=p.read_text();p.write_text('# v0.24 terminology correction\n\n- Earlier PI values: relaxed planning statistics; not guaranteed feasible capacities for individual job windows.\n- New PI diagnosis: fixed-request exact-window feasibility, not a causal certificate.\n- Resource-time transfer: task allocation-time weighted, normalised observed-week submission structure; not sensor GPU activity or application validation.\n- Zero-loss qualification: a probabilistic criterion on scenario-level zero missed work, not every confirmation trajectory being lossless.\n- Current reference repeated offers: 5.603331 / 4.423682 kW at four/eight hours, 16-h start spacing.\n\n## Earlier terminology history\n\n'+old.rstrip()+'\n')
    p=ROOT/'data/manifests/sources.yaml';s=p.read_text().replace('role: chronological_hourly_submission_counts_for_v023_structural_transfer_test','role: chronological_submission_counts_and_task_resource_time_for_v024_transfer_tests').replace('mainline_scope: eight_observed_weeks_with_synthetic_work_sizes_and_deadlines','mainline_scope: eight_observed_weeks_with_verified_task_resource_time_weights_normalised_totals_and_synthetic_classes_and_deadlines');p.write_text(s)
    print('Current indices updated',flush=True)
if __name__=='__main__':main()
