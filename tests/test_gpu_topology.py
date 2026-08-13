from __future__ import annotations

from dataclasses import replace

from aidrbench.hil.topology import (
    TopologySnapshot,
    check_inference_topology,
    parse_topology_matrix,
)

TOPOLOGY = """
        GPU0    GPU1    GPU2    GPU3    CPU Affinity   NUMA Affinity
GPU0     X      NODE    NODE    NODE    0-63           0
GPU1    NODE     X      NODE    NODE    0-63           0
GPU2    NODE    NODE     X      NODE    0-63           0
GPU3    NODE    NODE    NODE     X      0-63           0

Legend:
"""

P2P_OK = """
        GPU0    GPU1    GPU2    GPU3
GPU0     X       OK      OK      OK
GPU1     OK      X       OK      OK
GPU2     OK      OK      X       OK
GPU3     OK      OK      OK      X

Legend:
"""


def test_parse_topology_ignores_affinity_columns() -> None:
    matrix = parse_topology_matrix(TOPOLOGY)
    assert matrix.gpu_ids == (0, 1, 2, 3)
    assert matrix.get(0, 1) == "NODE"
    assert matrix.get(3, 3) == "X"


def test_inference_pair_is_p2p_capable_but_not_nvlink() -> None:
    snapshot = TopologySnapshot(
        links=parse_topology_matrix(TOPOLOGY),
        p2p_read=parse_topology_matrix(P2P_OK),
        p2p_write=parse_topology_matrix(P2P_OK),
        raw_links=TOPOLOGY,
        raw_p2p_read=P2P_OK,
        raw_p2p_write=P2P_OK,
    )
    result = check_inference_topology(snapshot, (0, 1), require_p2p=True)
    assert result.valid
    assert result.p2p_read_write_ok
    assert result.pair_paths == ("GPU0-GPU1:NODE",)
    assert any("not NVLink" in warning for warning in result.warnings)


def test_required_p2p_failure_blocks_topology() -> None:
    links = parse_topology_matrix(TOPOLOGY)
    p2p = parse_topology_matrix(P2P_OK)
    rows = list(p2p.values)
    rows[0] = ("X", "NS", "OK", "OK")
    failed = replace(p2p, values=tuple(rows))
    snapshot = TopologySnapshot(links, failed, p2p, TOPOLOGY, P2P_OK, P2P_OK)
    result = check_inference_topology(snapshot, (0, 1), require_p2p=True)
    assert not result.valid
    assert not result.p2p_read_write_ok
    assert any("P2P" in error for error in result.errors)
