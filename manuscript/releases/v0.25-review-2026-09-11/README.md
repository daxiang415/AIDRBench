# Frozen review evidence: v0.25

Snapshot ID: **AIDRBench-v0.25-review-2026-09-11**. Scientific content: English main/SI v0.25, Chinese v19 and eleven current figures. This is a review freeze; final submission readiness remains blocked by unresolved author/declaration, licence and archival inputs. It does not imply completed external validation or journal acceptance.

The immutable GitHub scientific anchor is [`8c508b9ca13c26089e27ff1a0b36405cbbfa6280`](https://github.com/daxiang415/AIDRBench/commit/8c508b9ca13c26089e27ff1a0b36405cbbfa6280). The branch `codex/manuscript-v025` can receive later documentation-only commits; its changing head is not the identifier of this scientific snapshot.

[freeze.json](freeze.json) binds that commit to [files.csv](files.csv), the paper/SI/PDF/Chinese files, eleven figures, exact GitHub plotting code, compact study-method files, and included summary data. The complete local v14 package separately binds the full simulation code, raw/processed inputs, complete trajectories and all artwork formats. Its SHA-256 was recalculated on 2026-09-11:

```text
e7d2095b32e3ad8af8ca396d7260a494120e52357b52342c6b395c91785cb923
AIDRBench_All_Figures_2026-09-10_v14.zip
13,392,344,034 bytes; 56,521 members
```

The local package is not uploaded to GitHub. Its recorded full-member verification and matching whole-archive hash identify the complete recovery copy. The lightweight GitHub checkout supplies everything needed to redraw the eleven current figures, but not everything needed to rerun the full scientific studies.

From a checkout of the GitHub review branch, check the frozen evidence files:

```bash
python manuscript/releases/v0.25-review-2026-09-11/verify.py
```

If this record is stored elsewhere, pass `--root PATH_TO_GITHUB_CHECKOUT`. To verify the complete local archive as well, add `--archive PATH_TO_V14_ZIP`. Verification reads files without changing them. English Markdown/PDF identities are exact; Chinese and packaged Markdown image links differ by delivery location. The GitHub plotting code was formatted for lint and subsequently reproduced all eleven full-package PNGs exactly.

Future scientific changes require a new snapshot ID, commit and checks. Complete author inputs and archive/access arrangements before recording a separate final submission freeze. The [current readiness audit](../../submission-readiness.md) distinguishes those remaining tasks from the completed review freeze.
