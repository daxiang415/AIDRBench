# Exact certificate-provenance fixtures

These two JSON files are byte-identical copies of the frozen q = 0.95
certificate manifest and validation-selection receipt. Their original paths
and SHA-256 values remain bound by
`configs/economics/economic_participation_v1.yaml`. Tests verify those hashes
before relocating reads to this directory. Original JSON contents are unchanged.

They make the certificate-pinned runtime tests runnable in a fresh checkout.
The tests still verify the actual historical Git blobs, controller criteria,
scenario-hash disjointness and the recorded certificate/selection provenance,
and replay only the existing non-locked seed-20000 example. These are metadata
fixtures, not newly evaluated locked scenarios or replacement certificates.

Full Git history is required (`git clone` without `--depth`, or fetch the
complete history); CI already uses `fetch-depth: 0`. The production economic
export still requires its original, hash-verified input files under `results/`.
