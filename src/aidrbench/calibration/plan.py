"""Deterministic P2 coarse-grid calibration planning."""

from __future__ import annotations

import csv
import hashlib
import itertools
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml

PLAN_COLUMNS = (
    "run_order",
    "run_id",
    "config_id",
    "repeat",
    "stage",
    "inference_cap_ratio",
    "active_batch_gpus",
    "batch_cap_ratio",
    "request_rate_level",
    "token_mix",
    "warmup_seconds",
    "measurement_seconds",
    "cooldown_seconds",
    "seed",
)


@dataclass(frozen=True, slots=True)
class CalibrationPlanSummary:
    """Machine-readable summary returned after writing a calibration plan."""

    output: str
    design: str
    unique_configurations: int
    runs: int
    repetitions: int
    estimated_runtime_hours: float
    seed: int
    config_sha256: str


@dataclass(frozen=True, slots=True)
class _PlanSettings:
    inference_cap_ratios: tuple[float, ...]
    batch_gpu_counts: tuple[int, ...]
    batch_cap_ratios: tuple[float, ...]
    request_rate_levels: tuple[str, ...]
    token_mixes: tuple[str, ...]
    repetitions: int
    warmup_seconds: int
    measurement_seconds: int
    cooldown_seconds: int
    seed: int
    randomize_order: bool


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _unique_sequence(value: object, name: str) -> Sequence[object]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    if len(value) != len({str(item) for item in value}):
        raise ValueError(f"{name} must not contain duplicates")
    return value


def _ratios(value: object, name: str) -> tuple[float, ...]:
    ratios: list[float] = []
    for raw_ratio in _unique_sequence(value, name):
        if isinstance(raw_ratio, bool) or not isinstance(raw_ratio, int | float):
            raise ValueError(f"{name} entries must be numbers")
        ratio = float(raw_ratio)
        if not 0.0 < ratio <= 1.0:
            raise ValueError(f"{name} entries must be in (0, 1]")
        ratios.append(ratio)
    return tuple(ratios)


def _non_negative_ints(value: object, name: str) -> tuple[int, ...]:
    result: list[int] = []
    for raw_count in _unique_sequence(value, name):
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
            raise ValueError(f"{name} entries must be non-negative integers")
        result.append(raw_count)
    return tuple(result)


def _labels(value: object, name: str) -> tuple[str, ...]:
    labels: list[str] = []
    for raw_label in _unique_sequence(value, name):
        if not isinstance(raw_label, str) or not raw_label.strip():
            raise ValueError(f"{name} entries must be non-empty strings")
        labels.append(raw_label.strip())
    return tuple(labels)


def _positive_int(value: object, name: str, *, allow_zero: bool = False) -> int:
    lower_bound = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < lower_bound:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a {qualifier} integer")
    return value


def _load_settings(document: object) -> _PlanSettings:
    root = _require_mapping(document, "hardware config")
    power = _require_mapping(root.get("power"), "power")
    calibration = _require_mapping(root.get("calibration"), "calibration")
    timing = _require_mapping(calibration.get("timing"), "calibration.timing")

    randomize_order = calibration.get("randomize_order", True)
    if not isinstance(randomize_order, bool):
        raise ValueError("calibration.randomize_order must be a boolean")

    return _PlanSettings(
        inference_cap_ratios=_ratios(power.get("infer_cap_ratios"), "power.infer_cap_ratios"),
        batch_gpu_counts=_non_negative_ints(
            calibration.get("batch_gpu_counts"), "calibration.batch_gpu_counts"
        ),
        batch_cap_ratios=_ratios(power.get("batch_cap_ratios"), "power.batch_cap_ratios"),
        request_rate_levels=_labels(
            calibration.get("request_rate_levels"), "calibration.request_rate_levels"
        ),
        token_mixes=_labels(calibration.get("token_mixes"), "calibration.token_mixes"),
        repetitions=_positive_int(calibration.get("repetitions"), "calibration.repetitions"),
        warmup_seconds=_positive_int(
            timing.get("warmup_seconds"), "calibration.timing.warmup_seconds", allow_zero=True
        ),
        measurement_seconds=_positive_int(
            timing.get("measurement_seconds"), "calibration.timing.measurement_seconds"
        ),
        cooldown_seconds=_positive_int(
            timing.get("cooldown_seconds"),
            "calibration.timing.cooldown_seconds",
            allow_zero=True,
        ),
        seed=_positive_int(calibration.get("seed"), "calibration.seed", allow_zero=True),
        randomize_order=randomize_order,
    )


