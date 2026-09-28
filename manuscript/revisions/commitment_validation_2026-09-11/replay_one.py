"""Replay one frozen v0.27 capacity case without editing the original receipts."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'manuscript/revisions/commitment_validation_2026-09-11'))
import capacity_validation as c
import pandas as pd
import numpy as np

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--role',choices=['development','confirmation'],default='confirmation');ap.add_argument('--weight',choices=c.WEIGHTS,default='resource_gpu_h');ap.add_argument('--seed',type=int,default=1011000);ap.add_argument('--fraction',type=float,default=.25);ap.add_argument('--output',type=Path,default=ROOT/'REPLAY_OUTPUT');args=ap.parse_args()
    original=c.OUT;src=c.r.scenario(args.role,args.weight,args.seed);c.r.OUT=args.output.resolve()
    target=c.r.scenario(args.role,args.weight,args.seed);target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copytree(src,target)
    task=c.task(args.seed,args.role,args.weight,args.fraction);result=c.evaluate(task)
    source=pd.read_csv(ROOT/f'manuscript/source_data/nature_commitment_validation_v1/capacity_{args.role}_ledgers.csv')
    row=source[(source.variant==args.weight)&(source.seed==args.seed)&np.isclose(source.fraction,args.fraction)].iloc[0]
    fields=['success_1pct','success_zero','instantaneous_supply_shortfall_hours','delay_exposure_gpu_h_h','incremental_energy_kwh','missed_gpu_h']
    for key in fields:assert np.isclose(float(row[key]),float(result['row'][key]),atol=1e-7,rtol=1e-10),(key,row[key],result['row'][key])
    receipt=dict(status='PASS',task=task,numeric_fields_checked=fields,original_inputs_untouched=True,output=str(args.output.resolve()))
    (args.output/'replay_check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
