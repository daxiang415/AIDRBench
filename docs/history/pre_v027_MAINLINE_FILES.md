> Updated preparation status: [v0.25 readiness](manuscript/submission-readiness.md) · [中文说明](manuscript/submission-readiness.zh.md) · [review freeze](manuscript/releases/v0.25-review-2026-09-11/README.md). The scientific anchor remains `8c508b9`; author and archive inputs are still pending.

> **Current GitHub reading copy: v0.25 (2026-09-10), uploaded for review on 2026-09-11.** Start with [GITHUB_REVIEW_V025.md](docs/GITHUB_REVIEW_V025.md). It links the current English/Chinese papers, PDFs, eleven figures and directly runnable summary-data plotting code. The 13.39-GB v14 archive and raw/hourly recovery data remain local; historical references below to local release paths are not GitHub downloads.
# AIDRBench formal mainline

## Current v0.25, 2026-09-10

- English main and SI: `manuscript/nature_communications_article.md`, `manuscript/supplementary_information.md`; identical paper title.
- Chinese: `docs/chinese_reader/v19/`, paragraph-aligned to v0.25.
- PDFs: v0.25 content_revision files in `manuscript/exports/`; six main and five supplementary figures, 21 numbered tables.
- Current artwork: `docs/figures/commitment_narrative_v1/artwork/`.
- Ready tables for reorganised F3/F4/S3/S4: `manuscript/source_data/nature_commitment_narrative_v1/`; no new simulations or selections.
- Complete handoff: `results/exports/AIDRBench_All_Figures_2026-09-10_v14.zip`; `RUN_ALL_FIGURES.py` redraws all eleven from tables.
- Revision, evidence allocation and verification: `manuscript/revisions/commitment_narrative_2026-09-10/`.

F3c foregrounds the crossed weight/order comparison. F4 shows paired supply margins, a prespecified trace example and the decision sequence. PV is in S4; the older 63/80 cross-score panel is S3d. Historical selection and PI corrections are consolidated in Supplementary Note 7. Old data, code and protocols remain frozen. The v14 package retains the complete v0.24 recovery data and portable replay entry points.

Interpretation: permutation changes order and alignment jointly; zero misses define a successful series, while qualification targets 95% overall success. A supply deficit rules out a successful affected series, not automatically a probabilistic offer. Strict PI feasibility is distinct from causal qualification and from economic participation.

  Author metadata, licence and public archive are not to be filled without user information.

## Archived v0.24 handoff and older records

The following paths describe earlier frozen versions, not the current reading copy.

### v0.24, 2026-09-10

- English: `manuscript/nature_communications_article.md`, `manuscript/supplementary_information.md`.
- Chinese: `docs/chinese_reader/v18/`, exactly aligned by paragraph.
- PDFs: v0.24 files in `manuscript/exports/`; six main figures, five supplementary figures, 21 supplementary tables.
- New complete data: `manuscript/source_data/nature_commitment_mechanisms_v1/`; 3,040 trajectories, 656,640 hourly rows, 720 frozen scenarios, 38 resolved fixed-request PI diagnoses, complete task-resource-time reconstruction.
- Current artwork: `docs/figures/commitment_mechanisms_v1/artwork/`, PNG/PDF/SVG/TIFF for all eleven.
- Complete handoff: `results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip`.
- Protocols, audit, detailed Chinese rationale and text changes: `manuscript/revisions/commitment_mechanisms_2026-09-10/`.

## Authority and scientific correction

The local refinement uses new development 988000–988099 and confirmation 989000–989299, fixed before execution in `refinement_protocol.json` and `refinement_selection.json`. Both standards select the same four/eight-hour offers, 5.603331/4.423682 kW. The earlier reference zero-loss derating is not a stable physical result. Task resource-time tests use new 990000-series realizations with frozen `workload_protocol.json`; they do not select new offers or certify production reliability.

The earlier cumulative release/deadline PI formulation is a relaxation for crossing job windows. Its existing numeric tables are retained as relaxed planning statistics, not guaranteed job-feasible capacities. New exact-window diagnostics use per-group execution edges and every original electrical criterion, including the actual event-peak rebound denominator. A verified PI schedule does not prove causal realizability. Earlier causal queue ledgers and the separate edge-based PV optimizer are unaffected by this interpretation correction.

The new study preserves all older data: five-workload `nature_workload_composition_v1`, recovery `nature_repeat_mechanism_v1`, structural/timing `nature_operating_tradeoffs_v1`. Their frozen protocols and code hashes must not be retroactively changed. Earlier samples must not be pooled with the new confirmation.

