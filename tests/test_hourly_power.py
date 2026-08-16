from __future__ import annotations

import pytest

from aidrbench.models.power import HourlyDataCenterPowerModel, VirtualDataCenter


def test_hourly_power_model_respects_capacity_and_pcc_power_identity() -> None:
    model = HourlyDataCenterPowerModel(
        data_center=VirtualDataCenter(
            gpus_per_node=4,
            node_count=2,
            flexible_gpu_fraction=0.5,
        ),
        idle_power_w_per_gpu=80.0,
        flexible_active_power_w_per_gpu=450.0,
        rigid_active_power_w_per_gpu=400.0,
        node_fixed_overhead_w=300.0,
        rigid_gpu_utilization=0.6,
        pue=1.2,
    )

    idle = model.predict(0.0)
    full = model.predict(model.flexible_capacity_gpu_h)

    assert 0.0 <= idle.active_flexible_gpus <= model.data_center.flexible_gpu_count
    assert full.active_flexible_gpus == pytest.approx(model.data_center.flexible_gpu_count)
    assert full.dc_power_kw > idle.dc_power_kw > 0.0
    assert full.flexible_energy_kwh == pytest.approx(full.flexible_it_power_kw)
    assert model.flexible_active_energy_per_gpu_h_kwh == pytest.approx(0.54)
    with pytest.raises(ValueError, match="exceeds flexible pool capacity"):
        model.predict(model.flexible_capacity_gpu_h + 0.1)


def test_hourly_power_model_uses_execution_class_power_and_class_compute_debt() -> None:
    model = HourlyDataCenterPowerModel(
        data_center=VirtualDataCenter(
            gpus_per_node=4,
            node_count=2,
            flexible_gpu_fraction=0.5,
        ),
        idle_power_w_per_gpu=80.0,
        flexible_active_power_w_per_gpu=400.0,
        rigid_active_power_w_per_gpu=400.0,
        node_fixed_overhead_w=300.0,
        rigid_gpu_utilization=0.6,
        pue=1.2,
        flexible_active_power_w_per_gpu_by_class=(
            ("offline_inference", 300.0),
            ("training", 500.0),
        ),
    )

    all_training = model.predict_by_class({"training": 2.0})
    all_offline = model.predict_by_class({"offline_inference": 2.0})
    balanced = model.predict_by_class({"training": 1.0, "offline_inference": 1.0})

    assert all_training.dc_power_kw > balanced.dc_power_kw > all_offline.dc_power_kw
    assert balanced.dc_power_kw == pytest.approx(model.predict(2.0).dc_power_kw)
    assert model.queued_work_energy_kwh({"training": 1.0, "offline_inference": 1.0}) == (
        pytest.approx(0.96)
    )
