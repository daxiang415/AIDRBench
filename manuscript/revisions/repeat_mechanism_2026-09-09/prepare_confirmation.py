"""Prepare independent inputs only; no controller execution or offer selection."""
import run_extension as x


def prepare_one(item):
    case,seed=item
    parent=x.m.load_frozen_hourly_scenario(x.source_artifact('confirmation',case,seed))
    rows=[]
    for h,g in [(4,8),(8,8),(8,12),(8,16)]:
        path=x.OUT/'programs'/'confirmation'/case/f'H{h}G{g}'/f'hourly_seed_{seed}'
        a=x.m.clone_program(parent,path,h,g)
        rows.append(dict(case=case,seed=seed,program=f'H{h}G{g}',scenario_hash=a.scenario_hash))
    return rows


if __name__=='__main__':
    x.m.parallel(prepare_one,[(c,s) for c in ['f05','f10','f20','f40','f60'] for s in range(970000,970300)],16,'prepare confirmation inputs')