## Direct recovery and plotting

The complete v13 package runs `RUN_ALL_FIGURES.py` from ready CSV tables. `04_code/commitment_mechanisms/replay_one.py` restores any new trajectory from relative frozen inputs and compares 92 numerical columns; `replay_pi.py` reproduces exact-window feasibility using the inherited packaged structural inputs. Old absolute paths are provenance only, not dependencies of these entry points. Original complete sources and historical manuscript versions are preserved in the package.

## Collaboration and remaining scope

  Do not fill author names, affiliations, contributions, funding, licence or public archive DOI without the user's information. No publication, repository upload or commit has been performed for this revision.

Statistical qualifications are pointwise and scenario-specific. Eight observed weeks × ten synthetic realisations are not 80 independent weeks. Task resource-time is allocated work, not measured busy-GPU activity; deadlines and permissions remain synthetic and no application pause/checkpoint/restart was measured. Economic price boundaries apply to the reference distribution only, with independent annual series rather than a continuous operating year.

## Archived baseline documentation: v0.19 and earlier

The sections below preserve earlier provenance, layouts, protocols and development notes. References to “current” within this archive describe that historical version. The current paths and scientific scope are specified above.

### Formal scientific assets

- `README.md`: scientific question, estimands, hypotheses and experiment plan.
- `manuscript/`: the article, Supplementary Information, terminology ledger,
  evidence allocation, clean-commit Source Data, submission-readiness audit and
  screened reference set.
- `configs/env/nature_mainline_*.yaml`: development, validation, locked-ID and
  locked-OOD environments.
- `configs/controller/nature_robust_mpc_v1.yaml`: the complete frozen causal
  controller specification.
- `configs/experiment/nature_*.yaml`, `configs/sensitivity/nature_*.yaml` and
  `configs/community/pv_bess.yaml`: exhaustion, hosting, renewable-integration
  and sparse sensitivity specifications.
- `configs/paper/nature_source_data_v1.yaml` and
  `configs/paper/nature_supplementary_figures_v1.yaml`: technical/system Source
  Data and supplementary-figure contracts.
- `configs/economics/` and `configs/paper/nature_economic_source_data_v1.yaml`:
  paired economic ledger, parameterised participation and Figure 6 Source Data
  contracts.
- `data/economics/` and `docs/economic_participation/`: economic input/evidence
  registers, allowed and forbidden interpretations, exact panel map and the
  Web-GPT drawing contract.
- `data/calibration/`: measured four-GPU power evidence and the validated
  calibration artifact.
- `data/examples/nature_supplementary_validation_v1/`: the deterministic,
  non-locked validation example needed to regenerate Supplementary Figures 3–4.
- `data/manifests/nature_*.yaml`: preregistration and hash-bound execution
  receipts. Downloaded data and generated Parquet results remain outside Git.
- `src/aidrbench/`: the hourly environment, causal controllers, optimisation,
  certification, statistics and paper-export implementation.
- `tests/` and `.github/workflows/ci.yml`: independent executable checks.
- `docs/figures/nature_mainline_v1/` and
  `docs/figures/nature_supplementary_v1/`: web-review previews and output
  manifests generated from the verified inputs.
- `manuscript/source_data/nature_economic_v1/`: the clean-commit, hash-bound
  ten-table economic Source Data bundle. Formal Main Figure 6 artwork is made
  by Web-GPT from `results/exports/AIDRBench_Figure6_WebGPT_v2.zip`; its original web provenance is retained; local revisions are now authorised.
- `configs/economics/cost_robustness_v1.yaml` and
  `src/aidrbench/evaluation/economic_cost_robustness.py`: the explicitly post-hoc
  delay/site-cost and annual-sampling sensitivity; it reuses the verified
  validation ledger without reopening locked scenarios or changing Figure 6.
- `manuscript/source_data/nature_economic_robustness_v1/`: four hash-bound
  supplementary economic tables (1,767 rows), supporting Supplementary
  Tables 7–9. Its current manifest records exact code hashes and clean-source
  generation from `52d96a2565a02783b9322a5e1fe0fb8b4ec42816`; all four CSVs
  remain byte-identical to the initial dirty-worktree bundle retained in Git.
- `results/exports/AIDRBench_Supplementary_Figure_S5_WebGPT_v1.zip`: the
  checksum-verified, self-contained Web-GPT input package for the four-panel
  community-profile sensitivity figure. It contains exact plot rows and no
  locally generated formal artwork.

