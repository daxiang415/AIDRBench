"""Resume only cached control renewable tasks using the unchanged frozen solver."""
import argparse
import json
import pandas as pd
import run_study_final as m


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=48);a=ap.parse_args()
    spec=json.loads((m.HERE/'secondary_protocol_final.json').read_text())
    tasks=[(c['name'],s) for c in spec['controls'] for s in range(960000,960100)]
    rows=m.parallel(m.renewable_task,tasks,a.workers,'controls renewable resume')
    frame=pd.DataFrame([r for block in rows for r in block]);assert len(frame)==3200
    frame.to_csv(m.SOURCE/'control_renewable_scenarios.csv',index=False)
