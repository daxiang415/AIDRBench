# Data availability and reproducibility

The repository accompanies manuscript **v0.27**, with **R8** main figures dated 17 September 2026.

## Included resources

| Resource | Location |
| --- | --- |
| Paper and supplementary information | `paper/v0.27/latex/` |
| Six main figures and panel CSV/Excel tables | `paper/v0.27/figures/main/` |
| Ten supplementary figures and reproduction scripts | `paper/v0.27/figures/supplement/` |
| Compact result tables and calibration evidence | `manuscript/source_data/` |
| Model implementation and configurations | `src/aidrbench/`, `configs/` |
| Study drivers and protocols | `manuscript/revisions/` |
| Test fixtures and regression checks | `data/examples/`, `tests/` |

Bulk production workloads, complete hourly trajectories and per-scenario recovery inputs are not distributed in this checkout. Protocols and source-data scope notes identify these external inputs. Running the complete production-scale study requires them in addition to the repository.

## Reproducibility levels

**File verification** checks the checkout against recorded hashes:

```bash
python tools/aidr.py check --hashes
```

**Figure reproduction** regenerates plots from the included panel tables. Supplementary audit scripts compare the rendered quantitative series with the reference coordinates. Layout can differ from the reference artwork.

**Experiment replay** reruns the analyses using their specified inputs, configurations and dependencies. The regression suite includes historical certificate checks; these require a full Git clone and the versions in `requirements-certificate.txt`.

Passing a file or plotting check is not equivalent to rerunning the complete study.

## Version records

`paper/v0.27/MANIFEST.csv` is the original release manifest. `docs/checkout-layout.json` records maintained documentation files and packaging changes. Scientific files retain their original hash checks.

The original layout is available at commit `66105ccaa5629f2d24c53c6d757922e139d54440` on `archive/v0.27-original-layout`. Earlier nested manifests, protocols and validation records describe the versions for which they were created. The historical runtime in `manuscript/source_data/nature_economic_robustness_v1/frozen_runtime/` is bound to its result manifest.

## Figure resources

The main Figure 1 SVG uses adjacent files in `Figure_1_assets/`; its PDF and PNG are standalone. `GITHUB_ADAPTATION.json` records the packaging change that extracted those assets without altering their bytes.

Reproduction output is written to separate directories. Reference paper PDFs and figures are not replaced by the plotting commands.

## Release identifiers

A software licence and archival DOI have not yet been assigned. The version label identifies the repository's manuscript snapshot, not a journal publication.