def _design_name(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if not normalized or re.fullmatch(r"[a-z0-9_]+", normalized) is None:
        raise ValueError("design must contain only letters, digits, hyphens, or underscores")
    return normalized


def _configured_combinations(
    document: object,
    settings: _PlanSettings,
    design: str,
) -> tuple[_PlanSettings, list[tuple[float, int, float, str, str]]]:
    root = _require_mapping(document, "hardware config")
    calibration = _require_mapping(root.get("calibration"), "calibration")
    designs = _require_mapping(calibration.get("designs"), "calibration.designs")
    selected = _require_mapping(designs.get(design), f"calibration.designs.{design}")
    raw_configurations = selected.get("configurations")

    repetitions = _positive_int(
        selected.get("repetitions", settings.repetitions),
        f"calibration.designs.{design}.repetitions",
    )
    randomize_order = selected.get("randomize_order", settings.randomize_order)
    if not isinstance(randomize_order, bool):
        raise ValueError(f"calibration.designs.{design}.randomize_order must be a boolean")
    raw_timing = selected.get("timing")
    timing = (
        _require_mapping(raw_timing, f"calibration.designs.{design}.timing")
        if raw_timing is not None
        else {}
    )
    selected_settings = replace(
        settings,
        repetitions=repetitions,
        randomize_order=randomize_order,
        warmup_seconds=_positive_int(
            timing.get("warmup_seconds", settings.warmup_seconds),
            f"calibration.designs.{design}.timing.warmup_seconds",
            allow_zero=True,
        ),
        measurement_seconds=_positive_int(
            timing.get("measurement_seconds", settings.measurement_seconds),
            f"calibration.designs.{design}.timing.measurement_seconds",
        ),
        cooldown_seconds=_positive_int(
            timing.get("cooldown_seconds", settings.cooldown_seconds),
            f"calibration.designs.{design}.timing.cooldown_seconds",
            allow_zero=True,
        ),
    )

    if raw_configurations is None:
        selection = selected.get("selection")
        if selection != "maximin":
            raise ValueError(
                f"calibration.designs.{design} must define configurations or "
                "selection: maximin"
            )
        configuration_count = _positive_int(
            selected.get("configuration_count"),
            f"calibration.designs.{design}.configuration_count",
        )
        return selected_settings, _maximin_combinations(
            settings,
            configuration_count,
        )
    if not isinstance(raw_configurations, list) or not raw_configurations:
        raise ValueError(f"calibration.designs.{design}.configurations must be a non-empty list")

    combinations: list[tuple[float, int, float, str, str]] = []
    for index, raw_configuration in enumerate(raw_configurations, start=1):
        name = f"calibration.designs.{design}.configurations[{index - 1}]"
        configuration = _require_mapping(raw_configuration, name)
        infer_ratio = _ratios(
            [configuration.get("inference_cap_ratio")], f"{name}.inference_cap_ratio"
        )[0]
        batch_gpus = _non_negative_ints(
            [configuration.get("active_batch_gpus")], f"{name}.active_batch_gpus"
        )[0]
        batch_ratio = _ratios(
            [configuration.get("batch_cap_ratio")], f"{name}.batch_cap_ratio"
        )[0]
        request_rate = _labels(
            [configuration.get("request_rate_level")], f"{name}.request_rate_level"
        )[0]
        token_mix = _labels([configuration.get("token_mix")], f"{name}.token_mix")[0]
        combination = (infer_ratio, batch_gpus, batch_ratio, request_rate, token_mix)
        allowed = (
            infer_ratio in settings.inference_cap_ratios
            and batch_gpus in settings.batch_gpu_counts
            and batch_ratio in settings.batch_cap_ratios
            and request_rate in settings.request_rate_levels
            and token_mix in settings.token_mixes
        )
        if not allowed:
            raise ValueError(f"{name} contains a value outside the configured factor levels")
        if combination in combinations:
            raise ValueError(f"{name} duplicates an earlier configuration")
        combinations.append(combination)
    return selected_settings, combinations


def _maximin_combinations(
    settings: _PlanSettings,
    configuration_count: int,
) -> list[tuple[float, int, float, str, str]]:
    """Select deterministic space-filling points from the configured factor grid."""

    candidates = list(
        itertools.product(
            settings.inference_cap_ratios,
            settings.batch_gpu_counts,
            settings.batch_cap_ratios,
            settings.request_rate_levels,
            settings.token_mixes,
        )
    )
    if configuration_count > len(candidates):
        raise ValueError(
            f"configuration_count={configuration_count} exceeds the "
            f"{len(candidates)} available combinations"
        )

    dimensions: tuple[Sequence[object], ...] = (
        settings.inference_cap_ratios,
        settings.batch_gpu_counts,
        settings.batch_cap_ratios,
        settings.request_rate_levels,
        settings.token_mixes,
    )

    def coordinates(candidate: tuple[float, int, float, str, str]) -> tuple[float, ...]:
        normalized: list[float] = []
        for value, levels in zip(candidate, dimensions, strict=True):
            denominator = max(len(levels) - 1, 1)
            normalized.append(levels.index(value) / denominator)
        return tuple(normalized)

    coordinate_map = {candidate: coordinates(candidate) for candidate in candidates}

    def squared_distance(
        left: tuple[float, ...],
        right: tuple[float, ...],
    ) -> float:
        return sum(
            (left_value - right_value) ** 2
            for left_value, right_value in zip(left, right, strict=True)
        )

    # Start from the full-cap, fully active reference operating point nearest
    # the median request/token levels. Seeded tie ordering then makes the
    # farthest-point design reproducible without privileging canonical order.
    reference = (
        settings.inference_cap_ratios[-1],
        settings.batch_gpu_counts[-1],
        settings.batch_cap_ratios[-1],
        settings.request_rate_levels[(len(settings.request_rate_levels) - 1) // 2],
        settings.token_mixes[(len(settings.token_mixes) - 1) // 2],
    )
    shuffled = candidates.copy()
    random.Random(settings.seed).shuffle(shuffled)
    selected = [reference]
    remaining = [candidate for candidate in shuffled if candidate != reference]
    while len(selected) < configuration_count:
        next_candidate = max(
            remaining,
            key=lambda candidate: min(
                squared_distance(coordinate_map[candidate], coordinate_map[chosen])
                for chosen in selected
            ),
        )
        selected.append(next_candidate)
        remaining.remove(next_candidate)
    return selected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_calibration_plan(
    config: str | Path,
    output: str | Path,
    *,
    design: str = "full_factorial",
) -> CalibrationPlanSummary:
    """Write a deterministic full-factorial or explicitly configured run plan."""

    config_path = Path(config)
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    settings = _load_settings(document)
    selected_design = _design_name(design)

    if selected_design == "full_factorial":
        combinations = list(
            itertools.product(
                settings.inference_cap_ratios,
                settings.batch_gpu_counts,
                settings.batch_cap_ratios,
                settings.request_rate_levels,
                settings.token_mixes,
            )
        )
    else:
        settings, combinations = _configured_combinations(
            document, settings, selected_design
        )
    rows: list[dict[str, object]] = []
    id_prefix = "p2" if selected_design == "full_factorial" else f"p2_{selected_design}"
    for config_number, combination in enumerate(combinations, start=1):
        infer_ratio, batch_gpus, batch_ratio, request_rate, token_mix = combination
        config_id = f"cfg{config_number:04d}"
        for repeat in range(1, settings.repetitions + 1):
            rows.append(
                {
                    "run_order": 0,
                    "run_id": f"{id_prefix}_{config_id}_r{repeat:02d}",
                    "config_id": config_id,
                    "repeat": repeat,
                    "stage": selected_design,
                    "inference_cap_ratio": infer_ratio,
                    "active_batch_gpus": batch_gpus,
                    "batch_cap_ratio": batch_ratio,
                    "request_rate_level": request_rate,
                    "token_mix": token_mix,
                    "warmup_seconds": settings.warmup_seconds,
                    "measurement_seconds": settings.measurement_seconds,
                    "cooldown_seconds": settings.cooldown_seconds,
                    "seed": settings.seed,
                }
            )

    if settings.randomize_order:
        random.Random(settings.seed).shuffle(rows)
    for run_order, row in enumerate(rows, start=1):
        row["run_order"] = run_order

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PLAN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    seconds_per_run = (
        settings.warmup_seconds + settings.measurement_seconds + settings.cooldown_seconds
    )
    return CalibrationPlanSummary(
        output=str(output_path),
        design=selected_design,
        unique_configurations=len(combinations),
        runs=len(rows),
        repetitions=settings.repetitions,
        estimated_runtime_hours=round(len(rows) * seconds_per_run / 3600.0, 3),
        seed=settings.seed,
        config_sha256=_sha256(config_path),
    )


def summary_dict(summary: CalibrationPlanSummary) -> dict[str, object]:
    """Convert the immutable public result to a JSON-ready dictionary."""

    return asdict(summary)