The generic `configs/env/hourly_{continuous,discrete}.yaml` fixtures are kept
only to exercise the public environment interface in unit tests. They are not
formal result configurations.

`data/examples/economic_certificate_provenance_v1/` supplies exact frozen JSON
metadata for checkout tests, alongside the existing non-locked validation
example. `scripts/check_clean_checkout.py` verifies the suite without ignored
production artifacts. `docs/release_completion/` retains versioned decision
evidence and the user's three-agent review loop. The earlier `content_review`
PDFs are historical versions with pending Figure 6/S5 notices.

`docs/figures/web_gpt_v1/` contains the accepted, unchanged Figure 6/S5 return
files. The user confirmed generation in web GPT-6. Its acceptance manifest binds
the eight output hashes and three independent passing reviews; detailed evidence
is in `docs/web_gpt_return_review/`. Current main and SI v0.19
`complete` PDFs insert the vector originals at 183 mm. Author metadata
and archival release remain pending. `scripts/package_completed_figures.py`
merges these two figures into the existing nine-figure handoff without redrawing
the earlier artwork or altering plot data.

The main PDF layout revision v0.8.1 introduced six separately numbered figure
pages and figure-title bookmarks, retained in v0.19. Its manuscript text was v0.8. The
figure-page map and validation are in
`manuscript/revisions/figure_pagination_2026-09-07/`; the old v0.8 PDF remains a
historical snapshot.

The v0.8 article rewrites the Abstract, Introduction, Results, Discussion and
Methods for readability, using Li et al. (2026), DOI
10.1038/s41467-026-76799-4, as a structural reference. Supplementary Information
v0.8 also uses the reference article's verified 49-page SI to guide its
organization. Six Supplementary Notes follow the main results, followed by nine
method sections, the five original figures and nine numbered tables. A reader
map and a tabulated presentation of existing community-profile values make the
supporting evidence easier to locate. A compact reference-input table makes the
economic mechanisms reproducible. Existing numerical results are retained.

The current integrated Chinese reading set is `docs/chinese_reader/v13/`, with
complete Chinese and paragraph-aligned bilingual versions of both documents.
`manuscript/revisions/readability_2026-09-06/` preserves the main-text revision;
`manuscript/revisions/supplement_readability_2026-09-06/` preserves the SI revision,
reference SI, original text, aligned authoring files and review records.
The SI table now explicitly identifies the baseline-relative terminal backlog,
normalised event-and-recovery peak relief and data-centre capacity in Table 6.
Earlier PDFs, Chinese reading versions and the v3 all-figure handoff remain
historical delivery snapshots. Accepted figure assets remain unchanged.

The v0.9 revision adds the explicitly post-hoc flexible-work and GPU-pool share
study in `configs/sensitivity/nature_flexible_share_v1.yaml`. Eight work shares
and six GPU allocations form 13 configurations on 200 paired nonlocked parent
scenarios. Twelve configurations pass the finite-horizon service gate; the 40%
GPU allocation fails and is retained. The 9,600 PI solves and 7,200 fixed-request
notice runs are documented in `docs/flexible_share_sensitivity/report_v1.md`.
Supplementary Tables 10–12 report these results. The 95% work-share point depends
on the clearance tail and is not a continuous-operation or causal certificate.
The main title of Results 1 and notice interpretation have been revised to match
this evidence; original locked results and economic figures remain unchanged.

`manuscript/source_data/nature_flexible_share_v1/` contains the full numerical
tables, while `docs/flexible_share_sensitivity/plot_data/` contains direct panel
inputs. `results/exports/AIDRBench_Flexible_Share_Plot_Data_v1.zip` packages both
with the explanation, frozen design and Web-GPT-6 drawing instructions.
All derived scenarios and hourly traces remain in
`results/nature_mainline/flexible_share_sensitivity_v1/`. The implementation,
validation and bilingual revision record are in
`manuscript/revisions/flexible_share_2026-09-07/`. No new formal figure was drawn;
the new evidence is included as tables in the current manuscript package.

The v0.10 revision adds the user's requested 10%, 20% and 30% work
fractions and a common-allocation 10–60% curve. With the original 60% flexible
GPU allocation, those three low-work cases exceed the separate rigid pool and
are retained as structural failures without simulated samples. Six new work
fractions at a fixed 40% GPU allocation all pass 200 paired baseline checks.
The v2 study therefore contains 22 configurations: 19 constructible and three
structurally infeasible; 18 pass the simulated service gate. All old v1
scenario-level results are reused exactly. The combined evidence comprises
14,400 PI optima, 10,800 fixed-request notice runs and 7,200 schedule pairs.

