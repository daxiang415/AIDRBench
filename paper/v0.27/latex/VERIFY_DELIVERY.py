"""Verify portable current files and, when available, the full-data annex."""
import argparse, csv, hashlib
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--quick', action='store_true', help='Skip the large full-data annex')
args = parser.parse_args()
root = Path(__file__).resolve().parent
folders = [root]
if not args.quick and (root/'05_Full_Data/FILE_MANIFEST.csv').is_file():
    folders.append(root/'05_Full_Data')
count = 0
for folder in folders:
    for row in csv.DictReader((folder/'FILE_MANIFEST.csv').open()):
        path = folder/row['path']
        assert path.is_file() and path.stat().st_size == int(row['bytes']), path
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], path
        count += 1
print(f'PASS: {count} files checked; full-data annex ' +
      ('checked' if len(folders) == 2 else 'not included in this check'))
