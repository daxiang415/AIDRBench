"""Execute frozen tasks after preparing immutable program inputs in parallel."""
import json
import pandas as pd
import run_extension as x


if __name__=='__main__':
    p=json.loads((x.HERE/'selection.json').read_text())
    assert p['protocol_sha256']==x.m.sha(x.PROTOCOL)
    tasks=p['confirmation_tasks']
    for t in tasks:
        path=x.OUT/'programs'/'confirmation'/t['case']/t['program']/f'hourly_seed_{t["seed"]}'/'metadata.json'
        assert path.exists(),path
    x.m.save(x.HERE/'confirmation_launch.json',dict(selection_sha256=x.m.sha(x.HERE/'selection.json'),
        launch_script_sha256=x.m.sha(__file__),tasks=len(tasks),workers=48,changes_to_task_function=False))
    rows=x.m.parallel(x.run_task,tasks,48,'confirmation')
    records=[r['task']|dict(success=r['success'],capacity_kw=r['capacity_kw'],
        failures=','.join(sorted({f for e in r['events'] for f in e['failures']})),
        missed_gpu_h=r['ledger']['incremental_missed_gpu_h']) for r in rows]
    df=pd.DataFrame(records).sort_values(['case','program','controller','fraction','kind','seed'])
    df.to_csv(x.OUT/'confirmation_outcomes.csv',index=False)
    print(df.groupby(['case','program','controller','fraction','kind']).agg(successes=('success','sum'),trials=('success','size')).to_string(),flush=True)
