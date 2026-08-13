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
