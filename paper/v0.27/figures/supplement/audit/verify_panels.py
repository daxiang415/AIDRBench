"""Compare delivered numeric series against artists captured from frozen renderers."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
DATA=HERE.parent

def same(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    return a.shape==b.shape and np.allclose(a,b,rtol=1e-12,atol=1e-12,equal_nan=True)

def name(key):
    return 'AIDRBench_'+('Figure_' if key[0]=='F' else 'Supplementary_Figure_')+str(int(key[1:]))

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--captured',type=Path,default=HERE/'captured')
    parser.add_argument('--report',type=Path,default=HERE/'PANEL_VERIFICATION.json')
    args=parser.parse_args()
    CAPTURE_DIR=args.captured
    tables={x['id']:x for x in json.loads((DATA/'PANEL_INDEX.json').read_text())}
    bindings=json.loads((DATA/'PLOT_ASSIGNMENTS.json').read_text());report=[]
    captured={key:json.loads((CAPTURE_DIR/(name(key)+'.json')).read_text()) for key in {t['figure'] for t in tables.values()}}
    for bind in bindings:
        tab=tables[bind['table']];df=pd.read_csv(DATA/tab['file']);artists=captured[tab['figure']][tab['panel']]['artists']
        kind=bind['kind'];matched=[];mode='whole_series'
        if kind=='matrix':
            expected=df[bind['columns']].to_numpy()
            if bind.get('transpose'):expected=expected.T
            matched=[a for a in artists if a['kind']=='matrix' and same(expected,a['values'])]
        else:
            expected=df[[bind['x'],bind['y']]].to_numpy()
            if kind=='points':
                candidates=[a for a in artists if a['kind'] in ['line','scatter']]
                matched=[a for a in candidates if same(expected,a['xy'])]
                if not matched:
                    # Some original renderers create one scatter/marker per record.
                    singleton=[a['xy'][0] for a in candidates if len(a['xy'])==1]
                    if singleton and all(any(same(p,q) for q in singleton) for p in expected):
                        matched=[{'kind':'individual_markers'}];mode='individual_markers'
            elif kind in ['bar','barh']:
                bottom=df[bind['bottom']].to_numpy() if 'bottom' in bind else np.zeros(len(df))
                matched=[a for a in artists if a['kind']=='bar' and a['orientation']==('vertical' if kind=='bar' else 'horizontal') and same(expected,a['xy']) and same(bottom,a['bottom'])]
            elif kind=='errorbar':
                segments=[[[x,lo],[x,hi]] for x,lo,hi in zip(df[bind['x']],df[bind['lower']],df[bind['upper']])]
                matched=[a for a in artists if a['kind']=='errorbar' and same(expected,a['xy']) and same(segments,a['segments'])]
        report.append(dict(table=bind['table'],series=bind['series'],kind=kind,passed=bool(matched),comparison=mode))
    quantitative={(f,p) for f,r in captured.items() for p,d in r.items() if d['artists'] and (f,p) not in [('F01','a'),('F01','c'),('S01','a'),('S01','b')]}
    covered={(tables[b['table']]['figure'],tables[b['table']]['panel']) for b in bindings}
    result=dict(series=len(report),passed=sum(r['passed'] for r in report),all_series_pass=all(r['passed'] for r in report),quantitative_panels=len(quantitative),uncovered_panels=sorted(quantitative-covered),tolerance=dict(rtol=1e-12,atol=1e-12),checks=report)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    for r in report:
        if not r['passed']:print('FAILED:',r)
    if not result['all_series_pass'] or result['uncovered_panels']:raise SystemExit(1)

if __name__=='__main__':main()
