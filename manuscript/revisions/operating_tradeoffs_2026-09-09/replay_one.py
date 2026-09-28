"""Replay any delivered structural/timing case directly, without production preprocessing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
for path in [HERE.parent/'aidrbench_project/src',HERE.parent,HERE.parent/'repeat_mechanism']:
    if path.exists():sys.path.insert(0,str(path))
import numpy as np
import pandas as pd
import aidrbench
from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario
from aidrbench.evaluation.exhaustion import _repeated_environment_document
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode
from study_controller_v4 import make_study_controller
from recovery_controller import AllWindowController

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--role',default='confirmation');ap.add_argument('--variant',default='u65d100g10');ap.add_argument('--seed',type=int,default=985000)
    ap.add_argument('--program',default='H8P16');ap.add_argument('--kind',default='repeated');ap.add_argument('--fraction',type=float,default=.5)
    ap.add_argument('--controller-config',type=Path,default=HERE.parent/'aidrbench_project/configs/controller/nature_robust_mpc_v1.yaml');a=ap.parse_args()
    table=pd.read_csv(a.data/f'{a.role}_ledgers.csv')
    match=table[(table.variant==a.variant)&(table.seed==a.seed)&(table.program==a.program)&(table.kind==a.kind)&np.isclose(table.fraction,a.fraction)]
    assert len(match)==1,'Specify one of the delivered trials';row=match.iloc[0]
    src=a.data/'recovery_inputs'/a.role/a.variant/str(a.seed);dest=a.output/'scenario';assert not dest.exists(),'Use a new output directory'
    shutil.copytree(src,dest);meta=json.loads((dest/'metadata.json').read_text());h=int(a.program.split('P')[0][1:]);period=int(a.program.split('P')[1])
    if a.program!='H8P16':
        phase=int(np.random.default_rng(a.seed+12002609).integers(0,24));starts=[111+phase-(3-i)*period for i in range(4)]
        tag='temporal' if a.role=='temporal' else 'tradeoff'
        meta['events']=[dict(event_id=i,source_event_id=f'{tag}_{i}',start_hour=s,stop_hour=s+h,requested_reduction_kw=1.,notice_hours=0.) for i,s in enumerate(starts)]
        meta.pop('scenario_hash');meta['scenario_hash']=hashlib.sha256(json.dumps(meta,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        (dest/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    assert meta['scenario_hash']==row.scenario_hash
    artifact=load_frozen_hourly_scenario(dest)
    d=_repeated_environment_document(artifact,notice_h=0,requested_reduction_kw=float(row.capacity_kw),event_ids=[3] if a.kind=='fresh' else None);d['dr']['event_duration_hours']=h
    env=HourlyCommunityAIDemandResponseEnv(d)
    proposer=make_study_controller('robust_mpc',robust_mpc_specification=load_robust_mpc_specification(a.controller_config))
    frame,_=rollout_hourly_episode(env,AllWindowController(proposer),seed=a.seed);frame=frame.drop(columns=['controller_action_time_ms']);frame.to_parquet(a.output/'replayed.parquet',index=False)
    index=pd.read_csv(a.data/'hourly_partition_index.csv');group=index[(index.role==a.role)&(index.variant==a.variant)&(index.program==a.program)&(index.kind==a.kind)&np.isclose(index.fraction,a.fraction)];assert len(group)==1
    expected=pd.read_parquet(a.data/group.iloc[0].full_parquet,filters=[('scenario_seed','=',a.seed)])
    numeric=list(frame.select_dtypes(include=['number','bool']).columns);errors={}
    for col in numeric:
        actual=frame[col].to_numpy().astype(float);reference=expected[col].to_numpy().astype(float)
        assert np.array_equal(np.isnan(actual),np.isnan(reference)),(col,'NaN mask')
        assert np.array_equal(np.isposinf(actual),np.isposinf(reference)) and np.array_equal(np.isneginf(actual),np.isneginf(reference)),(col,'infinite mask')
        finite=np.isfinite(actual)&np.isfinite(reference);errors[col]=float(np.max(np.abs(actual[finite]-reference[finite]))) if finite.any() else 0.
    assert len(frame)==216 and max(errors.values())<=1e-9,errors
    result=dict(status='PASS',role=a.role,variant=a.variant,program=a.program,kind=a.kind,fraction=a.fraction,seed=a.seed,rows=len(frame),numeric_columns=len(numeric),
        max_absolute_error=max(errors.values()),missing_value_masks_match=True,scenario_hash=meta['scenario_hash'],
        simulator_source=str(Path(aidrbench.__file__).resolve()),controller_source=str(Path(sys.modules['recovery_controller'].__file__).resolve()))
    (a.output/'replay_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
