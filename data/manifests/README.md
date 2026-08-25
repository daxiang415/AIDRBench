# Data manifests

P1 manifests record source URL, release/version, retrieval timestamp, SHA-256,
license, preprocessing configuration, and time-based split membership. Raw data
is never overwritten or committed.

`nature_mainline_validation_scenarios_v1.yaml` is a post-generation receipt for
the ignored local validation artifacts. It records the frozen-plan commit,
aggregate scenario-set digest and integrity checks without treating validation
as locked evidence or a capacity certificate.

Protocol hashes embedded in generated scenario or result receipts are immutable
run-time identities: they identify the exact protocol bytes at generation or
execution. They are intentionally not rewritten when the current top-level
protocol later appends a consumed-status update or a new result-receipt hash.
The current protocol instead verifies the immutable locked-ID and locked-OOD
receipts fail closed. A historical receipt hash must therefore never be compared
with the mutable current protocol as though it were a live pointer.

`sources.yaml` schema v2 binds every current formal input in the protocol to a
declared source and exact SHA-256. The Alibaba 2026 “Lite” file is a project-made,
bounded stratified sampler from the official job-execution-summary archive; it
is not a separate Alibaba release and it does not reproduce the temporal
correlations available in the much larger pod-hourly archive.