`configs/sensitivity/nature_flexible_share_v2.yaml` and
`docs/flexible_share_sensitivity/protocol_v2.md` define this extension.
The v2 explanation is `docs/flexible_share_sensitivity/report_v2.md`;
`manuscript/source_data/nature_flexible_share_v2/` and
`docs/flexible_share_sensitivity/plot_data/v2/` contain the complete numerical
and direct-plot inputs. `results/exports/AIDRBench_Flexible_Share_Plot_Data_v2.zip`
packages both. New raw scenarios and hourly traces are in
`results/nature_mainline/flexible_share_low_extension_v2/`; the combined index
is in `results/nature_mainline/flexible_share_sensitivity_v2/`, and the revision
record is `manuscript/revisions/flexible_share_low_range_2026-09-07/`.
Supplementary Tables 10–12 distinguish fixed GPU allocations, structural
failure, baseline service failure and the 95% tail-dependent stress case.

The earlier v0.11 revision reorganizes the main narrative around work eligibility,
GPU allocation, planning capacity, independent delivery qualification and
participation costs. Result 1 starts with the fixed-allocation 10–60% curve,
then explains allocation effects and the configuration-specific nominal gap.
The notice result is restricted to fixed-request success, and Discussion
identifies low-fraction fluid scaling and changing class eligibility at 60%.
Numerical source data, original certificates, economic results and accepted
artwork are preserved. The bilingual record and checks are in
`manuscript/revisions/main_narrative_2026-09-07/`. SI retains its scientific
content and aligns the reader guide with the revised first Results section.

The v0.13 analysis, retained in current v0.19, adds the joint share grid: f = 10–60% and g =
10–90% in ten-percentage-point steps. Among 54 primary configurations, 23 pass
all baseline checks, 9 fail baseline service and 22 fail the rigid-pool structural
screen without simulation. One passing configuration (50% work, 30% GPUs)
requires the clearance tail because mean flexible work exceeds pool capacity.
Failure counts delimit a chosen fixed-pool model; they are not a population
failure rate or the main scientific contribution. Main text emphasizes capacity
variation within the viable region. Supplementary Table 12 includes every fixed
request; Tables 13–14 give the complete grid and paired mean interactions.

`configs/sensitivity/nature_flexible_share_v3.yaml` and
`docs/flexible_share_sensitivity/protocol_v3.md` bind the execution design.
`manuscript/source_data/nature_flexible_share_v3/` includes all new and old
numerical results: 25,600 PI optima, 19,200 controller runs, 474 paired mean
contrasts and 128 notice contrasts. Original v2 scenario-level results are
unchanged. New raw scenarios and traces are in
`results/nature_mainline/flexible_share_joint_extension_v3/`, with the combined
index in `results/nature_mainline/flexible_share_sensitivity_v3/`.
The explanation is `docs/flexible_share_sensitivity/README.md`; revisions,
recovery inventory and independent checks are in
`manuscript/revisions/joint_share_grid_2026-09-07/`. Current Chinese reading set v13
corresponds to v0.19; v10 preserves the earlier v0.16 text.

Figure 1 was formally integrated in v0.15 and remains in manuscript v0.19 and Chinese reading set v13.
`docs/figure1_revision/v3/` contains the authorised local Python renderer, direct
CSVs, full numerical support, fonts and SVG/PDF/PNG/TIFF artwork. Its four panels
show the joint allocation curves, service-feasible allocations, the original
reference comparison and every calibration observation. Figure references and
bilingual captions are aligned. There is no pending web-generation step.

`results/exports/AIDRBench_All_Figures_2026-09-08_v8.zip` is the current complete
11-figure handoff. It contains current manuscripts and Chinese Markdown, every
figure's direct panel data and editable artwork, the new joint-grid source tables,
and a one-command `RUN_ALL_FIGURES.py` entry. The source and checks are recorded
in `manuscript/revisions/figure1_formal_2026-09-08/`, with the v0.16 text refresh
in `manuscript/revisions/opening_readability_2026-09-08/`. Earlier Figure 1 v1/v2 inputs
and v0.12/v0.14 draft PDFs remain historical snapshots.

