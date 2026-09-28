"""Repeat-only correction: enforce and check actual call durations at runtime.

Single-event, PI, scenarios and renewable inputs from v4 remain unchanged.
The erroneous one-hour repeat diagnostics are preserved in the parent output.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import pandas as pd
import run_study_final as m

HERE=Path(__file__).resolve().parent
OUT=m.OUT/'repeat_duration_corrected_v1'
PROTOCOL=HERE/'repeat_duration_protocol.json'


def run_task(t):
    path=OUT/t['role']/t['case']/f'{t["program"]}_{t["tag"]}_{t["seed"]}.json'
    identity=m.digest(dict(task=t,protocol_sha256=m.sha(PROTOCOL)))
    if path.exists():
        r=json.loads(path.read_text());assert r['identity']==identity
        assert m.sha(r['trace_path'])==r['trace_sha256'];return r
    a=m.load_frozen_hourly_scenario(m.artifact_path(t['role'],t['case'],t['seed'],t['program']))
    d=m._repeated_environment_document(a,notice_h=0,requested_reduction_kw=t['capacity_kw'],event_ids=t.get('event_ids'))
    # Frozen event anchors supply starts; this environment resolves durations
    # from the dr config rather than from frozen metadata stop_hour.
    d['dr']['event_duration_hours']=t['duration_h']
    env=m.HourlyCommunityAIDemandResponseEnv(d)
    controller=m.make_hourly_controller('robust_mpc',robust_mpc_specification=m.load_robust_mpc_specification(m.CONTROLLER))
    frame,_=m.rollout_hourly_episode(env,controller,seed=t['seed'])
    outcomes=m.derive_event_outcomes(frame,env.event_manifest,recovery_tolerance_gpu_h=env.config.recovery_backlog_tolerance_fraction*env.power_model.flexible_capacity_gpu_h)
    assert len(outcomes)==len(t.get('event_ids',[0,1,2,3]))
    for o in outcomes:
        assert o.duration_h==t['duration_h'], (t,asdict(o))
        assert o.start_hour==63+o.event_id*(t['duration_h']+(8 if t['duration_h']==4 else 12))
    frame=frame.drop(columns=['controller_action_time_ms'])
    baseline=pd.read_parquet(m.artifact_path(t['role'],t['case'],t['seed'])/'no_response_full.parquet')
    events=[asdict(o)|dict(success=o.success(m.CRITERIA)[0],failures=list(o.success(m.CRITERIA)[1])) for o in outcomes]
    path.parent.mkdir(parents=True,exist_ok=True);trace=path.with_suffix('.parquet');frame.to_parquet(trace,index=False)
    r=dict(identity=identity,task=t,scenario_hash=a.scenario_hash,success=all(e['success'] for e in events),events=events,
        runtime_duration_verified=True,environment_document_sha256=m.digest(d),
        ledger=m.series_ledger(frame,baseline,t['capacity_kw'],outcomes[0].start_hour),trace_path=str(trace),trace_sha256=m.sha(trace))
    m.save(path,r);return r


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['repeat_dev','repeat_select','repeat_confirm']);ap.add_argument('--workers',type=int,default=32);a=ap.parse_args()
    if a.stage=='repeat_select':
        d=pd.read_csv(OUT/'repeat_dev_summary.csv');rows=[]
        for (c,h),g in d.groupby(['case','duration_h']):
            ok=g[g.qualified];rows.append(dict(case=c,duration_h=int(h),capacity_kw=float(ok.capacity_kw.max()) if len(ok) else 0.,development_source_sha256=m.sha(OUT/'repeat_dev_summary.csv')))
        pd.DataFrame(rows).to_csv(OUT/'repeat_selected.csv',index=False);print(pd.DataFrame(rows).to_string(index=False),flush=True);return
    dev=a.stage=='repeat_dev';role='development' if dev else 'confirmation';p=json.loads(PROTOCOL.read_text())
    start,stop=p[f'{role}_seeds'];tasks=[]
    for row in pd.read_csv(m.OUT/'single_selected.csv').to_dict('records'):
        c,h,k=row['case'],int(row['duration_h']),row['capacity_kw'];program=f'H{h}G{8 if h==4 else 12}'
        if dev:
            for frac in [.25,.5,.75,1.]:
                for seed in range(start,stop+1):tasks.append(dict(role=role,case=c,seed=seed,duration_h=h,program=program,capacity_kw=k*frac,tag=f'fraction{frac}'))
        else:
            sel=pd.read_csv(OUT/'repeat_selected.csv');chosen=float(sel[(sel.case==c)&(sel.duration_h==h)].iloc[0].capacity_kw)
            for seed in range(start,stop+1):
                tasks.append(dict(role=role,case=c,seed=seed,duration_h=h,program=program,capacity_kw=k,tag='single_offer_repeated'))
                if chosen>0 and abs(chosen-k)>1e-12:tasks.append(dict(role=role,case=c,seed=seed,duration_h=h,program=program,capacity_kw=chosen,tag='selected_repeat'))
                for eid in range(4):tasks.append(dict(role=role,case=c,seed=seed,duration_h=h,program=program,capacity_kw=k,tag=f'fresh{eid}',event_ids=[eid]))
    rows=m.parallel(run_task,tasks,a.workers,a.stage)
    m.summary(rows).to_csv(OUT/f'{a.stage}_summary.csv',index=False);m.save(OUT/f'{a.stage}_receipts.json',rows)

if __name__=='__main__':main()
