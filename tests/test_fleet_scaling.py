from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aidrbench.cli import main
from aidrbench.datacenter.hardware import ComputeWorkload, EvidenceClass, load_gpu_profile
from aidrbench.datacenter.power_model import (
    ControlResponseCurve,
    NodeControlInput,
    NodeOperatingBaseline,
)
from aidrbench.datacenter.scaling import (
    CapacityRequest,
    NodeTopology,
    aggregate_homogeneous_fleet,
    compare_capacity_options,
    plan_capacity,
)


class FleetScalingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.scenario = cls.root / "configs/fleet/illustrative_10mw_70b_decode.yaml"

    def test_capacity_comparison_selects_feasible_h200_profile(self) -> None:
        result = compare_capacity_options(self.scenario)
        self.assertEqual(result.selected_profile_id, "nvidia_h200_sxm_141gb_spec_v1")
        self.assertEqual(len(result.plans), 2)
        self.assertTrue(all(plan.feasible for plan in result.plans))
        h100, h200 = result.plans
        self.assertGreater(h100.deployed_nodes, h200.deployed_nodes)
        self.assertEqual(h200.evidence_class, EvidenceClass.SPEC_DERIVED_SYNTHETIC)

    def test_power_budget_can_make_service_target_infeasible(self) -> None:
        profile = load_gpu_profile(
            self.root / "configs/hardware/gpu_profiles/h200_sxm_141gb.yaml"
        )
        workload = ComputeWorkload(
            workload_id="small",
            model_id="small",
            work_unit="token",
            flops_per_work_unit=1e12,
            hbm_bytes_per_work_unit=1e12,
            communication_bytes_per_work_unit=0.0,
            model_memory_gb=1.0,
            compute_efficiency=0.5,
            memory_efficiency=0.5,
            communication_efficiency=1.0,
            memory_reserve_fraction=0.9,
            evidence_class=EvidenceClass.SPEC_DERIVED_SYNTHETIC,
            notes=(),
        )
        plan = plan_capacity(
            profile,
            workload,
            NodeTopology(8, 4, 4, 1600.0),
            CapacityRequest(0.001, 1_000_000.0, 0.75, 1.2),
        )
        self.assertFalse(plan.feasible)
        self.assertEqual(plan.deployed_nodes, 0)
        self.assertIsNotNone(plan.infeasible_reason)

    def test_homogeneous_aggregation_splits_demand_and_sums_extensive_values(self) -> None:
        curve = ControlResponseCurve(
            cap_ratios=(0.7, 1.0),
            dynamic_power_ratios=(0.6, 1.0),
            service_ratios=(0.8, 1.0),
            latency_ratios=(1.25, 1.0),
            evidence_class=EvidenceClass.MEASURED,
            source="test fixture",
        )
        baseline = NodeOperatingBaseline(
            host_idle_power_w=100.0,
            inference_gpu_count=2,
            batch_gpu_count=2,
            inference_gpu_idle_power_w=20.0,
            batch_gpu_idle_power_w=10.0,
            inference_gpu_dynamic_power_w=100.0,
            batch_gpu_dynamic_power_w=80.0,
            inference_capacity_per_second=200.0,
            batch_capacity_per_gpu_second=100.0,
            ttft_p99_ms=20.0,
            tpot_p99_ms=4.0,
            load_power_exponent=1.0,
            evidence_class=EvidenceClass.MEASURED,
            source="test fixture",
        )
        result = aggregate_homogeneous_fleet(
            virtual_nodes=10,
            pue=1.2,
            baseline=baseline,
            inference_curve=curve,
            batch_curve=curve,
            fleet_control=NodeControlInput(2000.0, 1000.0, 0.7, 0.7, 1),
        )
        self.assertAlmostEqual(result.inference_capacity_per_second, 1600.0)
        self.assertAlmostEqual(result.inference_unserved_per_second, 400.0)
        self.assertAlmostEqual(result.batch_unserved_per_second, 200.0)
        self.assertAlmostEqual(result.facility_power_w, result.it_power_w * 1.2)
        self.assertEqual(result.evidence_class, EvidenceClass.HOMOGENEOUS_SCALED)

    def test_cli_writes_machine_readable_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.json"
            exit_code = main(
                [
                    "fleet",
                    "plan-capacity",
                    "--config",
                    str(self.scenario),
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("spec_derived_synthetic", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
