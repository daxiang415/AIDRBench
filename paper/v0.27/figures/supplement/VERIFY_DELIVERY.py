"""Check every delivered file against the SHA-256 manifest (standard library only)."""
from pathlib import Path
import csv
import hashlib

root = Path(__file__).resolve().parent
failures = []
with (root/'FILE_MANIFEST.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
for row in rows:
    p = root/row['path']
    if not p.is_file():
        failures.append((row['path'], 'missing'))
    elif p.stat().st_size != int(row['bytes']) or hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
        failures.append((row['path'], 'changed'))
for file, reason in failures:
    print(reason, file)
print(f"{'FAIL' if failures else 'PASS'}: {len(rows)-len(failures)}/{len(rows)} files match the delivered originals.")
raise SystemExit(bool(failures))
