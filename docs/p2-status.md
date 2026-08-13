# P2 hardware-calibration status

P2 is in progress. The repository can now generate the deterministic stage-A
coarse grid described in README section 18. The tracked hardware configuration
defines all factor levels, timing, repetitions, randomization, and seed; the
generated CSV records stable configuration/run IDs and stays under the ignored
machine-local `results/calibration/` directory.

Implemented:

- `aidrbench calibrate make-plan` with full-factorial expansion;
- an explicit eight-configuration `smoke` design that takes about 32 minutes
  before model-load overhead, selectable with `--design smoke`;
- reproducible seeded run ordering;
- validation that cap ratios never exceed the default-limit ratio of 1.0;
- runtime and configuration-hash summary output;
- read-only, fixed-cadence `nvidia-smi` collection with both UTC wall-clock and
  monotonic timestamps, explicit missing-value handling, GPU selection checks,
  and Parquet output;
- reproducible AIPerf smoke-trace generation that retains BurstGPT token lengths
  and relative arrival ordering while recording an explicit smoke-only time
  compression factor;
- a real vLLM/AIPerf smoke replay against `Qwen/Qwen3-0.6B`: 10/10 requests
  completed without errors and the server reported all 4,622 requested output
  tokens;
- paired one-second `nvidia-smi` evidence for that replay: 45 samples on each
  of four GPUs (180 rows total), with no missing values and no power-cap
  changes. The machine-local evidence is stored under
  `results/calibration/p2_vllm_smoke_001/`;
- a paired TP=1/TP=2 topology smoke at the unchanged 300 W default limit using
  the same 10-request trace. GPU 0--1 established NCCL tensor parallel over the
  measured `NODE` path, and both runs completed 10/10 requests without errors;
- `aidrbench calibrate compare-topology-runs`, which aligns AIPerf benchmark
  timestamps with one-second Parquet telemetry and reports arrival limitation,
  service speedup, per-GPU scaling efficiency, latency changes, power, and
  estimated energy per completion token. The first machine-local comparison is
  `results/calibration/topology_tp1_vs_tp2_300w_001.json`;
- evidence-aware H100/H200 GPU profiles, Roofline capacity comparison, explicit
  memory-fit and IT-power constraints, and homogeneous fleet aggregation;
- a deterministic 36-point maximin `screening` design (about 10.2 hours) so the
  972-run full-factorial plan remains a candidate space rather than the default
  execution schedule;
- a dry-run-by-default allow-listed power adapter, UUID-bound restore manifest,
  independent restore CLI, heartbeat watchdog, topology/P2P validation, and
  mixed inference/batch schedule coordinator;
- device-compatible 252/276/300 W cap levels, preserving 27 distinct physical
  actions on the measured 250–300 W controllable range.

Not yet completed:

- optional PDU integration for node-level power evidence;
- concrete vLLM/AIPerf and batch-worker execution backend plus supervisor launch;
- thermal soak and selection of the executable temperature limit;
- execution and summarization of the 36-point screening design;
- surrogate fitting and held-out evaluation.

No hardware measurements are fabricated by the planner. P2 remains incomplete
until the required calibration configurations and held-out surrogate results
exist. The completed runs are smoke validations; they are not used as a
calibrated hardware response model. In particular, the first topology pair is
arrival-limited and uses a 0.6B model, so its observed non-ideal scaling term
must not be interpreted as pure interconnect overhead.
