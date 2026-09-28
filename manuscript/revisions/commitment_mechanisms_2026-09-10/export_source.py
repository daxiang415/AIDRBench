"""Complete portable records and ready curves; all trials, no failure filtering."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import shutil
import importlib.util
import sys
import pandas as pd
import refine_offers as f
spec=importlib.util.spec_from_file_location('operating_export',f.HERE.parent/'operating_tradeoffs_2026-09-09/export_data.py')
e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
e.SOURCE=f.SOURCE

def main():
    frames=[];items=[]
    for role in ['development','confirmation','workload']:
        d,events=e.collect(role);d.to_csv(f.SOURCE/f'{role}_ledgers.csv',index=False);events.to_csv(f.SOURCE/f'{role}_events.csv',index=False);frames.append(d)
        items.extend((key,g.to_dict('records')) for key,g in d.groupby(['role','variant','program','kind','fraction']))
    parts=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for future in as_completed([pool.submit(e.export_group,item) for item in items]):
            parts.append(future.result())
            if len(parts)%10==0:print('Exported',len(parts),'/',len(items),flush=True)
    curves=[row for part in parts for row in part.pop('curves')]
    pd.DataFrame(parts).to_csv(f.SOURCE/'hourly_partition_index.csv',index=False);pd.DataFrame(curves).to_csv(f.SOURCE/'ready_hourly_curves.csv',index=False)
    n=e.inputs(pd.concat(frames,ignore_index=True))
    shutil.copytree(f.OUT/'pi',f.SOURCE/'pi_diagnostics',dirs_exist_ok=True)
    for p in f.HERE.glob('*protocol.json'):shutil.copyfile(p,f.SOURCE/p.name)
    shutil.copyfile(f.HERE/'refinement_selection.json',f.SOURCE/'refinement_selection.json')
    f.r.m.save(f.SOURCE/'export_receipt.json',dict(status='COMPLETE',input_scenarios=n,trials=sum(x['trials'] for x in parts),hourly_rows=sum(x['rows'] for x in parts),groups=len(parts),all_original_hourly_columns_preserved=True,ready_curves=len(curves),all_successes_and_failures_included=True))
    print('Complete inputs',n,flush=True)

if __name__=='__main__':main()
