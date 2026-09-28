"""Check the requested narrative corrections against source tables and readers."""
import hashlib
import json
import re
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE=ROOT/'manuscript/source_data/nature_commitment_narrative_v1'

def main():
    main=(ROOT/'manuscript/nature_communications_article.md').read_text()
    si=(ROOT/'manuscript/supplementary_information.md').read_text()
    title=re.search(r'^# (.+)',main,re.M)[1]
    assert re.search(r'^## (.+)',si,re.M)[1]==title
    narrative=main.split('## Abstract\n')[1].split('## Methods\n')[0]
    for phrase in ['earlier coarse-grid difference','replacing the coarse-grid value','earlier reference derating','63/80','PI tolerance lower bounds']:
        assert phrase not in narrative,phrase
    assert 'PI tolerance lower bounds' not in main
    assert 'PI tolerance lower bounds' not in (ROOT/'docs/nature-mainline-figure-preview.md').read_text()
    assert '### 7. Design provenance' in si
    assert 'Fig. 3c displays the primary pair' not in si
    assert 'Supplementary Fig. 3d displays the chronological primary requests' in si
    guide=si.split('## Reader guide\n')[1].split('## Supplementary Notes\n')[0]
    for n in [18,19,20,21]:assert f'Table {n}' in guide
    for text,prefix,n in [(main,'Figure',6),(si,'Supplementary Figure',5)]:
        assert [int(x) for x in re.findall(rf'^### {prefix} (\d+) \|',text,re.M)]==list(range(1,n+1))
        assert len(re.findall(rf'^!\[{prefix} \d+\]',text,re.M))==n
    assert [int(x) for x in re.findall(r'^### Supplementary Table (\d+) \|',si,re.M)]==list(range(1,22))
    for stem,doc in [('main',main),('supplement',si)]:
        p=ROOT/f'docs/chinese_reader/v19/{stem}_aligned_blocks.json';d=json.loads(p.read_text())
        assert d['source_sha256']==hashlib.sha256(doc.encode()).hexdigest()
        assert all(b['en'].strip() and b['zh'].strip() for b in d['blocks'])
        restored='\n\n'.join(b['en'] for b in d['blocks'])+'\n'
        assert re.sub(r'<!--.*?-->\s*','',doc,count=1,flags=re.S)==restored
        for path in re.findall(r'!\[[^]]*\]\(([^)]+)\)',doc):assert (ROOT/'manuscript'/path).resolve().is_file()
    summary=pd.read_csv(SOURCE/'timing_cross_summary.csv').query('fraction == 0.5').set_index(['weight','ordering'])
    expected={('job_count','chronological'):(80,80,0),('job_count','permuted'):(80,80,0),('resource_gpu_h','chronological'):(31,31,49),('resource_gpu_h','permuted'):(55,54,25)}
    for key,values in expected.items():assert tuple(summary.loc[key,['successes_1pct','successes_zero','instantaneous_shortage']])==values
    full=pd.read_csv(SOURCE/'supply_margin_trials.csv');assert len(full)==640
    p=full.query("fraction == 0.5 and weight == 'resource_gpu_h' and ordering == 'permuted'")
    assert ((p.shortage_hours==0)&(~p.success_zero)).sum()==1
    assert (p.shortage_hours==0).sum()==55
    pairs=pd.read_csv(SOURCE/'paired_resource_supply_margins.csv');assert len(pairs)==80
    assert ((pairs.chronological<0)&(pairs.permuted>=0)).sum()==29
    assert ((pairs.chronological>=0)&(pairs.permuted<0)).sum()==5
    assert not (pairs[['chronological','permuted']].abs()<1e-7).any().any()
    maps=pd.read_csv(SOURCE/'PANEL_DATA_MAP.csv');assert len(maps)==15
    for t in maps.table:assert (SOURCE/t).is_file()
    previous=ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1'
    for name in ['refinement_protocol.json','refinement_selection.json','pi_protocol.json','workload_protocol.json']:
        assert (previous/name).read_bytes()==(ROOT/'results/exports/AIDRBench_Figures_v13/03_data/commitment_mechanisms'/name).read_bytes()
    result=dict(status='PASS',title_unified=True,requested_old_phrases_removed=True,table_navigation_18_to_21=True,zero_miss_and_probability_distinguished=True,english_chinese_blocks_match=True,main_figures=6,supplementary_figures=5,supplementary_tables=21,timing_cross_counts_verified=True,paired_shortage_removed=29,paired_shortage_created=5,all_frozen_protocols_unchanged=True,new_simulations=0)
    (HERE/'text_and_evidence_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
