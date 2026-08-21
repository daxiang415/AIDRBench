#!/usr/bin/env bash
set -euo pipefail

output_directory="${1:-results/calibration/rtx6000pro_4gpu_v1/raw}"
aidrbench_bin="/home/user/miniconda3/envs/aidrbench/bin/aidrbench"
torchrun_bin="/home/user/miniconda3/envs/aidrbench/bin/torchrun"
workload_script="scripts/gpu_power_workload.py"
telemetry_pid=""

mkdir -p "$output_directory"

cleanup() {
  if [[ -n "$telemetry_pid" ]]; then
    kill "$telemetry_pid" 2>/dev/null || true
    wait "$telemetry_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

for mode in training offline_inference; do
  for gpu_count in 1 4; do
    if [[ "$gpu_count" == "1" ]]; then
      visible_devices="0"
      physical_ids=(0)
    else
      visible_devices="0,1,2,3"
      physical_ids=(0 1 2 3)
    fi
    for repeat in 1 2 3; do
      stem="${mode}_${gpu_count}gpu_repeat${repeat}"
      echo "START $stem"
      "$aidrbench_bin" calibrate collect-telemetry \
        --output "$output_directory/${stem}_telemetry.parquet" \
        --duration-seconds 28 \
        --interval-seconds 1 &
      telemetry_pid="$!"
      sleep 2
      CUDA_VISIBLE_DEVICES="$visible_devices" "$torchrun_bin" \
        --standalone \
        --nproc-per-node="$gpu_count" \
        "$workload_script" \
        --mode "$mode" \
        --physical-gpu-ids "${physical_ids[@]}" \
        --matrix-size 8192 \
        --warmup-seconds 5 \
        --measurement-seconds 20 \
        --seed "$((2026 + repeat))" \
        --output "$output_directory/${stem}_workload.json"
      wait "$telemetry_pid"
      telemetry_pid=""
      echo "DONE $stem"
      sleep 3
    done
  done
done

echo "CALIBRATION_RUNS_COMPLETE"
