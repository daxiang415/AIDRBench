# v0.25 verification and scope

This revision reorganises existing frozen evidence. It does not generate new scientific simulations, select new offers, change a confirmation set, or rerun economic sampling.

| Check | Evidence | Outcome |
|---|---|---|
| New supply plotting tables | `data_validation.json`; 640 trial records checked against frozen hourly ledgers | PASS |
| Crossed weight/order scores and paired supply changes | `text_and_evidence_audit.json`; 31/80, 55/80 and 54/80; 29 removed and 5 created shortages | PASS |
| Frozen study protocols and selections | Compared with delivered v13 bytes | Unchanged |
| English and Chinese correspondence | `revision_validation.json`; main 170 blocks, SI 153 blocks, source hashes | PASS |
| Figure source preflight and exported glyphs | `figure_source_qa.json`, `figure_glyph_audit.json` | PASS; eleven PDFs meet 6 pt |
| Portable package redraw | `redraw_validation.json`; all eleven PNG SHA-256 values equal current artwork | PASS |
| One existing resource-time case replayed from package | `replay_validation.json`; seed 990000, 216 hours, 92 numeric columns and missing-value masks | PASS; maximum absolute difference 0 |
| Main/SI PDF completeness and SI navigation | `pdf_validation.json`; 17/25 pages, 6/5 figures, 21 tables | PASS |

The replay verifies a delivered case and package paths; it is not an added observation or a new confirmation test. The simulator and recovery controller were imported from the package itself. The existing strict-PI witness and replay evidence from v13 is retained, rather than claimed to have been rerun here.

The direct plotting map distinguishes `plot_input`, which the supplied launcher reads, from the per-figure `ready_data` convenience copies for other plotting software. All earlier source data, full trajectories, frozen recovery inputs and original release files remain available. The complete v0.24 manuscript and all eleven previous figures are additionally archived inside v14.

The archive builder verifies every final member against its staging SHA-256, reads every payload to validate CRC, checks duplicate names and extraction-version consistency, and writes the final package hash. The final archive receipt is `package_validation.json`, stored alongside this report after completion; it is deliberately outside the archive to avoid a self-referential package checksum.

No new hardware pause/restart experiment or wider production-deadline validation is claimed. Author identities, funding, licence and public archiving remain pending user information. No publishing or subagent review was performed.
