"""Resumable mechanism extension; confirmation is gated by a frozen protocol."""
from __future__ import annotations
import argparse
import copy
from dataclasses import asdict
import json
from pathlib import Path
import sys
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREVIOUS=HERE.parent/'workload_composition_2026-09-09'
sys.path.insert(0,str(PREVIOUS))
import run_study_final as m
from recovery_controller import AllWindowController

OUT=ROOT/'results/nature_mainline/repeat_mechanism_v1'
PROTOCOL=HERE/'protocol.json'
BASEOUT=m.OUT


def capacity(case,h):
    d=pd.read_csv(BASEOUT/'single_selected.csv')
    return float(d[(d.case==case)&(d.duration_h==h)].iloc[0].capacity_kw)


def run_task(t):
    protocol_hash=m.sha(PROTOCOL) if PROTOCOL.exists() else 'exploratory_pilot'
    identity=m.digest(dict(task=t,protocol_sha256=protocol_hash,
        runner_sha256=m.sha(__file__),controller_sha256=m.sha(HERE/'recovery_controller.py')))
    path=OUT/t['role']/t['case']/f'{t["program"]}_{t["controller"]}_f{t["fraction"]}_{t["kind"]}_{t["seed"]}.json'
    if path.exists():
        r=json.loads(path.read_text());assert r['identity']==identity
        assert m.sha(r['trace_path'])==r['trace_sha256'];return r
    role=t.get('source_role',t['role'])
    parent=m.load_frozen_hourly_scenario(source_artifact(role,t['case'],t['seed']))
    h,g=t['duration_h'],t['gap_h']
    program_path=OUT/'programs'/role/t['case']/t['program']/f'hourly_seed_{t["seed"]}'
    a=m.load_frozen_hourly_scenario(program_path)
    # Runtime duration must agree with frozen event anchors.
    requested=capacity(t['case'],h)*t['fraction']
    ids=None if t['kind']=='repeated' else [int(t['kind'].replace('fresh',''))]
    d=m._repeated_environment_document(a,notice_h=0,requested_reduction_kw=requested,event_ids=ids)
    d['dr']['event_duration_hours']=h
    env=m.HourlyCommunityAIDemandResponseEnv(d)
    original=m.make_hourly_controller('robust_mpc',robust_mpc_specification=m.load_robust_mpc_specification(m.CONTROLLER))
    controller=original if t['controller']=='original' else AllWindowController(original if t['controller']=='all_window_mpc' else None)
    frame,_=m.rollout_hourly_episode(env,controller,seed=t['seed'])
    outcomes=m.derive_event_outcomes(frame,env.event_manifest,
        recovery_tolerance_gpu_h=env.config.recovery_backlog_tolerance_fraction*env.power_model.flexible_capacity_gpu_h)
    for eid,o in zip(range(4) if ids is None else ids,outcomes,strict=True):
        assert o.duration_h==h and o.start_hour==63+eid*(h+g)
        assert o.start_hour+h+24<=168, 'Every recovery must end during active arrivals'
    frame=frame.drop(columns=['controller_action_time_ms'])
    baseline=pd.read_parquet(parent.directory/'no_response_full.parquet')
    events=[asdict(o)|dict(success=o.success(m.CRITERIA)[0],failures=list(o.success(m.CRITERIA)[1])) for o in outcomes]
    path.parent.mkdir(parents=True,exist_ok=True)
    trace=path.with_suffix('.parquet');frame.to_parquet(trace,index=False)
    r=dict(identity=identity,task=t,capacity_kw=requested,scenario_hash=a.scenario_hash,
        environment_document=d,events=events,success=all(e['success'] for e in events),
        ledger=m.series_ledger(frame,baseline,requested,63),
        trace_path=str(trace),trace_sha256=m.sha(trace),
        controller_audit=getattr(controller,'audit',[]))
    m.save(path,r)
    return r


def source_artifact(role,case,seed):
    source=BASEOUT if role=='development' else OUT/'scenario_source'
    return source/role/case/'scenarios'/'single'/f'hourly_seed_{seed}'


def freeze_seed(payload):
    role,seed=payload
    previous=m.OUT
    m.OUT=OUT/'scenario_source'
    try:
        m.template_task((role,seed))
        return [m.freeze_task((f,role,seed)) for f in [.05,.1,.2,.4,.6]]
    finally:
        m.OUT=previous


def prepare_programs(tasks):
    keys=sorted({(t.get('source_role',t['role']),t['case'],t['seed'],t['duration_h'],t['gap_h']) for t in tasks})
    for role,case,seed,h,g in keys:
        parent=m.load_frozen_hourly_scenario(source_artifact(role,case,seed))
        path=OUT/'programs'/role/case/f'H{h}G{g}'/f'hourly_seed_{seed}'
        m.clone_program(parent,path,h,g)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['pilot','development','freeze_confirmation','confirmation'])
    ap.add_argument('--workers',type=int,default=24);args=ap.parse_args()
    if args.stage=='pilot':
        tasks=[dict(role='pilot',source_role='development',case='f10',seed=s,
            duration_h=h,gap_h=g,program=f'H{h}G{g}',controller=c,fraction=1.,kind='repeated')
            for s in range(930000,930004) for h,g in [(4,8),(8,8),(8,12),(8,16)]
            for c in ['original','all_window_mpc','all_window_greedy']]
    else:
        assert PROTOCOL.exists()
        p=json.loads(PROTOCOL.read_text())
        if args.stage=='freeze_confirmation':
            first,last=p['confirmation_seeds']
            rows=m.parallel(freeze_seed,[('confirmation',s) for s in range(first,last+1)],args.workers,args.stage)
            assert all(r['baseline_service_feasible'] for group in rows for r in group)
            m.save(OUT/'baseline_receipts.json',rows)
            return
        if args.stage=='confirmation':
            selection=json.loads((HERE/'selection.json').read_text())
            tasks=selection['confirmation_tasks']
        else:
            tasks=p[args.stage+'_tasks']
    prepare_programs(tasks)
    rows=m.parallel(run_task,tasks,args.workers,args.stage)
    records=[r['task']|dict(success=r['success'],capacity_kw=r['capacity_kw'],
        failures=','.join(sorted({f for e in r['events'] for f in e['failures']})),
        missed_gpu_h=r['ledger']['incremental_missed_gpu_h']) for r in rows]
    df=pd.DataFrame(records).sort_values(['case','program','controller','fraction','kind','seed'])
    df.to_csv(OUT/f'{args.stage}_outcomes.csv',index=False)
    print(df.groupby(['case','program','controller','fraction','kind']).agg(successes=('success','sum'),trials=('success','size'),missed_gpu_h=('missed_gpu_h','sum')).to_string(),flush=True)


if __name__=='__main__':main()
