"""Frozen structural tests starting from the corrected causal controller."""
from __future__ import annotations
import argparse
import copy
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / 'workload_composition_2026-09-09'))
sys.path.insert(0, str(HERE.parent / 'repeat_mechanism_2026-09-09'))
import run_study_final as m
from recovery_controller import AllWindowController

OUT = ROOT / 'results/nature_mainline/operating_tradeoffs_v1'
PROTOCOL = HERE / 'protocol.json'
REFERENCE = float(pd.read_csv(m.OUT / 'single_selected.csv').query('case == "f10" and duration_h == 8').iloc[0].capacity_kw)
VARIANTS = [dict(name=f'u{int(u*100)}d{int(d*100)}g10', utilization=u, slack_multiplier=d, gpu_share=.1) for u in [.5,.65,.8] for d in [.5,1.]]
VARIANTS += [dict(name=f'u{int(u*100)}d50g20', utilization=u, slack_multiplier=.5, gpu_share=.2) for u in [.65,.8]]
REFERENCE_VARIANT = 'u65d100g10'
CRITERIA_NAMES = ['mean_delivery','interval_delivery','deadline_miss','rebound','window_peak_relief','terminal_backlog']


def programs(variant):
    result = [dict(name='H8P16', h=8, period=16), dict(name='H8P24', h=8, period=24)]
    if variant == REFERENCE_VARIANT:
        result += [dict(name='H4P16', h=4, period=16)]
    return result


def starts(seed, period):
    phase = int(np.random.default_rng(seed + 12002609).integers(0,24))
    return [111 + phase - (3-i)*period for i in range(4)]


def scenario(role, variant, seed, program='H8P16'):
    return OUT / 'inputs' / role / variant / str(seed) / program / f'hourly_seed_{seed}'


def freeze_seed(payload):
    role, seed = payload
    root = OUT / 'inputs' / role / str(seed)
    root.mkdir(parents=True, exist_ok=True)
    doc, _ = m.make_document(.6, role, seed)
    env = m.HourlyCommunityAIDemandResponseEnv(doc)
    env.reset(seed=seed)
    template = env._arrivals.copy()
    case = m.case_definition(.1)
    for cls in ['training','offline_inference']:
        mask = template.job_class == cls
        template.loc[mask,'arrival_gpu_h'] *= (374.4*168*case['eligible_shares'][cls]/template.loc[mask,'arrival_gpu_h'].sum())
    template.to_parquet(root / 'template_f10.parquet', index=False)
    rows = []
    for v in VARIANTS:
        path = scenario(role,v['name'],seed)
        if (path/'baseline_receipt.json').exists():
            rows.append(json.loads((path/'baseline_receipt.json').read_text())); continue
        d, _ = m.make_document(.1,role,seed)
        u, g = v['utilization'],v['gpu_share']
        d['virtual_datacenter']['flexible_gpu_fraction'] = g
        d['virtual_datacenter']['rigid_gpu_utilization'] = 576*u*.9/(576-round(576*g))
        d['workload']['flexible_arrival_utilization'] = u*.1/g
        arrivals = template.copy()
        arrivals['arrival_gpu_h'] *= u/.65
        arrivals['slack_hours'] = np.maximum(1,np.floor(arrivals.slack_hours*v['slack_multiplier'])).astype(int)
        arrivals['source_mode'] = 'f10_structural_utilization_and_deadline_intervention'
        input_path = root / f'{v["name"]}_arrivals.parquet'
        arrivals.to_parquet(input_path,index=False)
        d['workload']['arrivals_path'] = str(input_path)
        for key in ['event_start_hour_choices','event_duration_choices','event_notice_choices','event_reduction_fraction_range']:
            d['dr'].pop(key,None)
        d['dr'].update(source='configured',events_path=None,event_start_hours=starts(seed,16),event_duration_hours=8,event_notice_hours=0,event_reduction_kw=1.,event_start_jitter_hours=0)
        if not path.exists(): m.freeze_hourly_scenario(d,seed=seed,output_directory=path.parent)
        parent = m.load_frozen_hourly_scenario(path)
        assert np.isclose(parent.arrivals.arrival_gpu_h.sum(),576*u*.1*168,atol=1e-7)
        baseline_doc = m._repeated_environment_document(parent,notice_h=0,requested_reduction_kw=0)
        baseline_env = m.HourlyCommunityAIDemandResponseEnv(baseline_doc)
        baseline, summary = m.rollout_hourly_episode(baseline_env,m.make_hourly_controller('no_control'),seed=seed)
        baseline = baseline.drop(columns=['controller_action_time_ms'])
        baseline.to_parquet(path/'no_response_full.parquet',index=False)
        missed = float(baseline.missed_gpu_h.sum())
        receipt = dict(role=role,seed=seed,**v,baseline_missed_gpu_h=missed,baseline_miss_rate=float(summary['deadline_miss_rate']),
            baseline_service_feasible=m.baseline_service_gate(baseline,float(summary['deadline_miss_rate']),baseline_env.config.pcc_capacity_kw),
            baseline_zero_service=missed<=1e-7,operating_peak_kw=baseline_env.power_model.reference_mix_operating_peak_kw,
            flexible_gpu_count=round(576*g),scenario_hash=parent.scenario_hash,phase=starts(seed,16)[-1]-111,
            total_arrival_gpu_h=float(parent.arrivals.arrival_gpu_h.sum()),source=str(path),baseline_sha256=m.sha(path/'no_response_full.parquet'))
        m.save(path/'baseline_receipt.json',receipt)
        for p in programs(v['name']):
            dest = scenario(role,v['name'],seed,p['name'])
            if dest == path: continue
            dest.mkdir(parents=True,exist_ok=True)
            meta = copy.deepcopy(parent.metadata)
            for name in meta['files']: shutil.copyfile(path/name,dest/name)
            meta['events'] = [dict(event_id=i,source_event_id=f'tradeoff_{i}',start_hour=s,stop_hour=s+p['h'],requested_reduction_kw=1.,notice_hours=0.) for i,s in enumerate(starts(seed,p['period']))]
            meta.pop('scenario_hash');meta['scenario_hash']=m.digest(meta)
            m.save(dest/'metadata.json',meta)
            child = m.load_frozen_hourly_scenario(dest)
            for name in ['arrivals.parquet','community.parquet','baseline.parquet']: assert child.metadata['files'][name] == parent.metadata['files'][name]
        rows.append(receipt)
    return rows


