"""Verify the frozen v0.25 evidence in a GitHub checkout, optionally with its full ZIP."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=here.parents[2])
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    record = json.loads((here / 'freeze.json').read_text())
    manifest = here / record['files']['manifest']
    if digest(manifest) != record['files']['sha256']:
        raise SystemExit('The freeze file manifest has changed.')
    rows = list(csv.DictReader(manifest.open()))
    if len(rows) != record['files']['count']:
        raise SystemExit('The frozen file count has changed.')
    failures = []
    for row in rows:
        path = args.root / row['path']
        if not path.is_file():
            failures.append({'path': row['path'], 'error': 'missing'})
        elif path.stat().st_size != int(row['bytes']) or digest(path) != row['sha256']:
            failures.append({'path': row['path'], 'error': 'content differs'})
    if failures:
        raise SystemExit(json.dumps({'status': 'FAIL', 'files': failures}, indent=2))
    if args.archive:
        expected = record['complete_local_package']
        if (args.archive.stat().st_size != expected['bytes']
                or digest(args.archive) != expected['sha256']):
            raise SystemExit('The full archive differs from the frozen v14 package.')
    print(json.dumps({'status': 'PASS', 'frozen_files': len(rows),
                      'scientific_commit': record['git']['scientific_commit'],
                      'archive_checked': bool(args.archive),
                      'submission_readiness': record['submission_readiness']}, indent=2))


if __name__ == '__main__':
    main()