`scripts/draw_review_figures.py`, `docs/figures/local_review_v3/` and
`results/exports/AIDRBench_Figure_Recovery_v3.zip` preserve explicitly labelled
local Figure 6/S5 drafts and standalone redraw inputs. These were originally authorised
for review only; that historical restriction was superseded on 2026-09-08. Optional renderer
arguments create separate local-figure-review PDFs; they do not fill the formal
artwork slots. `docs/figure_recovery/` records recovery scope and commands.

## Deliberately excluded

This mainline excludes reinforcement-learning training and rewards,
hardware-in-the-loop power actuation, legacy minute-level protocols, controller
leaderboards, and H100/H200 capacity extrapolation. None is needed to reproduce
the paper's claims. Earlier implementations remain available through Git
history rather than coexisting with the formal files.

## Minimum verification

```bash
python -m aidrbench project-check
python -m aidrbench protocol-check \
  --manifest data/manifests/nature_mainline_protocol_v1.yaml
ruff check .
mypy src
pytest
```

Paper source data and figures are regenerated with the commands in
`docs/paper-packaging.md`.

## Opening revision v0.16, 2026-09-08

Manuscript v0.16 replaces the Abstract and five Introduction paragraphs to explain the grid-connection problem, the commitment question, and its service and cost constraints. All Results, Discussion, Methods, figure legends, numerical inputs and formal figures remain as in v0.15. Chinese reader v10 is paragraph-aligned. The v0.16 complete handoff was `results/exports/AIDRBench_All_Figures_2026-09-08_v5.zip`; it refreshes the manuscript files while preserving all 11 figures, plotting data and redraw code. Revision evidence is in `manuscript/revisions/opening_readability_2026-09-08/`.

## Historical supplementary revision v0.17, 2026-09-08

Manuscript v0.17 rewrites the Supplementary Notes and supporting Methods for readability and reporting precision. The main article body is unchanged from v0.16. The hourly deadline queue is distinguished from its eight observation/reporting labels; S5's caption now limits its conclusion to the tested profiles. Table numbers, display equations, source data and all formal artwork are preserved. The aligned Chinese reader at that revision was v11, and its handoff was `results/exports/AIDRBench_All_Figures_2026-09-08_v6.zip`. Source reconciliation, translation checks and PDF inspection are recorded in `manuscript/revisions/supplement_clarity_2026-09-08/`. No new subagents or experiments were used.

## Historical content extension v0.18, 2026-09-08

The independent repeated-offer extension is governed by `configs/experiment/nature_repeat_capacity_v1.yaml`, not the original preregistration. The initial execution identities and all original locked evidence remain unchanged. New results are in `results/nature_mainline/repeat_capacity_v1/`; manuscript-ready tables and complete hourly drawing data are in `manuscript/source_data/nature_repeat_capacity_v1/`.

The extension completed 21,620 formal controller replays: 5,000 development, 13,800 confirmation, 1,920 production-timing, 600 extended-horizon, and 300 additional paired original-horizon replays. There are 100 new development and 300 new confirmation seeds. Production timing uses eight observed weeks with ten model replicates per week and two ordering conditions; these runs are not independent production deployments.

Nine development-selected repeated offers passed pointwise confirmation, and one original offer also passed. The horizon sensitivity changed the severe last-call failure without changing the quarter-offer dispatch trajectories through hour 167. State-feature prediction did not improve; that negative result is retained. Complete-series economics preserves history within four-call series, not across a simulated continuous year.

At this historical extension, article and SI were v0.18, Chinese readers v12, and the handoff was `results/exports/AIDRBench_All_Figures_2026-09-08_v7.zip`. The six main and five supplementary images are existing artwork retained for the author's planned redraw; new analyses are available as direct plotting data. Figure 3 remains explicitly labelled as the initial planning-request diagnostic. No subagents were started.

Validation, derivation explanations and reporting-only baseline-gate correction are in `manuscript/revisions/repeat_capacity_2026-09-08/`. The current runner fixes the baseline flag; re-running simulations must use a fresh output directory because the historical execution code hash is retained.

## Current results explanation v0.19, 2026-09-08

The Results, Abstract, Discussion and corresponding supplementary explanations now connect work eligibility, call schedules, grid benefits and participation costs to concrete choices. All numerical tables, Methods, references and figure assets remain those of v0.18. The revised text retains the successful original repeated offer, recovery-boundary intervention and negative prediction result. Chinese readers are v13; the full handoff is `results/exports/AIDRBench_All_Figures_2026-09-08_v8.zip`. Revision evidence is in `manuscript/revisions/results_clarity_2026-09-08/`. No new simulations or subagents were used.
