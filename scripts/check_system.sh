#!/usr/bin/env bash
set -u

# Read-only P0 inventory. This script never installs software or changes GPU state.
run_if_available() {
  local command_name="$1"
  shift
  if command -v "$command_name" >/dev/null 2>&1; then
    "$command_name" "$@"
  else
    echo "[missing] $command_name"
  fi
}

echo "[system] kernel"
run_if_available uname -a
echo "[system] operating system"
run_if_available lsb_release -a
echo "[system] cpu"
run_if_available lscpu
echo "[system] memory"
run_if_available free -h
echo "[system] storage"
run_if_available lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
echo "[tool] python"
run_if_available python3 --version
echo "[tool] uv"
run_if_available uv --version
echo "[tool] docker"
run_if_available docker --version
echo "[gpu] inventory"
run_if_available nvidia-smi -L
echo "[gpu] topology"
run_if_available nvidia-smi topo -m
echo "[gpu] power limits (read only)"
run_if_available nvidia-smi -q -d POWER
