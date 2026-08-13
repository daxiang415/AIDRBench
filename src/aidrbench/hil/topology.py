"""Read-only GPU topology and P2P capability checks."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from itertools import combinations
from typing import Protocol

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_GPU_LABEL = re.compile(r"GPU([0-9]+)")


class TopologyError(RuntimeError):
    """Raised when GPU topology cannot be parsed or verified."""


@dataclass(frozen=True, slots=True)
class TopologyMatrix:
    """Square GPU-to-GPU matrix returned by nvidia-smi topo."""

    gpu_ids: tuple[int, ...]
    values: tuple[tuple[str, ...], ...]

    def get(self, source_gpu_id: int, target_gpu_id: int) -> str:
        try:
            row = self.gpu_ids.index(source_gpu_id)
            column = self.gpu_ids.index(target_gpu_id)
        except ValueError as exc:
            raise TopologyError("GPU ID is absent from the topology matrix") from exc
        return self.values[row][column]


@dataclass(frozen=True, slots=True)
class TopologySnapshot:
    """Link path plus P2P read/write matrices captured at preflight."""

    links: TopologyMatrix
    p2p_read: TopologyMatrix
    p2p_write: TopologyMatrix
    raw_links: str
    raw_p2p_read: str
    raw_p2p_write: str


@dataclass(frozen=True, slots=True)
class InferenceTopologyCheck:
    """Decision record for the GPUs that jointly serve one model."""

    valid: bool
    pair_paths: tuple[str, ...]
    p2p_read_write_ok: bool
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


class TopologyBackend(Protocol):
    def query_topology(self) -> TopologySnapshot: ...


def parse_topology_matrix(output: str) -> TopologyMatrix:
    """Parse the leading square matrix while ignoring affinity/legend columns."""

    clean = _ANSI_ESCAPE.sub("", output)
    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    header_index: int | None = None
    gpu_labels: list[str] = []
    for index, line in enumerate(lines):
        tokens = line.split()
        labels = [token for token in tokens if _GPU_LABEL.fullmatch(token)]
        if len(labels) >= 1 and tokens[: len(labels)] == labels:
            header_index = index
            gpu_labels = labels
            break
    if header_index is None or not gpu_labels:
        raise TopologyError("topology output has no GPU matrix header")
    gpu_ids = tuple(int(_GPU_LABEL.fullmatch(label).group(1)) for label in gpu_labels)  # type: ignore[union-attr]
    rows: dict[int, tuple[str, ...]] = {}
    for line in lines[header_index + 1 :]:
        tokens = line.split()
        if not tokens or _GPU_LABEL.fullmatch(tokens[0]) is None:
            if rows:
                break
            continue
        source_id = int(tokens[0][3:])
        if len(tokens) < len(gpu_ids) + 1:
            raise TopologyError(f"topology row GPU{source_id} is incomplete")
        rows[source_id] = tuple(tokens[1 : len(gpu_ids) + 1])
        if len(rows) == len(gpu_ids):
            break
    if set(rows) != set(gpu_ids):
        raise TopologyError("topology matrix does not contain every header GPU")
    return TopologyMatrix(
        gpu_ids=gpu_ids,
        values=tuple(rows[gpu_id] for gpu_id in gpu_ids),
    )


class NvidiaSmiTopologyBackend:
    """Read-only, no-shell topology probe."""

    def __init__(self, executable: str = "nvidia-smi", *, timeout_seconds: float = 5.0) -> None:
        if not executable:
            raise ValueError("nvidia-smi executable must not be empty")
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def _run(self, arguments: list[str]) -> str:
        try:
            completed = subprocess.run(
                [self.executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise TopologyError(f"executable not found: {self.executable}") from exc
        except subprocess.TimeoutExpired as exc:
            raise TopologyError("nvidia-smi topology query timed out") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
            raise TopologyError(
                f"nvidia-smi topology query failed with exit code "
                f"{completed.returncode}: {detail}"
            )
        return completed.stdout

    def query_topology(self) -> TopologySnapshot:
        links = self._run(["topo", "-m"])
        p2p_read = self._run(["topo", "-p2p", "r"])
        p2p_write = self._run(["topo", "-p2p", "w"])
        return TopologySnapshot(
            links=parse_topology_matrix(links),
            p2p_read=parse_topology_matrix(p2p_read),
            p2p_write=parse_topology_matrix(p2p_write),
            raw_links=links,
            raw_p2p_read=p2p_read,
            raw_p2p_write=p2p_write,
        )


def check_inference_topology(
    snapshot: TopologySnapshot,
    inference_gpu_ids: tuple[int, ...],
    *,
    require_p2p: bool,
) -> InferenceTopologyCheck:
    """Check every inference-pool pair without assuming NVLink exists."""

    expected_ids = set(snapshot.links.gpu_ids)
    matrix_ids = (
        set(snapshot.p2p_read.gpu_ids),
        set(snapshot.p2p_write.gpu_ids),
    )
    errors: list[str] = []
    warnings: list[str] = []
    if any(ids != expected_ids for ids in matrix_ids):
        errors.append("topology and P2P matrices contain different GPU IDs")
    missing = sorted(set(inference_gpu_ids) - expected_ids)
    if missing:
        errors.append(f"inference GPU IDs missing from topology: {missing}")
    pair_paths: list[str] = []
    p2p_ok = True
    if not missing:
        for source, target in combinations(inference_gpu_ids, 2):
            path = snapshot.links.get(source, target)
            read = snapshot.p2p_read.get(source, target)
            write = snapshot.p2p_write.get(source, target)
            pair_paths.append(f"GPU{source}-GPU{target}:{path}")
            if read != "OK" or write != "OK":
                p2p_ok = False
                if require_p2p:
                    errors.append(
                        f"GPU{source}-GPU{target} P2P read/write is {read}/{write}"
                    )
            if not path.startswith("NV"):
                warnings.append(
                    f"GPU{source}-GPU{target} uses {path}, not NVLink; "
                    "tensor-parallel communication must be measured"
                )
    return InferenceTopologyCheck(
        valid=not errors,
        pair_paths=tuple(pair_paths),
        p2p_read_write_ok=p2p_ok,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
