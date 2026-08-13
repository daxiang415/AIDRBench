# Evidence-aware fleet scaling

The virtual-fleet layer separates four things that must not be conflated:

1. a versioned GPU SKU specification;
2. a hardware-independent work-unit definition;
3. a measured or benchmark-anchored operating baseline and control-response
   curve;
4. a data-center capacity and workload scenario.

This separation permits H100/H200 counterfactual scenarios without claiming
that AIDRBench measured hardware it does not own.

## Evidence classes

Every profile and prediction carries one of these labels:

```text
measured
homogeneous_scaled
benchmark_anchored_synthetic
spec_derived_synthetic
```

`spec_derived_synthetic` is never promoted to `measured`. The supplied H100 and
H200 profiles cite public specifications and contain no hidden serving
throughput or idle-power assumptions.

## Capacity planning

`aidrbench fleet plan-capacity` first checks model-memory fit, then estimates a
transparent Roofline ceiling:

```text
capacity = min(effective tensor compute / FLOPs per work unit,
               effective HBM bandwidth / bytes per work unit)
```

For tensor-parallel profiles, an explicit serialized communication term is
added after the compute/memory roof. `communication_bytes_per_work_unit` and
`communication_efficiency` must be supplied by a profiler or matched
benchmark. A zero communication workload is retained as a visible warning, not
silently interpreted as perfect scaling.

The efficiency factors live in the scenario rather than the GPU profile. They
are assumptions until replaced by a matched public benchmark. Nameplate power
is used only as a capacity constraint; it is not reported as operating power.

Run the checked-in illustrative comparison:

```bash
conda run -n aidrbench python -m aidrbench fleet plan-capacity \
  --config configs/fleet/illustrative_10mw_70b_decode.yaml \
  --output results/fleet/illustrative_10mw_70b_decode.json
```

The example compares explicit 8-GPU H100 SXM 80 GB and H200 SXM 141 GB node
profiles under a 10 MW IT budget. It uses an illustrative dense-70B decode work
unit and must not be cited as a serving benchmark.

## Control-environment bridge

The control layer consumes two additional P2 artifacts:

- `NodeOperatingBaseline`: idle and dynamic component power, default-cap
  inference/batch capacity, TTFT, and TPOT;
- `ControlResponseCurve`: cap ratio to normalized dynamic power, service rate,
  and latency.

`predict_node_response` refuses cap values outside the calibrated range.
`aggregate_homogeneous_fleet` splits aggregate demand evenly, applies the node
response, and sums extensive quantities. Latency remains a per-request metric
and is not multiplied by node count. Unserved inference and batch work are
returned explicitly so the future Gym environment can preserve queue/backlog
conservation.

The bridge produces the raw fields needed by RL, MPC, and rule-based control:

```text
IT and facility power
inference/batch capacity
served and unserved work
TTFT/TPOT p99
inference/batch utilization
evidence chain
```

P3 will wrap these fields in state transitions and rewards. Controller logic
must not be embedded in the fleet model.

## What to run on the local server

The complete 324-point grid with three repetitions is retained as a candidate
space, not as the default execution schedule. Generate the deterministic
36-point maximin screening design instead:

```bash
conda run -n aidrbench python -m aidrbench calibrate make-plan \
  --config configs/hardware/four_gpu_node.yaml \
  --design screening \
  --output results/calibration/screening_plan.csv
```

This plan is about 10.2 hours before model-load overhead. Allow-listed cap
resolution, restore manifests, an independent heartbeat watchdog, topology
checks, and mixed-workload dry-run orchestration are implemented. Real
execution remains disabled until the concrete workload backend, external
watchdog launch, and thermal threshold are validated. The current smoke
evidence validates the serving/telemetry path but is not a response curve.

After the screening runs, the next P2 stage is:

```text
hardware run summaries
  -> normalized control-response curves
  -> held-out validation
  -> benchmark/spec baseline substitution for H100/H200
  -> homogeneous fleet aggregation
  -> P3 environment rollouts
```

If a public H100/H200 serving benchmark is later added, its model, precision,
software stack, scenario, system topology, result ID, and source URL must be
stored with the baseline. A mismatched MLPerf result must not be silently used
as a vLLM/Qwen measurement.
