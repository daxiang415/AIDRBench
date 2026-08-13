from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from aidrbench.datacenter.hardware import (
    ComputeWorkload,
    EvidenceClass,
    estimate_roofline_capacity,
    load_gpu_profile,
)


class HardwareProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.h100 = load_gpu_profile(
            root / "configs/hardware/gpu_profiles/h100_sxm_80gb.yaml"
        )
        cls.h200 = load_gpu_profile(
            root / "configs/hardware/gpu_profiles/h200_sxm_141gb.yaml"
        )
        cls.workload = ComputeWorkload(
            workload_id="dense-decode",
            model_id="dense-70b",
            work_unit="decode_token",
            flops_per_work_unit=140e9,
            hbm_bytes_per_work_unit=140e9,
            communication_bytes_per_work_unit=0.0,
            model_memory_gb=140.0,
            compute_efficiency=0.35,
            memory_efficiency=0.65,
            communication_efficiency=0.5,
            memory_reserve_fraction=0.90,
            evidence_class=EvidenceClass.SPEC_DERIVED_SYNTHETIC,
            notes=(),
        )

    def test_profiles_are_explicit_spec_derived_skus(self) -> None:
        self.assertEqual(self.h100.model, "H100 SXM 80GB")
        self.assertEqual(self.h200.model, "H200 SXM 141GB")
        self.assertEqual(self.h100.evidence_class, EvidenceClass.SPEC_DERIVED_SYNTHETIC)
        self.assertEqual(self.h200.evidence_class, EvidenceClass.SPEC_DERIVED_SYNTHETIC)
        self.assertGreater(self.h200.memory_bandwidth_tb_s, self.h100.memory_bandwidth_tb_s)

    def test_roofline_reports_memory_bottleneck_and_provenance(self) -> None:
        h100 = estimate_roofline_capacity(self.h100, self.workload, gpu_count=4)
        h200 = estimate_roofline_capacity(self.h200, self.workload, gpu_count=4)
        self.assertEqual(h100.bottleneck, "memory")
        self.assertEqual(h200.bottleneck, "memory")
        self.assertGreater(h200.work_units_per_second, h100.work_units_per_second)
        self.assertEqual(h200.evidence_class, EvidenceClass.SPEC_DERIVED_SYNTHETIC)
        self.assertTrue(any("not a serving benchmark" in item for item in h200.warnings))

    def test_model_memory_constraint_is_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "model requires"):
            estimate_roofline_capacity(self.h100, self.workload, gpu_count=1)

    def test_communication_time_reduces_multi_gpu_capacity(self) -> None:
        without_communication = estimate_roofline_capacity(
            self.h200, self.workload, gpu_count=4
        )
        communication_workload = replace(
            self.workload,
            communication_bytes_per_work_unit=2e9,
            communication_efficiency=0.5,
        )
        with_communication = estimate_roofline_capacity(
            self.h200,
            communication_workload,
            gpu_count=4,
        )
        self.assertIsNotNone(with_communication.communication_ceiling_per_second)
        self.assertGreater(with_communication.communication_time_per_work_unit_s, 0.0)
        self.assertLess(
            with_communication.work_units_per_second,
            without_communication.work_units_per_second,
        )

    def test_efficiency_cannot_exceed_one(self) -> None:
        with self.assertRaisesRegex(ValueError, "compute_efficiency"):
            ComputeWorkload(
                workload_id="invalid",
                model_id="invalid",
                work_unit="token",
                flops_per_work_unit=1.0,
                hbm_bytes_per_work_unit=1.0,
                communication_bytes_per_work_unit=0.0,
                model_memory_gb=1.0,
                compute_efficiency=1.1,
                memory_efficiency=1.0,
                communication_efficiency=1.0,
                memory_reserve_fraction=0.9,
                evidence_class=EvidenceClass.SPEC_DERIVED_SYNTHETIC,
                notes=(),
            )


if __name__ == "__main__":
    unittest.main()
