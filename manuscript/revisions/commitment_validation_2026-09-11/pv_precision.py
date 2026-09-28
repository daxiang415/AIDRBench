"""Strict repeat solves of unchanged PV inputs; preserve solver bounds and failures."""
from __future__ import annotations
import argparse,json,math,sys
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'workload_composition_2026-09-09'))
import run_study_final as m
import aidrbench.evaluation.renewable_integration as pv
OUT=ROOT/'results/nature_mainline/commitment_validation_v1/pv_precision'
SOURCE=ROOT/'manuscript/source_data/nature_commitment_validation_v1'
LOCK=HERE/'pv_precision_protocol.json'
OPTIONS=dict(threads=1,mip_rel_gap=1e-7,mip_abs_gap=1e-7,primal_feasibility_tolerance=1e-8,dual_feasibility_tolerance=1e-8,mip_feasibility_tolerance=1e-8,time_limit=120.)
RECEIPTS=[]

def strict_solve(problem,*,allow_infeasible=False):
    try:
        problem.solve(solver='HIGHS',highs_options=OPTIONS)
    finally:
        info=getattr(problem.solver_stats,'extra_stats',None)
        row=dict(stage=len(RECEIPTS)+1,status=str(problem.status),mixed_integer=bool(problem.is_mixed_integer()),objective=None if problem.value is None or not math.isfinite(problem.value) else float(problem.value))
        for key in ['mip_gap','mip_dual_bound','objective_function_value','max_primal_infeasibility','max_dual_infeasibility','num_primal_infeasibilities','num_dual_infeasibilities']:
            value=getattr(info,key,None)
            row[key]=value if value is not None and math.isfinite(value) else None
        RECEIPTS.append(row)
    status=str(problem.status)
    if status=='optimal':return status
    if allow_infeasible and status=='infeasible':return status
    raise RuntimeError('strict solve unresolved: '+status)

def run_task(task):
    case,seed,bess,operation,analysis=task
    path=OUT/f'{case}_{seed}_{int(bess)}_{operation}_{analysis}.json'
    identity=m.digest(dict(task=task,protocol_sha256=m.sha(LOCK)))
    if path.exists():
        result=json.loads(path.read_text());assert result['identity']==identity;return result
    RECEIPTS.clear();pv._solve=strict_solve
    artifact=m.load_frozen_hourly_scenario(m.artifact_path('confirmation',case,seed))
    port=m.CommunityPortfolio(pv_enabled=True,pv_rated_kw=500.,bess_enabled=bess,bess_power_kw=100. if bess else 0.,bess_energy_kwh=200. if bess else 0.,bess_dispatch_mode='milp_exclusive')
    row=dict(case=case,seed=seed,bess_enabled=bess,dc_operation=operation,analysis=analysis,scenario_hash=artifact.scenario_hash)
    try:
        opts=dict(portfolio=port,dc_operation=operation,dc_scale_of_reference_mix=1.,max_deadline_miss_rate=0.)
        result=(pv.solve_curtailment_constrained_pv_hosting(artifact,maximum_pv_curtailment_fraction=.05,**opts) if analysis=='pv_hosting' else pv.solve_fixed_capacity_pv_operation(artifact,pv_rated_kw=500.,**opts))
        row.update(result.summary() if result else dict(status='infeasible'))
        row['resolved']=result is not None
    except Exception as exc:
        row.update(resolved=False,status='unresolved',error=type(exc).__name__+': '+str(exc))
    record=dict(identity=identity,row=row,solves=list(RECEIPTS));m.save(path,record);return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','run']);ap.add_argument('--workers',type=int,default=16);args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
    if args.stage=='freeze':
        assert not LOCK.exists()
        tasks=[(case,s,b,o,a) for case in ['f10','f10_g20'] for s in range(960000,960100) for b in ([False,True] if case=='f10' else [False]) for o in ['rigid','flexible'] for a in (['pv_hosting','fixed_pv_operation'] if case=='f10' else ['pv_hosting'])]
        # Original control seeds may be non-contiguous; preserve exactly the published sample.
        idx=pd.read_csv(m.SOURCE/'control_renewable_scenarios.csv');seeds=sorted(idx.query("case=='f10_g20'").seed.unique())
        tasks=[t for t in tasks if t[0]=='f10']+[("f10_g20",int(s),False,o,'pv_hosting') for s in seeds for o in ['rigid','flexible']]
        assert len(seeds)==100
        m.save(LOCK,dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),runner_sha256=m.sha(__file__),model_sha256=m.sha(pv.__file__),options=OPTIONS,tasks=tasks,
            scope='same 100 paired primary inputs and same 100 GPU20 control inputs; no selection on outcome; unresolved solves retained; LP and MIP separated'))
        print('Frozen',len(tasks),flush=True);return
    p=json.loads(LOCK.read_text());assert p['runner_sha256']==m.sha(__file__) and p['model_sha256']==m.sha(pv.__file__)
    results=m.parallel(run_task,p['tasks'],args.workers,'strict PV')
    pd.DataFrame([x['row'] for x in results]).sort_values(['case','seed','bess_enabled','dc_operation','analysis']).to_csv(SOURCE/'pv_strict_results.csv',index=False)
    stages=[x['row']|s for x in results for s in x['solves']]
    pd.DataFrame(stages).to_csv(SOURCE/'pv_strict_solver_stages.csv',index=False)
    print(pd.DataFrame([x['row'] for x in results]).groupby(['case','bess_enabled','analysis']).resolved.agg(['sum','count']).to_string(),flush=True)
if __name__=='__main__':main()
