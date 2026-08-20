# Data manifests

P1 manifests record source URL, release/version, retrieval timestamp, SHA-256,
license, preprocessing configuration, and time-based split membership. Raw data
is never overwritten or committed.

`nature_mainline_validation_scenarios_v1.yaml` is a post-generation receipt for
the ignored local validation artifacts. It records the frozen-plan commit,
aggregate scenario-set digest and integrity checks without treating validation
as locked evidence or a capacity certificate.
