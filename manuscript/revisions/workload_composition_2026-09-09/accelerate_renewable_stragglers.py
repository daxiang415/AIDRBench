"""Numerically equivalent HiGHS multi-starts for a frozen list of slow problems.

Never writes the original result cache. Only fully optimal eight-solve groups
are candidates for reconciliation; a time-limited incumbent is not accepted.
"""
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
import multiprocessing
from pathlib import Path
import time
import numpy as np
import run_study_final as m

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/'solver_acceleration_protocol.json'
OUT=m.OUT/'numerical_multistart'


def trial(task):
    import aidrbench.evaluation.renewable_integration as ri
    from aidrbench.evaluation.hosting_capacity import CommunityPortfolio
    case,seed,solver_seed=task;started=time.monotonic();stages=[]
    def solve(problem,allow_infeasible=False):
        remaining=600-(time.monotonic()-started)
        if remaining<=0:raise TimeoutError('Numerical attempt exceeded 600 seconds')
        options={'threads':1,'random_seed':solver_seed,'mip_rel_gap':1e-4,'mip_abs_gap':1e-6,'time_limit':remaining}
        problem.solve(solver='HIGHS',highs_options=options)
        info=problem.solver_stats.extra_stats
        row=dict(status=str(problem.status),mip=problem.is_mixed_integer(),
            gap=float(info.mip_gap) if np.isfinite(info.mip_gap) else None,
            nodes=int(info.mip_node_count),primal=float(info.objective_function_value),
            dual=float(info.mip_dual_bound) if np.isfinite(info.mip_dual_bound) else None)
        stages.append(row)
        if problem.status!='optimal':raise RuntimeError(f'Numerical attempt not optimal: {problem.status}')
        if row['mip']:
            assert row['gap']<=1e-4+1e-10 or abs(row['primal']-row['dual'])<=1e-6+1e-9,row
        return 'optimal'
    ri._solve=solve
    a=m.load_frozen_hourly_scenario(m.artifact_path('confirmation',case,seed));rows=[]
    try:
        for bess in [False,True]:
            port=CommunityPortfolio(pv_enabled=True,pv_rated_kw=500,bess_enabled=bess,
                bess_power_kw=100 if bess else 0,bess_energy_kwh=200 if bess else 0,bess_dispatch_mode='milp_exclusive')
            for operation in ['rigid','flexible']:
                for analysis in ['hosting','operation']:
                    options=dict(portfolio=port,dc_operation=operation,dc_scale_of_reference_mix=1.,max_deadline_miss_rate=0.)
                    value=ri.solve_curtailment_constrained_pv_hosting(a,maximum_pv_curtailment_fraction=.05,**options) if analysis=='hosting' else ri.solve_fixed_capacity_pv_operation(a,pv_rated_kw=500,**options)
                    row=dict(case=case,seed=seed,bess_enabled=bess,solver_random_seed=solver_seed,solver_threads=1,
                        numerical_acceleration_protocol_sha256=m.sha(PROTOCOL),scenario_hash=a.scenario_hash)
                    row.update(value.summary());rows.append(row)
        status='OPTIMAL_COMPLETE';error=None
    except Exception as exc:
        status='NOT_ACCEPTED';error=f'{type(exc).__name__}: {exc}'
    receipt=dict(status=status,case=case,seed=seed,solver_random_seed=solver_seed,
        elapsed_seconds=time.monotonic()-started,finished_unix=time.time(),stages=stages,error=error,rows=rows,
        protocol_sha256=m.sha(PROTOCOL),scenario_hash=a.scenario_hash)
    m.save(OUT/case/str(seed)/f'solver_seed_{solver_seed}.json',receipt)
    return {key:receipt[key] for key in ['status','case','seed','solver_random_seed','elapsed_seconds','error']}


if __name__=='__main__':
    protocol=json.loads(PROTOCOL.read_text());tasks=[(x['case'],x['seed'],r) for x in protocol['cases'] for r in protocol['solver_random_seeds']]
    with ProcessPoolExecutor(max_workers=16,mp_context=multiprocessing.get_context('spawn')) as pool:
        for future in as_completed([pool.submit(trial,t) for t in tasks]):print(json.dumps(future.result()),flush=True)
