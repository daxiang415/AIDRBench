# Architecture boundary

AIDRBench keeps controller policy separate from execution backends. Controllers
emit one of 27 stable action IDs; emulator and hardware backends implement the
same `reset`, `apply_action`, `advance`, `get_state`, `get_metrics`, and `close`
contract.

P0 establishes interfaces only. P1 adds data, P2 adds measured surrogates, P3
adds queue dynamics and the Gymnasium environment, P4 adds benchmark controllers,
and P5 adds guarded hardware execution.
