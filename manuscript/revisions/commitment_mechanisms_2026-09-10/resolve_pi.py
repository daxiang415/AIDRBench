"""Preserve the original timeout; spend more solver time on that diagnostic only."""
import json
import pandas as pd
import pi_diagnostic as p
f=p.f
records=[]
for path in sorted((f.OUT/'pi').glob('*/receipt.json')):
    old=json.loads(path.read_text())
    if old['classification']!='unresolved':continue
    task=old['task'];dest=path.parent/'extended_solve';dest.mkdir(exist_ok=True)
    lock=dest/'protocol.json'
    if not lock.exists():f.r.m.save(lock,dict(parent_receipt_sha256=f.r.m.sha(path),action='extend unresolved solve time only; unchanged request, sample and constraints',time_limit_s=600,solver_script_sha256=f.r.m.sha(p.__file__)))
    receipt=dest/'receipt.json'
    if receipt.exists():new=json.loads(receipt.read_text())
    else:
        s=p.snapshot_at(task['scenario'],task['seed'],task['request_kw']);new,hour,extra=p.solve_snapshot(s,task['request_kw'],task['miss_rate'],time_limit=600)
        new.update(task=task,parent_receipt_sha256=f.r.m.sha(path))
        if hour is not None:
            hour.to_parquet(dest/'hourly_witness.parquet',index=False);extra[0].to_parquet(dest/'execution_edges.parquet',index=False);extra[1].to_parquet(dest/'work_groups.parquet',index=False)
        f.r.m.save(receipt,new)
    records.append(new);print(task['id'],new['classification'],flush=True)
summary=pd.read_csv(f.SOURCE/'pi_diagnostic_summary.csv')
for x in records:
    match=summary.id==x['task']['id'];assert match.sum()==1
    summary.loc[match,'initial_classification']=summary.loc[match,'classification']
    for k in ['classification','solver_status','solver_message','seconds','max_constraint_violation','missed_gpu_h','terminal_backlog_gpu_h']:
        if k in x:summary.loc[match,k]=x[k]
summary.to_csv(f.SOURCE/'pi_diagnostic_resolved.csv',index=False)
