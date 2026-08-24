"""Evidence labels shared by formal calibration artifacts."""

from enum import StrEnum


class EvidenceClass(StrEnum):
    """Provenance class for measured and explicitly modelled quantities."""

    MEASURED = "measured"
    HOMOGENEOUS_SCALED = "homogeneous_scaled"
    BENCHMARK_ANCHORED_SYNTHETIC = "benchmark_anchored_synthetic"
    SPEC_DERIVED_SYNTHETIC = "spec_derived_synthetic"