def score(events, frame, baseline_receipt):
    failures = {f for e in events for f in e.success(m.CRITERIA)[1]}
    missed = float(frame.missed_gpu_h.sum())
    electrical = not (failures-{'deadline_miss'})
    return dict(success_1pct=not failures and baseline_receipt['baseline_service_feasible'],
        success_zero=electrical and missed<=1e-7 and baseline_receipt['baseline_zero_service'] and baseline_receipt['baseline_service_feasible'],
        success_01pct=electrical and missed/max(float(frame.arrival_gpu_h.sum()),1e-12)<=.001+1e-9 and baseline_receipt['baseline_miss_rate']<=.001+1e-9 and baseline_receipt['baseline_service_feasible'],
        missed_gpu_h=missed,miss_rate=missed/max(float(frame.arrival_gpu_h.sum()),1e-12),
        **{f'failure_{f}': f in failures for f in CRITERIA_NAMES})


def evaluate(task):
    role,variant,seed,program = [task[k] for k in ['role','variant','seed','program']]
    folder = OUT / 'runs' / role / variant / program
    path = folder/f'{task["kind"]}_f{task["fraction"]}_{seed}.json'
    identity = m.digest(dict(task=task,protocol_sha256=m.sha(PROTOCOL) if PROTOCOL.exists() else 'pilot',runner_sha256=m.sha(__file__)))
    if path.exists():
        result=json.loads(path.read_text()); assert result['identity']==identity; assert m.sha(result['trace_path'])==result['trace_sha256']; return result
    a = m.load_frozen_hourly_scenario(scenario(role,variant,seed,program))
    bpath = scenario(role,variant,seed)
    receipt = json.loads((bpath/'baseline_receipt.json').read_text())
    baseline = pd.read_parquet(bpath/'no_response_full.parquet')
    p = next(p for p in programs(variant) if p['name']==program)
    capacity = REFERENCE*task['fraction']
    d = m._repeated_environment_document(a,notice_h=0,requested_reduction_kw=capacity,event_ids=[3] if task['kind']=='fresh' else None)
    d['dr']['event_duration_hours'] = p['h']
    env = m.HourlyCommunityAIDemandResponseEnv(d)
    proposer = m.make_hourly_controller('robust_mpc',robust_mpc_specification=m.load_robust_mpc_specification(m.CONTROLLER))
    controller = AllWindowController(proposer)
    frame,_ = m.rollout_hourly_episode(env,controller,seed=seed)
    frame=frame.drop(columns=['controller_action_time_ms'])
    outcomes=m.derive_event_outcomes(frame,env.event_manifest,recovery_tolerance_gpu_h=env.config.recovery_backlog_tolerance_fraction*env.power_model.flexible_capacity_gpu_h)
    assert all(e.start_hour+e.duration_h+24<=168 for e in outcomes)
    assert [e.start_hour for e in outcomes] == (starts(seed,p['period'])[-1:] if task['kind']=='fresh' else starts(seed,p['period']))
    active = frame.event_active
    reducible = frame.baseline_pcc_power_kw-frame.community_power_kw-env.power_model.predict_by_class({}).dc_power_kw
    necessary_shortfall = np.maximum(.95*capacity-reducible[active].to_numpy(),0.)
    row = dict(**task,capacity_kw=capacity,operating_peak_kw=receipt['operating_peak_kw'],phase=receipt['phase'],
        **score(outcomes,frame,receipt),baseline_service_feasible=receipt['baseline_service_feasible'],baseline_zero_service=receipt['baseline_zero_service'],
        instantaneous_supply_shortfall_hours=int((necessary_shortfall>1e-7).sum()),max_instantaneous_supply_shortfall_kw=float(necessary_shortfall.max()),
        **m.series_ledger(frame,baseline,capacity,outcomes[0].start_hour),
        guard_hours=sum(x['additional_cap_active'] for x in controller.audit),overlap_guard_hours=sum(x['additional_cap_active'] and x['observed_active_windows']>1 for x in controller.audit))
    events=[asdict(e)|dict(failures=list(e.success(m.CRITERIA)[1])) for e in outcomes]
    folder.mkdir(parents=True,exist_ok=True)
    trace=path.with_suffix('.parquet');frame.to_parquet(trace,index=False)
    result=dict(identity=identity,row=row,events=events,trace_path=str(trace),trace_sha256=m.sha(trace),scenario_path=str(a.directory),scenario_hash=a.scenario_hash,controller_audit=controller.audit)
    m.save(path,result)
    return result


