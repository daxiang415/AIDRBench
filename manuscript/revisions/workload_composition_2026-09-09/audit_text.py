"""Check current bilingual source alignment, figure references and release scope."""
import hashlib
import json
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];READER=ROOT/'docs/chinese_reader/v14'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    reports={}
    for stem,name,nfig in [('main','nature_communications_article.md',6),('supplement','supplementary_information.md',5)]:
        source=ROOT/'manuscript'/name;document=source.read_text();aligned=json.loads((READER/f'{stem}_aligned_blocks.json').read_text())
        assert aligned['source_sha256']==sha(source)
        assert (READER/'sources'/f'{stem}_original.md').read_bytes()==source.read_bytes()
        body=re.sub(r'^<!--.*?-->\s*','',document,flags=re.S)
        assert body=='\n\n'.join(r['en'] for r in aligned['blocks'])+'\n'
        assert len({r['id'] for r in aligned['blocks']})==len(aligned['blocks'])
        assert all(r['en'].strip() and r['zh'].strip() for r in aligned['blocks'])
        assert not re.search(r'[\u4e00-\u9fff]',body), 'Chinese text leaked into English source'
        images=re.findall(r'!\[([^]]+)\]\(([^)]+)\)',body);assert len(images)==nfig,(stem,len(images))
        for alt,path in images:
            p=(source.parent/path).resolve();assert p.is_file()
            assert 'workload_composition_v1' in str(p)
        tag='Figure' if stem=='main' else 'Supplementary Figure'
        headings=re.findall(rf'^### {tag} (\d+) \|',body,re.M)
        assert headings==[str(i) for i in range(1,nfig+1)]
        if stem=='supplement':
            tables=re.findall(r'^### Supplementary Table (\d+) \|',body,re.M)
            assert tables==[str(i) for i in range(1,10)]
        else:
            resultbody=body.split('## Results\n',1)[1].split('## Discussion\n',1)[0]
            assert len(re.findall(r'^### ',resultbody,re.M))==6
            for old in ['201.00-kW','39.65-kW','36.71-kW','75% of work was deferrable','nine of ten tested schedules']:
                assert old not in resultbody,old
            refs=body.split('## References\n',1)[1].split('\n## ',1)[0]
            numbers=[int(n) for n in re.findall(r'^(\d+)\. ',refs,re.M)];assert numbers==list(range(1,41))
            for n in re.findall(r'Supplementary Table (\d+)',body):assert 1<=int(n)<=9
        for r in aligned['blocks']:
            if r['en'].startswith('\\['):assert r['en']==r['zh'],r['id']
        words=len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",body))
        reports[stem]=dict(status='PASS',source_sha256=sha(source),aligned_blocks=len(aligned['blocks']),figures=nfig,tables=9 if stem=='supplement' else 0,english_words_including_captions_tables_references=words)
    (HERE/'text_audit.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))

if __name__=='__main__':main()
