# Nature Communications submission readiness — v0.25

Audit updated: **2026-09-11**. Stage: preparation for initial submission. Target: research Article. Title: *Workload timing limits reliable demand response from AI data centres*.

**Readiness: blocked for actual submission; the scientific reading copy is frozen for review.** Current papers and figures are available and reproducible within their declared model scope. Author information and declarations remain incomplete, the software licence is undecided, and the full revised data/code archive has no public archival identifier. This audit does not certify journal acceptance or completion of the final submission package.

The [2026-09-06 audit](readiness-history/submission-readiness_2026-09-06.md) is historical. Its manuscript versions, test counts, figure provenance and table structure do not describe the current release.

## Current version and recoverability

The immutable scientific review anchor is commit [`8c508b9ca13c26089e27ff1a0b36405cbbfa6280`](https://github.com/daxiang415/AIDRBench/commit/8c508b9ca13c26089e27ff1a0b36405cbbfa6280), available on `codex/manuscript-v025` and [draft PR #2](https://github.com/daxiang415/AIDRBench/pull/2). At this audit it has not been merged into `main`. Later documentation-only commits do not change the scientific anchor; select the explicit commit when reproducing the reviewed content.

The original research working directory still has substantial uncommitted development and historical material. This does not mean the new version lacks a backup: the isolated GitHub reading copy was committed and pushed, and the complete local v14 archive was retained. Neither the dirty research directory nor an unspecified branch head is the release identifier.

The [review freeze record](releases/v0.25-review-2026-09-11/README.md) binds the paper, SI, Chinese readers, figures, plotting code and summary data to content hashes and the immutable Git commit. It also identifies the complete local v14 archive by SHA-256. The GitHub snapshot is approximately 34 MB and excludes large raw/hourly/recovery data; the full archive is 13,392,344,034 bytes. The whole archive hash was rechecked on 2026-09-11 and matches the completed v0.25 integrity receipt. This is a review freeze, not a journal-submission release or public data deposit.

## Deliverable matrix

| Item | Current evidence and status | Remaining action |
|---|---|---|
| English main text | [v0.25 Markdown](nature_communications_article.md), 17-page PDF | Preserve evidence limits; obtain author approval of final text |
| Supplementary Information | [v0.25 Markdown](supplementary_information.md), 25-page PDF | Keep final metadata and archive identifiers aligned |
| Chinese readers | [v19 main](../docs/chinese_reader/v19/main_zh.md) and [v19 SI](../docs/chinese_reader/v19/supplement_zh.md); 170/153 aligned blocks | Update if the corresponding English content changes |
| Displays | Six main figures, five supplementary figures, 21 numbered supplementary tables | Complete the final journal-stage file preflight |
| Figure inputs and code | Eleven figures redraw from included CSV/JSON; PNG/PDF/SVG in GitHub, TIFFs reproducible | Full trajectory replay still needs the complete local package |
| Bibliography | 42 numbered entries in the main text | Reconcile the historical reference-manager export with the final citation order |
| Author identity | Names, order, affiliations and corresponding-author email remain placeholders | Author-supplied information required |
| Funding and declarations | Funding/acknowledgements, CRediT contributions and competing interests remain placeholders | Author-supplied declarations required; absence is not a declaration of no interests |
| Availability and licence | Working statements; GitHub reading copy public, full archival deposition and licence pending | Confirm licence and deposit/access arrangements, then insert actual identifiers |
| Submission forms and accompanying files | No completed final submission package certified | Confirm applicable reporting, disclosure, permissions and journal-stage requirements |

Current descriptive counts are an **182-word abstract** and **1,599-word Results**, using the convention in the [v0.25 revision receipt](revisions/commitment_narrative_2026-09-10/revision_validation.json). These counts are not claims of compliance with current journal limits. The old audit's exact format-limit conclusions are withdrawn from the active record; article-type and submission-stage instructions still need to be checked before actual submission.

## Supported findings and boundaries

- **Workload representation changes commitment transfer.** At 2.95 kW, count-weighted tests succeed in 80/80 realisations in both orders; resource-time weighting gives 31/80 in original order and 55/80 at the 1% service standard or 54/80 at zero misses after hourly permutation (Figure 3c; Supplementary Table 20). Eight observed weeks with ten synthetic realisations each are not 80 independent production weeks. Permutation changes hourly order and alignment with calls and community demand together.
- **Diagnosis changes the appropriate response.** Figure 4 and Supplementary Table 19 distinguish immediate supply shortage, strict work-group-window infeasibility and a feasible full-information schedule with causal-controller failure. A PI witness is not an implementable causal controller. One failed series does not automatically disqualify a probabilistic contract.
- **Reference offers qualify within their stated distribution.** Four/eight-hour repeated offers remain 5.603331/4.423682 kW, with zero-miss confirmation counts 297/300 and 296/300. Both standards select the same offers on the tested local grid. The eight-hour grid ceiling is not a continuous capacity maximum. Zero misses define a successful series; qualification targets 95% overall success probability.
- **Costs are compared after qualification.** Figures 6/S5 and Supplementary Table 21 retain failed reference-product trajectories. At the stated waiting valuation and zero fixed fee, thresholds remain USD 183.30/330.11 per offered accounting kW-year. These are conditional participation screens, not measured profits or quotations for workloads that fail transfer.
- **Evidence types remain separate.** Aggregate-PI numbers are relaxed planning statistics, not guaranteed work-group-feasible capacity. Board-power calibration does not establish application pause/checkpoint/restart performance. Independent annual series accounting is not a continuous-year operating test. PV hosting and fixed-PV utilisation are distinct secondary outcomes.

## Verification record and limits

Checks apply to their named snapshots, not every local historical branch.

| Check | Recorded result | Scope |
|---|---|---|
| GitHub redraw | Eleven PNG hashes match the local v0.25 artwork | Independent checkout, after plotting-code formatting changes |
| Text, Chinese and PDFs | Main/SI Markdown and PDF hashes match; Chinese alignment and image links pass | [GitHub validation](../docs/github_review_v025_validation.json) at the scientific anchor |
| Repository checks | Ruff, mypy and 169 local tests pass | GitHub checkout, not the original uncommitted research tree |
| Remote CI | Lint, type checking and tests pass | [Run 34558025261](https://github.com/daxiang415/AIDRBench/actions/runs/34558025261) for `8c508b9` |
| Numerical/source checks | 640 supply records reconcile; crossed scores and paired shortages match; protocols unchanged | Existing [v0.25 verification summary](revisions/commitment_narrative_2026-09-10/VERIFICATION_SUMMARY.md) |
| Package replay | One 216-hour series matches 92 numeric columns and missing-value masks, maximum absolute difference 0 | Existing v14 portability check, not a new scientific observation |
| Package integrity | 56,521 members passed SHA-256/CRC at packaging; whole ZIP hash rechecked for this freeze | Full local archive, not all published in GitHub |
| PDF presentation | 17/25 pages, six/five figures, 21 SI tables; text-edge and bookmark checks passed | Previous targeted visual checks, not a fresh page-by-page inspection here |

This update did not rerun all scientific simulations, reselect offers, redo economic sampling or newly inspect every PDF page. The contributor's latest review is useful feedback; its claimed reruns are not substituted for independently retained execution receipts.

## Open scientific priorities

Reproducibility does not settle novelty, importance or external validity. The present argument centres on a wrong-commitment decision exposed by workload representation, with diagnostics separating delivery impossibility, control opportunity and participation value. Whether that contribution is sufficiently distinct from the cited recent literature remains a substantive scientific and editorial judgement.

The next evidence priority is a prespecified external test using another chronological task-level trace or a held-out period not already used in development. Preserve task resource-time and its alignment with calls. Freeze requests, controller and scoring before observing outcomes; report both service endpoints, baseline failures and week-level results. Do not recycle the current eight weeks as new independent external confirmation. No such new external result is certified here.

A focused comparison against the already cited closest studies should state the shared concept, additional controlled evidence and operational decision changed. Hardware pause/restart validation remains valuable but unperformed; it is not declared a universal Nature Communications admission requirement. More simulations with the same input structure would not resolve these gaps by themselves.

## From review freeze to final submission freeze

1. Decide final scientific scope after any targeted external validation and literature comparison. Preserve old protocols and failed results; an added study needs its own prospective design and independent confirmation rules.
2. Fill only author-confirmed identity, correspondence, funding, contributions and competing interests. The user previously deferred these inputs; placeholders remain intentionally unfilled.
3. Confirm the licence and actual archival/access arrangements. Public GitHub review access does not supply a DOI or deposit the full local data package.
4. Select one clean release commit containing the resulting final paper, SI, figures, source data and code. Update affected outputs, verify hashes and links, and bind the commit to its archive hashes. Do not silently relabel the review anchor as the final submission release.
5. Complete applicable journal-stage file/form checks and final author approval. Confirm access before replacing availability placeholders or claiming readiness.

No journal submission, release tag, new DOI or all-author approval is claimed by this audit.
