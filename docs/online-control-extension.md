# Online control extension

Rule-based control, MPC, robust MPC, RL, CMDP rewards, safety layers, and HIL
remain available as an optional control extension. They are not required to
answer the Nature Communications mainline question and must not select the
nominal, PI, or NA physical boundaries.

Existing controller implementations and diagnostic outputs are retained for
reproducibility. Their role is to report what fraction of the precomputed NA
boundary a deployable controller can realize after the mechanism results are
complete. Historical reward and checkpoint comparisons are summarized in
`docs/hourly-validation-status.md`; they are not main-paper evidence.

