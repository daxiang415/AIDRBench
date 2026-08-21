# RTX PRO 6000 four-GPU calibration v1

Updated: 2026-08-17.

## Scope

This bounded calibration supports the hourly demand-response power model. It
does not change GPU clocks or power limits and does not attempt a thermal or
DVFS response surface.

Hardware:

- 4× NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition;
- 300 W reported power limit per GPU;
- PCIe `NODE` paths between GPUs, with no NVLink reported by `nvidia-smi topo`.

Workloads:

- `training`: BF16 8192×8192 forward/backward work plus NCCL gradient
  all-reduce for the four-GPU condition;
- `offline_inference`: BF16 8192×8192 batched forward work without
  inter-GPU communication;
- 1-GPU and 4-GPU conditions, three repeats each;
- five-second warm-up and twenty-second measurement windows;
- one-second read-only `nvidia-smi` telemetry;
- repeats 1–2 fit parameters and repeat 3 is held out.

## Fitted values

| Parameter | Nominal | 95% t interval |
| --- | ---: | ---: |
| GPU idle power | 13.94 W/GPU | 5.86–22.01 W/GPU |
| Four-GPU training active power | 259.08 W/GPU | 249.22–268.94 W/GPU |
| Four-GPU offline-inference active power | 300.02 W/GPU | 299.96–300.09 W/GPU |
| Node fixed overhead | 300 W/node | 150–450 W/node |

The combined active-power held-out MAE is 4.47 W/GPU. Training held-out MAE is
8.91 W/GPU, while offline inference held-out MAE is 0.03 W/GPU.

The training result captures a material topology effect: single-GPU training
reaches approximately 300 W, while four-GPU training averages approximately
259 W/GPU because the synchronized workload spends time in PCIe/NCCL gradient
communication. Four-GPU offline inference remains at the 300 W power limit.

## Evidence limitation

GPU power is measured, but the host exposes no accessible BMC/DCMI device and
RAPL/turbostat requires unavailable privileged MSR access. Consequently the
node CPU, memory and fan term is an explicit assumption inherited from the
declared 300 W baseline, with a deliberately broad interval. The complete
artifact is therefore labelled `benchmark_anchored_synthetic`, not `measured`.

The artifact, fitted per-run summaries and identifier-redacted raw telemetry
are under `data/calibration/`. The private source files remain ignored under
`results/calibration/rtx6000pro_4gpu_v1/raw/`; public telemetry replaces GPU
UUIDs and the host name without changing any measurement value.
