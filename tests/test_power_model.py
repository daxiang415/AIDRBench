from __future__ import annotations

import unittest

from aidrbench.datacenter.hardware import EvidenceClass
from aidrbench.datacenter.power_model import (
    ControlResponseCurve,
    NodeControlInput,
    NodeOperatingBaseline,
    predict_node_response,
)


class PowerModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.curve = ControlResponseCurve(
            cap_ratios=(0.7, 1.0),
            dynamic_power_ratios=(0.6, 1.0),
            service_ratios=(0.8, 1.0),
            latency_ratios=(1.25, 1.0),
            evidence_class=EvidenceClass.MEASURED,
            source="test fixture",
        )
        self.baseline = NodeOperatingBaseline(
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

    def test_curve_interpolates_only_inside_calibrated_domain(self) -> None:
        point = self.curve.at(0.85)
        self.assertAlmostEqual(point.dynamic_power_ratio, 0.8)
        self.assertAlmostEqual(point.service_ratio, 0.9)
        self.assertAlmostEqual(point.latency_ratio, 1.125)
        with self.assertRaisesRegex(ValueError, "outside the calibrated range"):
            self.curve.at(0.6)

    def test_node_prediction_conserves_work_and_keeps_idle_power(self) -> None:
        prediction = predict_node_response(
            self.baseline,
            self.curve,
            self.curve,
            NodeControlInput(
                inference_demand_per_second=200.0,
                batch_demand_per_second=100.0,
                inference_cap_ratio=0.7,
                batch_cap_ratio=0.7,
                active_batch_gpus=1,
            ),
        )
        self.assertAlmostEqual(prediction.inference_capacity_per_second, 160.0)
        self.assertAlmostEqual(prediction.inference_served_per_second, 160.0)
        self.assertAlmostEqual(prediction.inference_unserved_per_second, 40.0)
        self.assertAlmostEqual(prediction.batch_capacity_per_second, 80.0)
        self.assertAlmostEqual(prediction.batch_unserved_per_second, 20.0)
        self.assertGreater(prediction.power_w, self.baseline.host_idle_power_w)
        self.assertEqual(prediction.ttft_p99_ms, 25.0)

    def test_invalid_batch_gpu_action_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside the node topology"):
            predict_node_response(
                self.baseline,
                self.curve,
                self.curve,
                NodeControlInput(1.0, 1.0, 1.0, 1.0, 3),
            )


if __name__ == "__main__":
    unittest.main()
