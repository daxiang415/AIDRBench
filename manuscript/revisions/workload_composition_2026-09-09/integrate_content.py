"""Integrate evidence-driven edits while preserving paragraph-aligned Chinese readers."""

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
READER = ROOT / "docs/chinese_reader/v14"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reader_format(value):
    def convert(m):
        path = Path(m.group(2))
        path = path if path.is_absolute() else (ROOT / "manuscript" / path).resolve()
        assert path.is_file(), path
        return f"![{m.group(1)}]({path})"

    return (
        re.sub(r"!\[([^]]*)\]\(([^)]+)\)", convert, value)
        .replace("\\[", "$$")
        .replace("\\]", "$$")
        .replace("\\(", "$")
        .replace("\\)", "$")
    )


def renumber_references(rows):
    """Retain every cited work, numbering it by first appearance after revision."""
    def decode(raw):
        if not re.fullmatch(r'\d+(?:[–,-]\d+)*',raw):return None
        values=[]
        for term in raw.split(','):
            ends=re.split('[–-]',term)
            values.extend(range(int(ends[0]),int(ends[-1])+1))
        return values
    order=[]
    for row in rows:
        for raw in re.findall(r'<sup>(.*?)</sup>',row['en']):
            for n in decode(raw) or []:
                if n not in order:order.append(n)
    reference_start=next(i for i,r in enumerate(rows) if r['en']=='## References')+1
    reference_end=next((i for i in range(reference_start,len(rows)) if rows[i]['en'].startswith('## ')),len(rows))
    refs={int(re.match(r'(\d+)\.',r['en'])[1]):r for r in rows[reference_start:reference_end]}
    assert set(order)<=set(refs)
    order.extend(n for n in refs if n not in order)
    mapping={old:new for new,old in enumerate(order,1)}
    def encode(values):
        values=sorted(set(values));parts=[];i=0
        while i<len(values):
            j=i
            while j+1<len(values) and values[j+1]==values[j]+1:j+=1
            if j-i>=2:parts.append(f'{values[i]}–{values[j]}')
            else:parts.extend(str(x) for x in values[i:j+1])
            i=j+1
        return ','.join(parts)
    def replace(match):
        vals=decode(match[1])
        return '<sup>'+encode([mapping[n] for n in vals])+'</sup>' if vals else match[0]
    for r in rows:
        for lang in ['en','zh']:r[lang]=re.sub(r'<sup>(.*?)</sup>',replace,r[lang])
    newrefs=[]
    for old in order:
        r=refs[old]
        for lang in ['en','zh']:r[lang]=re.sub(r'^\d+\.',str(mapping[old])+'.',r[lang])
        newrefs.append(r)
    rows[reference_start:reference_end]=newrefs
    (HERE/'reference_number_map.json').write_text(json.dumps(mapping,indent=2)+'\n')
    return rows


def main():
    results = json.loads((HERE / "edits.json").read_text())
    edits = results["replace"]
    after = results.get("after", {})
    (READER / "sources").mkdir(parents=True, exist_ok=True)
    changes = []
    report = {}
    for stem, filename in [
        ("main", "nature_communications_article.md"),
        ("supplement", "supplementary_information.md"),
    ]:
        old = json.loads((HERE / f"before/reader_v13/{stem}_aligned_blocks.json").read_text())
        assert old["source_sha256"] == sha(HERE / "before" / filename)
        rows = []
        for row in old["blocks"]:
            if row["id"] in results.get("delete", []):
                continue
            revised = dict(row)
            if row["id"] in edits:
                revised.update(edits[row["id"]])
                changes.append(dict(id=row["id"], old=row, new=revised))
            rows.append(revised)
            rows.extend(after.get(row["id"], []))
        rows.extend(results.get("append", {}).get(stem, []))
        if stem in results.get("new_blocks", {}):
            rows=results["new_blocks"][stem]
        expanded = []
        for row in rows:
            ens, zhs = row["en"].split("\n\n"), row["zh"].split("\n\n")
            assert len(ens) == len(zhs), (row["id"], len(ens), len(zhs))
            for n, (en, zh) in enumerate(zip(ens, zhs, strict=True)):
                expanded.append(
                    dict(row, id=row["id"] if n == 0 else row["id"] + f"_r{n + 1}", en=en, zh=zh)
                )
        rows = expanded
        if stem=='main':rows=renumber_references(rows)
        assert len({row["id"] for row in rows}) == len(rows)
        header = (
            "<!--\nWorking "
            + ("manuscript" if stem == "main" else "Supplementary Information")
            + ", version 0.20, 2026-09-09.\nInference-led workload composition and complete five-scenario downstream recalculation.\nSix new data-driven review figures; historical evidence archived separately; author metadata pending.\n-->\n\n"
        )
        text = header + "\n\n".join(row["en"] for row in rows) + "\n"
        path = ROOT / "manuscript" / filename
        path.write_text(text)
        (READER / "sources" / f"{stem}_original.md").write_text(text)
        note = "本版逐段对应正文与补充材料 v0.20（2026-09-09）。主体结果为 5%、10%、20%、40%、60% 工作资格的完整新计算；40% 和 60% 的额外假设明确标出。正文含六幅新数据审阅图，历史结果另行归档。\n\n"
        chinese = []
        bilingual = []
        for row in rows:
            en, zh = reader_format(row["en"]), reader_format(row["zh"])
            chinese.append(zh)
            if en.startswith(("![", "$$")):
                bilingual.append(zh)
            else:
                bilingual.extend([f"<!-- {row['id']} -->\n{en}", zh])
        (READER / f"{stem}_zh.md").write_text(note + "\n\n".join(chinese) + "\n")
        (READER / f"{stem}_bilingual.md").write_text(note + "\n\n".join(bilingual) + "\n")
        (READER / f"{stem}_aligned_blocks.json").write_text(
            json.dumps(dict(source_sha256=sha(path), blocks=rows), ensure_ascii=False, indent=2)
            + "\n"
        )
        report[stem] = dict(blocks=len(rows), source_sha256=sha(path))
    assert set(edits) == {c["id"] for c in changes}
    (HERE / "text_changes.json").write_text(
        json.dumps(changes, ensure_ascii=False, indent=2) + "\n"
    )
    (HERE / "reader_build.json").write_text(json.dumps(report, indent=2) + "\n")
    (READER / "README.md").write_text(
        "# 中文阅读稿 v14\n\n对应正文与补充材料 v0.20；五档工作资格的新计算、结果、方法和图注均逐段同步。六幅正文审阅图使用新数据，历史补充证据另行归档。\n\n- [正文中文全文](main_zh.md)\n- [补充材料中文全文](supplement_zh.md)\n- [正文中英对照](main_bilingual.md)\n- [补充材料中英对照](supplement_bilingual.md)\n\n本轮未启动子智能体；作者信息保持待定。\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
