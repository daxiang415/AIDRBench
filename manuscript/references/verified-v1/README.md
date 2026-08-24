# Verified manuscript references

- `references.ris` contains the 30 DOI records retrieved through the
  `nature-citation` DOI-whitelist workflow.
- `references_manual_verified.ris` contains four official data/report and
  USENIX records that are absent from, or not exportable through, the Crossref
  path.
- `dois.txt` is the screened DOI whitelist. Crossref did not export the two
  NREL technical-report records, so they are retained in the manual file.

The two RIS files together correspond to references 1–34 in the manuscript.
The rejected first-pass keyword matches are deliberately excluded from the
formal repository. `../../citation-claims-v1.txt` records the claim set used
for screening; this directory is the only manuscript reference library.
