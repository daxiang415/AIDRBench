#!/usr/bin/env python3
"""Minimal CUDA/NCCL calibration probes for cross-hardware scaling.

Run this inside an image that provides PyTorch with CUDA support. The script
does not change clocks or power limits. It emits raw measurements and runtime
metadata as JSON so later scaling code can keep measurements separate from GPU
specification assumptions.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive finite number")
    return parsed


def _write_json(payload: dict[str, Any], output: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _runtime_metadata() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "nccl_version": torch.cuda.nccl.version(),
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _device_metadata(device_index: int) -> dict[str, Any]:
    properties = torch.cuda.get_device_properties(device_index)
    return {
        "visible_device_index": device_index,
        "name": properties.name,
        "total_memory_bytes": properties.total_memory,
        "compute_capability": [properties.major, properties.minor],
        "multi_processor_count": properties.multi_processor_count,
    }


def _elapsed_seconds(operation: Callable[[], None], repetitions: int) -> float:
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(repetitions):
        operation()
    end.record()
    end.synchronize()
    return float(start.elapsed_time(end)) / 1_000.0


def _timed_for_duration(
    operation: Callable[[], None],
    *,
    warmups: int,
    target_seconds: float,
    calibration_repetitions: int,
) -> tuple[float, int]:
    for _ in range(warmups):
        operation()
    torch.cuda.synchronize()
    calibration_seconds = _elapsed_seconds(operation, calibration_repetitions)
    if calibration_seconds <= 0:
        raise RuntimeError("CUDA event timer returned a non-positive duration")
    repetitions = max(
        calibration_repetitions,
        math.ceil(target_seconds * calibration_repetitions / calibration_seconds),
    )
    return _elapsed_seconds(operation, repetitions), repetitions


def run_local(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    torch.cuda.set_device(0)
    device = torch.device("cuda", 0)
    dtype = torch.bfloat16
    torch.manual_seed(args.seed)

    matrix_size = args.matrix_size
    left = torch.randn((matrix_size, matrix_size), device=device, dtype=dtype)
    right = torch.randn((matrix_size, matrix_size), device=device, dtype=dtype)
    result = torch.empty_like(left)

    def matrix_multiply() -> None:
        torch.mm(left, right, out=result)

    compute_started_at_utc = _utc_now()
    compute_seconds, compute_repetitions = _timed_for_duration(
        matrix_multiply,
        warmups=args.warmups,
        target_seconds=args.duration_seconds,
        calibration_repetitions=5,
    )
    compute_ended_at_utc = _utc_now()
    operations = 2.0 * matrix_size**3 * compute_repetitions
    achieved_tflops = operations / compute_seconds / 1_000_000_000_000.0

    element_size = torch.empty((), dtype=dtype).element_size()
    memory_bytes = args.memory_mib * 1024 * 1024
    element_count = memory_bytes // element_size
    source = torch.empty(element_count, device=device, dtype=dtype)
    destination = torch.empty_like(source)
    source.fill_(1)

    def memory_copy() -> None:
        destination.copy_(source)

    memory_started_at_utc = _utc_now()
    memory_seconds, memory_repetitions = _timed_for_duration(
        memory_copy,
        warmups=args.warmups,
        target_seconds=args.duration_seconds,
        calibration_repetitions=10,
    )
    memory_ended_at_utc = _utc_now()
    moved_bytes = 2.0 * element_count * element_size * memory_repetitions
    memory_bandwidth_gb_s = moved_bytes / memory_seconds / 1_000_000_000.0

    payload = {
        "schema_version": 1,
        "benchmark": "aidrbench_gpu_local_microbench",
        "evidence_class": "measured",
        "power_limit_changed": False,
        "physical_gpu_id": args.physical_gpu_id,
        "runtime": _runtime_metadata(),
        "device": _device_metadata(0),
        "compute": {
            "operation": "dense_matrix_multiply",
            "dtype": "bfloat16",
            "matrix_shape": [matrix_size, matrix_size],
            "started_at_utc": compute_started_at_utc,
            "ended_at_utc": compute_ended_at_utc,
            "warmups": args.warmups,
            "repetitions": compute_repetitions,
            "elapsed_seconds": compute_seconds,
            "achieved_tflops": achieved_tflops,
        },
        "memory": {
            "operation": "device_to_device_copy",
            "dtype": "bfloat16",
            "buffer_bytes": element_count * element_size,
            "traffic_definition": "source read plus destination write",
            "started_at_utc": memory_started_at_utc,
            "ended_at_utc": memory_ended_at_utc,
            "warmups": args.warmups,
            "repetitions": memory_repetitions,
            "elapsed_seconds": memory_seconds,
            "achieved_bandwidth_gb_s": memory_bandwidth_gb_s,
        },
    }
    _write_json(payload, args.output)
    print(json.dumps(payload, ensure_ascii=False))


def _message_sizes(value: str) -> list[int]:
    result: list[int] = []
    for item in value.split(","):
        size = _positive_int(item.strip())
        if size in result:
            raise argparse.ArgumentTypeError(f"duplicate message size: {size}")
        result.append(size)
    return result


def _all_reduce_time(tensor: torch.Tensor, repetitions: int) -> float:
    dist.barrier()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(repetitions):
        dist.all_reduce(tensor)
    end.record()
    end.synchronize()
    local_seconds = float(start.elapsed_time(end)) / 1_000.0
    measured = torch.tensor([local_seconds], device=tensor.device, dtype=torch.float64)
    dist.all_reduce(measured, op=dist.ReduceOp.MAX)
    return float(measured.item())


def run_distributed(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    local_rank = int(os.environ["LOCAL_RANK"])
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if len(args.physical_gpu_ids) != world_size:
        raise ValueError("physical GPU ID count must equal WORLD_SIZE")
    if len(set(args.physical_gpu_ids)) != world_size or any(
        gpu_id < 0 for gpu_id in args.physical_gpu_ids
    ):
        raise ValueError("physical GPU IDs must be distinct non-negative integers")
    torch.cuda.set_device(local_rank)
    dist.init_process_group(backend="nccl")
    try:
        devices: list[dict[str, Any] | None] = [None] * world_size
        dist.all_gather_object(devices, _device_metadata(local_rank))
        measurements: list[dict[str, Any]] = []
        for message_mib in args.message_mib:
            message_bytes = message_mib * 1024 * 1024
            element_count = message_bytes // 4
            tensor = torch.ones(element_count, device=local_rank, dtype=torch.float32)
            for _ in range(args.warmups):
                dist.all_reduce(tensor)
            started_at_utc = _utc_now()
            elapsed_seconds = _all_reduce_time(tensor, args.iterations)
            ended_at_utc = _utc_now()
            latency_seconds = elapsed_seconds / args.iterations
            algorithmic_bandwidth = message_bytes / latency_seconds / 1_000_000_000.0
            bus_bandwidth = algorithmic_bandwidth * 2.0 * (world_size - 1) / world_size
            measurements.append(
                {
                    "message_mib": message_mib,
                    "message_bytes": message_bytes,
                    "iterations": args.iterations,
                    "started_at_utc": started_at_utc,
                    "ended_at_utc": ended_at_utc,
                    "elapsed_seconds_max_rank": elapsed_seconds,
                    "latency_ms": latency_seconds * 1_000.0,
                    "algorithmic_bandwidth_gb_s": algorithmic_bandwidth,
                    "bus_bandwidth_gb_s": bus_bandwidth,
                }
            )
            del tensor
            torch.cuda.empty_cache()

        if rank == 0:
            payload = {
                "schema_version": 1,
                "benchmark": "aidrbench_nccl_all_reduce_microbench",
                "evidence_class": "measured",
                "power_limit_changed": False,
                "world_size": world_size,
                "physical_gpu_ids": args.physical_gpu_ids,
                "runtime": _runtime_metadata(),
                "devices": devices,
                "collective": "all_reduce_sum",
                "dtype": "float32",
                "warmups": args.warmups,
                "measurements": measurements,
            }
            _write_json(payload, args.output)
            print(json.dumps(payload, ensure_ascii=False))
    finally:
        dist.destroy_process_group()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    local = commands.add_parser("local", help="measure BF16 GEMM and device memory copy")
    local.add_argument("--physical-gpu-id", type=int, required=True)
    local.add_argument("--matrix-size", type=_positive_int, default=8192)
    local.add_argument("--memory-mib", type=_positive_int, default=4096)
    local.add_argument("--duration-seconds", type=_positive_float, default=5.0)
    local.add_argument("--warmups", type=_positive_int, default=10)
    local.add_argument("--seed", type=int, default=42)
    local.add_argument("--output", required=True)
    local.set_defaults(function=run_local)

    distributed = commands.add_parser("distributed", help="measure NCCL all-reduce")
    distributed.add_argument("--physical-gpu-ids", type=int, nargs="+", required=True)
    distributed.add_argument("--message-mib", type=_message_sizes, default=[1, 16, 256, 1024])
    distributed.add_argument("--iterations", type=_positive_int, default=50)
    distributed.add_argument("--warmups", type=_positive_int, default=10)
    distributed.add_argument("--output", required=True)
    distributed.set_defaults(function=run_distributed)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
