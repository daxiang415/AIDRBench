"""Replay one delivered scenario without raw third-party trace preprocessing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
for path in [HERE.parent/'aidrbench_project/src',HERE.parent,HERE.parent/'workload_composition_2026-09-09']:
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
    ap.add_argument('--role',default='confirmation');ap.add_argument('--case',default='f10');ap.add_argument('--seed',type=int,default=970000)
    ap.add_argument('--program',default='H8G12');ap.add_argument('--controller',default='all_window_mpc');ap.add_argument('--fraction',type=float,default=.75)
    ap.add_argument('--controller-config',type=Path,required=True);a=ap.parse_args()
    table=pd.read_csv(a.data/f'{a.role}_ledgers.csv')
    match=table[(table.case==a.case)&(table.seed==a.seed)&(table.program==a.program)&(table.controller==a.controller)&np.isclose(table.fraction,a.fraction)]
    assert len(match)==1;row=match.iloc[0]
    src=a.data/'recovery_inputs'/a.role/a.case/str(a.seed);dest=a.output/'scenario'
    assert not dest.exists(),'Use a new output folder'
    shutil.copytree(src,dest)
    meta=json.loads((dest/'metadata.json').read_text());h=int(row.duration_h);g=int(row.gap_h)
    meta['events']=[dict(event_id=i,source_event_id=f'mix_repeat_{i}',start_hour=63+i*(h+g),stop_hour=63+i*(h+g)+h,
        requested_reduction_kw=1.,notice_hours=0.) for i in range(4)]
    meta.pop('scenario_hash')
    meta['scenario_hash']=hashlib.sha256(json.dumps(meta,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert meta['scenario_hash']==row.scenario_hash
    (dest/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    artifact=load_frozen_hourly_scenario(dest)
    d=_repeated_environment_document(artifact,notice_h=0,requested_reduction_kw=float(row.capacity_kw));d['dr']['event_duration_hours']=h
    env=HourlyCommunityAIDemandResponseEnv(d)
    original=make_study_controller('robust_mpc',robust_mpc_specification=load_robust_mpc_specification(a.controller_config))
    controller=original if a.controller=='original' else AllWindowController(original if a.controller=='all_window_mpc' else None)
    frame,_=rollout_hourly_episode(env,controller,seed=a.seed);frame=frame.drop(columns=['controller_action_time_ms'])
    frame.to_parquet(a.output/'replayed.parquet',index=False)
    index=pd.read_csv(a.data/'hourly_partition_index.csv')
    group=index[(index.role==a.role)&(index.case==a.case)&(index.program==a.program)&(index.controller==a.controller)&np.isclose(index.fraction,a.fraction)]
    assert len(group)==1
    expected=pd.read_parquet(a.data/group.iloc[0].full_parquet,filters=[('scenario_seed','=',a.seed)])
    numeric=list(frame.select_dtypes(include=['number','bool']).columns)
    errors={}
    for col in numeric:
        actual=frame[col].to_numpy().astype(float);reference=expected[col].to_numpy().astype(float)
        assert np.array_equal(np.isnan(actual),np.isnan(reference)),(col,'missing-value mask')
        finite=np.isfinite(actual)&np.isfinite(reference)
        assert np.array_equal(np.isinf(actual),np.isinf(reference)),(col,'infinity mask')
        errors[col]=float(np.max(np.abs(actual[finite]-reference[finite]))) if finite.any() else 0.
    assert all(val<=1e-9 for val in errors.values()),errors
    (a.output/'replay_validation.json').write_text(json.dumps(dict(status='PASS',rows=len(frame),numeric_columns=len(numeric),
        max_absolute_error=max(errors.values()),scenario_hash=meta['scenario_hash'],source='delivered frozen inputs and code',
        simulator_source=str(Path(aidrbench.__file__).resolve()),controller_source=str(Path(sys.modules['recovery_controller'].__file__).resolve()),
        missing_value_masks_match=True),indent=2)+'\n')
    print('PASS',len(frame),'hours;',len(numeric),'numeric columns;',max(errors.values()),'maximum error')


if __name__=='__main__':main()
