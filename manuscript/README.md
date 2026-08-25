# Manuscript workspace

Target: **Nature Communications Article**.

The journal does not prescribe a Microsoft Word template for initial submission. This workspace follows the current official Article order and keeps inline figures for repository review:

1. Title and authors
2. Abstract
3. Introduction
4. Results
5. Discussion
6. Methods
7. Data Availability
8. Code Availability
9. References
10. Acknowledgements
11. Author Contributions
12. Competing Interests
13. Figure Legends

Official guidance:

- https://www.nature.com/ncomms/submit/article
- https://www.nature.com/ncomms/submit/how-to-submit
- https://www.nature.com/documents/ncomms-formatting-instructions.pdf

## Current files

- `nature_communications_article.md`: English working manuscript v0.3.
- `supplementary_information.md`: Supplementary Methods/Results working draft with evidence partitions, lock discipline, controller specification, certification rules, optimisation audits, full certificate tables and four generated supplementary figures.
- `terminology-ledger.md`: canonical terms that must remain stable across the manuscript and Supplementary Information.
- `results-evidence-allocation.md`: main-text versus Supplementary evidence decisions.
- `source_data/`: clean-commit, hash-verified CSV tables underlying all main figures and the numerical supplementary figures.
- `submission-readiness.md`: completed checks and the remaining author/archival metadata blockers.
- `references/verified-v1/`: screened DOI whitelist, reference-manager exports and manual official-source records.

## Current status

- Title: 10 words (journal maximum: 15).
- Abstract: 139 whitespace-delimited words (current official Article maximum: 150; hyphenated compounds counted as one).
- Introduction + Results + Discussion: approximately 3,856 whitespace-delimited words (current official main-text maximum: 6,000, excluding Methods and figure legends).
- Methods: approximately 2,647 whitespace-delimited words (excluded from the 6,000-word main-text limit but still edited for reproducibility and concision).
- Supplementary Information: approximately 7,396 whitespace-delimited words, including tables and captions.
- Main figures: five, within the journal's maximum of ten display items.
- Supplementary figures: four generated at 183-mm width with editable SVG/PDF, 600-dpi TIFF, repository-preview PNG and per-figure source manifests.
- Quantitative Results and figure legends: drafted from hash-verified Source Data.
- Tracked Source Data: 21 main-figure tables (17,386 rows) plus calibration, observation and representative-trajectory tables for supplementary figures.
- Literature citations: 34 references (approximately 938 whitespace-delimited words); 30 DOI records exported through the screened citation workflow and four official data/proceedings records maintained in a separate verified RIS file.
- Author metadata, funding, contributions, competing interests and archival DOI: author input required.

## Evidence-first drafting order

The draft is revised in this order: Results, Introduction, Discussion, Methods, title, Abstract. The v0.3 file is already arranged in publication order, but later edits should continue to originate from the Results evidence rather than from desired claims.
