# Hardware safety boundary

Hardware mutation is disabled by default. `aidrbench hil power-preflight`,
`hil dry-run-action`, and `calibrate dry-run-plan` are read-only even when the
hardware configuration is not ready for execution.

## Independent gates

Real power-limit changes require all of the following:

- an exact GPU ID allow-list and matching fresh inventory;
- stable GPU UUIDs captured in a restore manifest;
- device-reported min/default/max power ranges;
- distinct physical limits for every configured cap level;
- a configured maximum GPU temperature;
- a successful topology and inference-pool P2P check;
- `safety.allow_hardware_mutation: true` in tracked configuration;
- an execution-specific CLI acknowledgement;
- privilege granted outside the controller process.

The Python adapter never invokes a shell and never prepends `sudo`. A future
service account or supervisor owns the narrow privilege to run the allow-listed
`nvidia-smi --id <id> --power-limit <validated watts>` command.

## Current machine result

The four GPUs report a 250 W minimum and 300 W default. The former batch levels
0.60 and 0.80 both clipped to 250 W, collapsing 27 logical actions into 18
physical actions. V0 now uses 0.84, 0.92, and 1.00 for both pools, which resolve
to distinct 252, 276, and 300 W limits.

GPU 0–1 have P2P read/write support, but `nvidia-smi topo -m` reports a `NODE`
path rather than NVLink. Tensor-parallel performance must therefore be measured
on this exact pair. The topology warning is retained in every preflight
manifest.

## Read-only preflight

```bash
conda run -n aidrbench python -m aidrbench hil power-preflight \
  --config configs/hardware/four_gpu_node.yaml \
  --restore-manifest results/safety/gpu_restore_manifest.json \
  --audit-log results/safety/actuator_audit.jsonl
```

The manifest is written before any possible mutation and contains default
limits, UUIDs, topology, P2P matrices, configuration hash, hostname, and UTC
timestamp.

Resolve one action without mutation:

```bash
conda run -n aidrbench python -m aidrbench hil dry-run-action \
  --config configs/hardware/four_gpu_node.yaml \
  --action 0 \
  --restore-manifest results/safety/gpu_restore_manifest.json \
  --audit-log results/safety/actuator_audit.jsonl
```

Dry-run a generated mixed-workload plan without launching processes or
sleeping:

```bash
conda run -n aidrbench python -m aidrbench calibrate dry-run-plan \
  --plan results/calibration/screening_plan.csv \
  --config configs/hardware/four_gpu_node.yaml \
  --output results/calibration/screening_dry_run.json \
  --restore-manifest results/safety/gpu_restore_manifest.json \
  --audit-log results/safety/actuator_audit.jsonl
```

## Restoration and watchdog

Verification is the default and does not mutate hardware:

```bash
scripts/restore_gpu_power.sh \
  --manifest results/safety/gpu_restore_manifest.json
```

Emergency restoration requires both explicit flags and still verifies every
GPU UUID before applying the captured defaults:

```bash
scripts/restore_gpu_power.sh \
  --manifest results/safety/gpu_restore_manifest.json \
  --execute \
  --acknowledge-hardware-mutation
```

`aidrbench hil watchdog` is intended to run as an independent supervisor
process. It watches an atomically replaced monotonic heartbeat file and invokes
the same restore path once if the controller heartbeat is missing or stale. A
clean `status: stopped` heartbeat exits without restoration.

Real P2 execution remains disabled until the concrete vLLM/AIPerf and batch
worker backend is implemented, the temperature threshold is chosen from an
observed thermal soak test, and the external watchdog launch is integrated.
