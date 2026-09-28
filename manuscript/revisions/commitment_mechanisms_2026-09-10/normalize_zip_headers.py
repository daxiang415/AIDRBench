"""Normalize conservative ZIP version hints; payloads and member names are unchanged.

Some inherited Info-ZIP entries have local extraction version 2.0 and central
version 4.5. Raising the local hint to the existing central hint prevents
zipnote warnings without rewriting, recompressing or weakening ZIP64 metadata.
Run only after the archive builder has completed, before handing off the file.
"""
import hashlib
import json
import struct
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = ROOT / 'results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    receipt_path = HERE / 'package_validation.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'PASS'
    assert digest(ARCHIVE) == receipt['sha256']
    old_digest = receipt['sha256']
    changes = []
    with zipfile.ZipFile(ARCHIVE) as archive, ARCHIVE.open('r+b') as stream:
        members = archive.infolist()
        for member in members:
            stream.seek(member.header_offset)
            header = stream.read(8)
            assert header[:4] == b'PK\x03\x04'
            local_version = struct.unpack_from('<H', header, 4)[0]
            if local_version != member.extract_version:
                assert local_version == 20 and member.extract_version == 45
                changes.append((member.header_offset + 4, member.extract_version))
        for offset, version in changes:
            stream.seek(offset)
            stream.write(struct.pack('<H', version))
    with zipfile.ZipFile(ARCHIVE) as archive, ARCHIVE.open('rb') as stream:
        assert len(archive.infolist()) == receipt['files']
        for member in archive.infolist():
            stream.seek(member.header_offset + 4)
            assert struct.unpack('<H', stream.read(2))[0] == member.extract_version
        assert archive.testzip() is None
    receipt.update(
        sha256=digest(ARCHIVE),
        extraction_version_hints_consistent=True,
        normalized_local_headers=len(changes),
        pre_header_normalization_sha256=old_digest,
        header_normalization_scope='Only local required-version fields raised from 20 to 45; member bytes and central directory unchanged; all CRCs checked again.',
    )
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    ARCHIVE.with_suffix('.zip.sha256').write_text(f'{receipt["sha256"]}  {ARCHIVE.name}\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
