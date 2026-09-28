"""Freeze offers and confirmation tasks using development results only."""
from pathlib import Path
import json
import pandas as pd
import run_extension as x


def main():
    p=json.loads(x.PROTOCOL.read_text())
    df=pd.read_csv(x.OUT/'development_outcomes.csv')
    assert len(df)==len(p['development_tasks'])==10100
    keys=['case','program','duration_h','gap_h','controller','fraction','capacity_kw']
    s=df.groupby(keys).success.agg(['sum','size']).reset_index().rename(columns={'sum':'successes','size':'trials'})
    s['wilson_lower']=s.apply(lambda r:x.m.wilson_lower_bound(int(r.successes),int(r.trials),.95),axis=1)
    s['qualified']=s.wilson_lower>=.95
    s.to_csv(x.OUT/'development_summary.csv',index=False)
    selected=[];tasks=[]
    for (case,program,ctrl),g in s.groupby(['case','program','controller']):
        if ctrl=='all_window_greedy':continue
        valid=g[g.qualified].sort_values('fraction')
        row=g.iloc[0]
        chosen=float(valid.fraction.iloc[-1]) if len(valid) else None
        selected.append(dict(case=case,program=program,controller=ctrl,duration_h=int(row.duration_h),gap_h=int(row.gap_h),
            selected_fraction=chosen,selected_capacity_kw=None if chosen is None else chosen*x.capacity(case,int(row.duration_h))))
        fractions={chosen if chosen is not None else 1.}
        if program=='H8G12':fractions.add(1.)
        for fraction in sorted(fractions):
            for seed in range(p['confirmation_seeds'][0],p['confirmation_seeds'][1]+1):
                tasks.append(dict(role='confirmation',case=case,seed=seed,duration_h=int(row.duration_h),gap_h=int(row.gap_h),
                    program=program,controller=ctrl,fraction=fraction,kind='repeated'))
    for seed in range(p['confirmation_seeds'][0],p['confirmation_seeds'][1]+1):
        tasks.append(dict(role='confirmation',case='f10',seed=seed,duration_h=8,gap_h=12,
            program='H8G12',controller='all_window_greedy',fraction=1.,kind='repeated'))
    path=x.HERE/'selection.json';assert not path.exists(),'Selection is immutable'
    result=dict(protocol_sha256=x.m.sha(x.PROTOCOL),development_outcomes_sha256=x.m.sha(x.OUT/'development_outcomes.csv'),
        development_summary_sha256=x.m.sha(x.OUT/'development_summary.csv'),confirmation_not_yet_run=True,
        selected=selected,confirmation_tasks=tasks)
    x.m.save(path,result)
    pd.DataFrame(selected).to_csv(x.OUT/'selected_offers.csv',index=False)
    x.m.save(x.HERE/'PROGRESS.json',dict(status='SELECTION_FROZEN',confirmation_tasks=len(tasks),selection_sha256=x.m.sha(path)))
    print(pd.DataFrame(selected).to_string(index=False))
    print('Confirmation tasks',len(tasks),flush=True)


if __name__=='__main__':main()
