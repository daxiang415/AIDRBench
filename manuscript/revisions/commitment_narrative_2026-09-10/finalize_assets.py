"""Write complete panel mappings and frozen source/artwork manifests."""
import csv
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE=ROOT/'manuscript/source_data/nature_commitment_narrative_v1'
ART=ROOT/'docs/figures/commitment_narrative_v1/artwork'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    maps=[]
    def row(fig,panel,table,selection,columns,uncertainty):
        assert (SOURCE/table).is_file()
        maps.append(dict(figure=fig,panel=panel,table=table,selection=selection,columns=columns,uncertainty=uncertainty))
    row('3','a','refinement_selected_confirmed.csv','Both durations and both service endpoints','selected_capacity_kw;confirmation_successes;confirmation_lower','One-sided 95% Wilson; n=300; no test-set reselection')
    row('3','b','ready_pi_categories.csv','Five variants; zero-miss full 5.90 kW; three diagnostic seeds each','variant;category;cases','Mechanism counts; not prevalence')
    row('3','c','timing_cross_summary.csv','fraction=0.5; both weights and both orders','weight;ordering;successes_1pct;successes_zero','Descriptive counts from eight observed weeks x ten synthetic realisations')
    row('3','d','weighted_week_summary.csv','fraction=0.5; ordering=chronological; both weights','week;weight;successes_zero','Ten realisations per observed week; no binomial confidence inference')
    row('4','a','paired_resource_supply_margins.csv','All 80 paired resource-time realisations at 2.95 kW','week;seed;chronological;permuted','Every paired point; zero defines necessary supply condition')
    row('4','b','supply_hourly_example.csv','Lowest seed 990000; chronological; hour<168; both weights','hour;weight;event_active;available_reduction_kw;request_kw','Illustrative raw step traces; all 216 h are retained in table')
    row('4','c','decision_steps.csv','All four steps in order','step;criterion;decision','Qualitative decision logic; not experimental estimates')
    row('S3','a,b','refinement_development_summary.csv','All four/eight-hour candidates and both endpoints','program;capacity_kw;wilson_lower','One-sided 95% Wilson; n=100')
    row('S3','c','confirmation_summary.csv','H8P16; repeated; fraction=1; success_1pct; six baseline structural variants','variant;instantaneous_supply_limited_trials;failed_deadline_miss','Potentially overlapping failure families; n=300')
    row('S3','d','external_cross_score_weekly.csv','fraction=0.75 with prescribed 0.5 comparator','week;successes_zero;instantaneous_shortage','Separate 986000-series; both scores coincide')
    row('S4','a','renewable_paired_comparisons.csv','pv_hosting; five primary cases; both BESS modes','case;bess_enabled;difference_of_all_scenario_minima','Difference of two minima over n=100; no mean/CI interpretation')
    row('S4','b','renewable_paired_comparisons.csv','fixed_pv_operation; five primary cases; both BESS modes','case;bess_enabled;mean_paired_gain;gain_ci_low;gain_ci_high','Mean and 95% paired bootstrap CI; excludes optimisation error')
    row('S4','c','single_confirm_summary.csv','f10; notice_h=0; both durations','case;duration_h;successes;trials;wilson_lower','One-sided 95% Wilson; n=300')
    row('S4','c','control_causal_summary.csv','GPU 20/30 and rigid proxy 150/225; both durations','case;duration_h;successes;trials;wilson_lower','One-sided 95% Wilson; n=300')
    row('S4','d','renewable_paired_comparisons.csv','pv_hosting; f10 and four allocation/power controls','case;bess_enabled;difference_of_all_scenario_minima','Difference of minima; n=100')
    with (SOURCE/'PANEL_DATA_MAP.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(maps[0]));w.writeheader();w.writerows(maps)
    (SOURCE/'README.md').write_text('''# v0.25 直接绘图表

本版重新组织现有证据，不新增实验、不选择新报价。`PANEL_DATA_MAP.csv` 逐面板对应图 3、4、S3、S4；其余七张图保留 v0.24 数据及图形。

运行 `plot_narrative.py --data 此目录 --output 输出目录` 即可绘制这四张图，无需数据清洗、模拟或重新抽样。`decision_steps.csv` 可直接修改图 4c 的步骤和决策文字。

`supply_margin_trials.csv` 保留两个请求的全部 640 条记录，`paired_resource_supply_margins.csv` 是 2.95 kW 的 80 个资源时间配对点。`supply_hourly_example.csv` 保留最低协议种子 990000 在四种表示下的全部 216 h；主图按预先声明的 168 h 到达时域显示原序的两个权重，没有按结果挑选种子。其余均为先前已交付表的完整副本。

完整原始控制轨迹、冻结输入、PI 见证、生产任务资源时间与原协议保留在前版 `nature_commitment_mechanisms_v1`，完整包中路径为 `03_data/commitment_mechanisms/`；结构数据在 `03_data/operating_tradeoffs/`，五档及 PV 数据在 `03_data/`。本目录是新增的绘图入口，并不替代完整证据。

## 供给余量

每个小时的余量（kW）= 基线 PCC 功率 − 社区功率 − 空闲及刚性固定数据中心功率 − 0.95 × 请求。对事件小时取最小值，负值表示必要供给条件不满足；与既有账本一致，短缺计数使用 −1e−7 kW 数值容差。通过这一条件并不保证工作期限、恢复或整体资格。

固定功率由冻结硬件、利用率及功率参数独立重建，并与逐类别执行电量核对（1e−8 容差）。原日志中没有执行的类别项可为空，合计检查确认这些空项表示零执行，原日志未改写。所有缺口小时计数与原账本逐条一致。

小时置乱同时改变顺序、时间依赖以及与调用和社区的对齐，不能单独解释为自相关干预。八个观察周各十个合成实现不等于八十个独立生产周；不根据合并计数构造生产可靠性置信保证。
''')
    files=sorted(p for p in SOURCE.rglob('*') if p.is_file() and p.name not in ['FILE_MANIFEST.csv','SHA256SUMS.txt'])
    rows=[dict(path=str(p.relative_to(SOURCE)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    with (SOURCE/'FILE_MANIFEST.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
    (SOURCE/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in rows)+f'{sha(SOURCE/"FILE_MANIFEST.csv")}  FILE_MANIFEST.csv\n')
    for prefix,count,name in [('AIDRBench_Figure_',6,'source_manifest.json'),('AIDRBench_Supplementary_Figure_',5,'supplement_source_manifest.json')]:
        outputs={}
        for n in range(1,count+1):
            for ext in ['pdf','svg','png','tiff']:
                p=ART/f'{prefix}{n}.{ext}';outputs[p.name]=dict(sha256=sha(p),bytes=p.stat().st_size)
        (ART/name).write_text(json.dumps(dict(version='0.25',outputs=outputs,new_plot_script_sha256=sha(HERE/'plot_narrative.py'),source_manifest_sha256=sha(SOURCE/'FILE_MANIFEST.csv')),indent=2)+'\n')
    print(json.dumps(dict(source_files=len(rows),source_bytes=sum(r['bytes'] for r in rows),panel_map_rows=len(maps),figures=11,new_simulations=0)))

if __name__=='__main__':main()
