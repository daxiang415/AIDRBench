# Nature Communications paper packaging

The frozen mainline results are packaged through two deterministic commands. These commands do
not select capacities, reopen locked data, or rerun scientific experiments; they only project
existing, hash-bound result artifacts into manuscript source data and figures.

## 1. Export manuscript source data

```bash
aidrbench paper export-source-data \
  --specification configs/paper/nature_source_data_v1.yaml \
  --output results/nature_mainline/source_data_v1 \
  --repository-root .
```

The specification declares every input path, output CSV, retained column, fixed label, sort key,
figure number, and panel. The exporter fails closed on missing inputs, missing columns, duplicate
identifiers, output path traversal, or label collisions. `source_data_manifest.json` records:

- the SHA-256 of the specification;
- the SHA-256 and row count of every input;
- the SHA-256, columns, and row count of every exported CSV;
- the Git commit and whether the working tree was dirty during export.

The current bundle includes development and independent validation exhaustion, joint DC–PV
hosting, fixed-capacity PV-operation and the earlier fixed-PV/max-DC hosting results; locked-ID and
locked-OOD certificates at q={0.90, 0.95, 0.99}; and the predeclared power, workload,
success-criterion and infrastructure sensitivities.

## 2. Generate the five main figures

```bash
aidrbench paper figures \
  --source-data results/nature_mainline/source_data_v1 \
  --output results/figures/nature_mainline_v1 \
  --figures 1 2 3 4 5 \
  --formats svg pdf tiff png
```

Before reading any CSV, the figure generator checks its SHA-256 against the source-data manifest.
Each figure receives a separate JSON manifest recording the source-data manifest hash, source table
IDs, physical size, backend, minimum configured font size, scientific conclusion, claim boundaries,
and output hashes. SVG and PDF are editable vector outputs; TIFF is exported at 600 dpi and PNG is
provided for rapid review.

The production renderer uses a reference-led Nature Communications visual contract rather than an
equal-sized dashboard grid:

- every main figure is rendered at the journal's 180-mm double-column width;

- Figure 1 is a schematic-led composite in which the nominal-to-job-derived mechanism is the hero
  panel and the quantitative gap, hardware anchor, and evidence hierarchy are subordinate;
- Figure 2 gives most of the page width to the duration-dependent capacity layers, while reliability
  and notice diagnostics remain compact supporting panels;
- Figure 3 makes compute-debt accumulation the dominant mechanism and pairs the development and
  validation service heatmaps below it;
- Figure 4 uses the validation joint DC–PV hosting envelope as the hero panel, followed by the
  fixed-201-kW PV-hosting gain, fixed-500-kW PV operation and the orthogonal AI–DER interaction
  contrasts;
- Figure 5 places the locked-ID versus locked-OOD generalization boundary across the full lower row,
  above compact predeclared sensitivity summaries.

The shared visual system uses low-saturation colours, direct labels, short panel headings, asymmetric
panel areas, and explicit white space. It deliberately avoids decorative cards, repeated long titles,
redundant legends, and duplicate panels that do not add a distinct claim.

## 3. Clean provenance workflow

Final manuscript artifacts should be generated from a committed, clean tree:

```bash
git status --short
uv lock --check
ruff check .
mypy src
pytest

aidrbench paper export-source-data
aidrbench paper figures
```

After export, confirm that `software.git.working_tree_dirty` is `false` in
`results/nature_mainline/source_data_v1/source_data_manifest.json`. Generated results remain ignored
by Git; release copies should be deposited with the manuscript source data and archived under the
same tagged commit.

## 4. Interpretation boundaries

- PI is a perfect-information planning upper bound, not a causal certificate.
- Restricted NA is a finite-scenario information bound, not an unseen-scenario reliability claim.
- The locked-ID q=0.95 H=1 candidate remains not certified and must stay visible.
- Repeated-event results are fixed-capacity mechanism diagnostics, not repeated-event capacity
  certificates.
- Renewable-integration and hosting validation are independent planning-result replications, not
  real-world causal effects; partially feasible envelope cells are not zero-capacity points.
- Fixed-PV energy benefits do not imply lower PCC peak, and the declared 1% flexible deadline-miss
  budget remains visible.
- Locked-OOD replays fixed validation-selected candidates. Zero certified OOD cells does not mean
  that OOD firm capacity is zero, because OOD capacity reselection was prohibited.