def tasks_for(role,seeds):
    tasks=[]
    for seed in seeds:
        for v in VARIANTS:
            for p in programs(v['name']):
                for f in [.25,.5,.75,1.]:
                    tasks.append(dict(role=role,variant=v['name'],seed=seed,program=p['name'],fraction=f,kind='repeated'))
            tasks.append(dict(role=role,variant=v['name'],seed=seed,program='H8P16',fraction=1.,kind='fresh'))
    return tasks


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['pilot','freeze_protocol','development','confirmation']);ap.add_argument('--workers',type=int,default=40);args=ap.parse_args()
    if args.stage=='freeze_protocol':
        assert not PROTOCOL.exists()
        protocol=dict(status='posthoc_design_with_new_prospective_confirmation',parent_version='0.22',variants=VARIANTS,
            development_seeds=[984000,984099],confirmation_seeds=[985000,985299],pilot_seeds=[984998,984999],
            reference_capacity_kw=REFERENCE,fractions=[.25,.5,.75,1.],programs={v['name']:programs(v['name']) for v in VARIANTS},
            controller='unchanged all-window MPC from v0.21',selection_criteria=['success_1pct','success_zero'],
            selection='largest grid offer with one-sided Wilson95 >= .95; baseline failures retained in denominator',
            zero_deadline_miss_gpu_h_tolerance=1e-7,other_criteria=asdict(m.CRITERIA),
            clock_design='same random target start 111+UniformInteger(0,23), four backward-spaced calls, matched target-only fresh control',
            inference='pointwise model-scenario qualification; earlier event clocks also move with period; no pure gap causation',
            design_sha256=m.sha(HERE/'DESIGN_ZH.md'),runner_sha256=m.sha(__file__),
            parent_controller_sha256=m.sha(HERE.parent/'repeat_mechanism_2026-09-09/recovery_controller.py'),
            economic_scope='new fee scenarios reuse full ledgers, all failures retained, no market profit claim',
            temporal_scope='8 observed 2020 weeks x 10 new synthetic realizations, no new source/SLA claim')
        m.save(PROTOCOL,protocol);print('Frozen protocol',m.sha(PROTOCOL));return
    if args.stage=='pilot':seeds=range(984998,985000);role='pilot';tasks=tasks_for(role,seeds)
    else:
        p=json.loads(PROTOCOL.read_text());assert p['runner_sha256']==m.sha(__file__)
        role=args.stage;first,last=p[role+'_seeds'];seeds=range(first,last+1)
        tasks=tasks_for(role,seeds) if role=='development' else json.loads((HERE/'selection.json').read_text())['confirmation_tasks']
    rows=m.parallel(freeze_seed,[(role,s) for s in seeds],args.workers,'freeze '+role)
    m.save(OUT/f'{role}_baseline_receipts.json',rows)
    results=m.parallel(evaluate,tasks,args.workers,role)
    data=pd.DataFrame([r['row'] for r in results]).sort_values(['variant','program','kind','fraction','seed'])
    data.to_csv(OUT/f'{role}_ledgers.csv',index=False)
    print(data.groupby(['variant','program','kind','fraction'])[['success_1pct','success_zero']].sum().to_string(),flush=True)


if __name__=='__main__':main()
