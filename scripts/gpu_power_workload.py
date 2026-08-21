#!/usr/bin/env python3
"""Run a bounded, metadata-rich GPU workload for power calibration.

Launch with ``torchrun``.  The script never changes clocks or power limits.
Training performs BF16 forward/backward matrix work and, for multi-GPU runs,
an NCCL gradient all-reduce. Offline inference performs BF16 batched forward
matrix work without communication.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import torch
import torch.distributed as dist

WorkloadMode = Literal["training", "offline_inference"]


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed < float("inf"):
        raise argparse.ArgumentTypeError("value must be finite and non-negative")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not 0.0 < parsed < float("inf"):
        raise argparse.ArgumentTypeError("value must be finite and positive")
    return parsed


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _training_step(left: torch.Tensor, weight: torch.Tensor, world_size: int) -> None:
    prediction = torch.mm(left, weight)
    loss = prediction.float().square().mean()
    loss.backward()
    if weight.grad is None:
        raise RuntimeError("training workload produced no gradient")
    if world_size > 1:
        dist.all_reduce(weight.grad, op=dist.ReduceOp.SUM)
    weight.grad = None


def _inference_step(
    left: torch.Tensor,
    weight: torch.Tensor,
    output: torch.Tensor,
    _world_size: int,
) -> None:
    torch.mm(left, weight, out=output)


def _run_for_seconds(
    operation: Any,
    left: torch.Tensor,
    weight: torch.Tensor,
    output: torch.Tensor | None,
    *,
    world_size: int,
    duration_seconds: float,
) -> int:
    deadline = time.monotonic() + duration_seconds
    iterations = 0
    while time.monotonic() < deadline:
        if output is None:
            operation(left, weight, world_size)
        else:
            operation(left, weight, output, world_size)
        torch.cuda.synchronize()
        iterations += 1
    return iterations


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    local_rank = int(os.environ["LOCAL_RANK"])
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if len(args.physical_gpu_ids) != world_size:
        raise ValueError("physical GPU ID count must equal WORLD_SIZE")
    torch.cuda.set_device(local_rank)
    dist.init_process_group(
        backend="nccl",
        device_id=torch.device("cuda", local_rank),
    )
    try:
        torch.manual_seed(args.seed + rank)
        device = torch.device("cuda", local_rank)
        dtype = torch.bfloat16
        left = torch.randn((args.matrix_size, args.matrix_size), device=device, dtype=dtype)
        weight = torch.randn(
            (args.matrix_size, args.matrix_size),
            device=device,
            dtype=dtype,
            requires_grad=args.mode == "training",
        )
        output = (
            None
            if args.mode == "training"
            else torch.empty_like(left, requires_grad=False)
        )
        operation = _training_step if args.mode == "training" else _inference_step

        _run_for_seconds(
            operation,
            left,
            weight,
            output,
            world_size=world_size,
            duration_seconds=args.warmup_seconds,
        )
        dist.barrier()
        started_at_utc = _utc_now()
        started_monotonic = time.monotonic()
        iterations = _run_for_seconds(
            operation,
            left,
            weight,
            output,
            world_size=world_size,
            duration_seconds=args.measurement_seconds,
        )
        torch.cuda.synchronize()
        dist.barrier()
        elapsed_seconds = time.monotonic() - started_monotonic
        ended_at_utc = _utc_now()
        local_result = {
            "rank": rank,
            "local_rank": local_rank,
            "physical_gpu_id": args.physical_gpu_ids[rank],
            "iterations": iterations,
            "elapsed_seconds": elapsed_seconds,
            "iterations_per_second": iterations / elapsed_seconds,
            "started_at_utc": started_at_utc,
            "ended_at_utc": ended_at_utc,
            "device_name": torch.cuda.get_device_name(local_rank),
            "peak_memory_allocated_bytes": torch.cuda.max_memory_allocated(local_rank),
        }
        gathered: list[dict[str, Any] | None] = [None] * world_size
        dist.all_gather_object(gathered, local_result)
        if rank == 0:
            payload = {
                "schema_version": 1,
                "benchmark": "aidrbench_gpu_power_workload",
                "evidence_class": "measured",
                "power_limit_changed": False,
                "mode": args.mode,
                "operation": (
                    "bf16_forward_backward_with_gradient_all_reduce"
                    if args.mode == "training"
                    else "bf16_batched_forward"
                ),
                "matrix_size": args.matrix_size,
                "dtype": "bfloat16",
                "world_size": world_size,
                "physical_gpu_ids": args.physical_gpu_ids,
                "warmup_seconds": args.warmup_seconds,
                "requested_measurement_seconds": args.measurement_seconds,
                "seed": args.seed,
                "hostname": socket.gethostname(),
                "torch_version": torch.__version__,
                "cuda_version": torch.version.cuda,
                "nccl_version": torch.cuda.nccl.version(),
                "ranks": gathered,
            }
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(payload, ensure_ascii=False))
    finally:
        dist.destroy_process_group()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("training", "offline_inference"), required=True)
    parser.add_argument("--physical-gpu-ids", type=int, nargs="+", required=True)
    parser.add_argument("--matrix-size", type=_positive_int, default=8192)
    parser.add_argument("--warmup-seconds", type=_non_negative_float, default=5.0)
    parser.add_argument("--measurement-seconds", type=_positive_float, default=30.0)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", required=True)
    return parser


if __name__ == "__main__":
    run(build_parser().parse_args())
