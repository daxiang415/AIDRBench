"""Strict, hash-bound configuration for the economic-participation extension."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from aidrbench.data.splits import sha256_file


def _mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _exact_fields(document: Mapping[str, Any], expected: set[str], *, name: str) -> None:
    observed = set(document)
    if observed != expected:
        raise ValueError(
            f"{name} fields mismatch; missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _nonempty_string(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _integer_list(value: object, *, name: str, positive: bool = False) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        raise ValueError(f"{name} must contain integers")
    parsed = tuple(int(item) for item in value)
    if positive and any(item <= 0 for item in parsed):
        raise ValueError(f"{name} must contain positive integers")
    if tuple(sorted(set(parsed))) != parsed:
        raise ValueError(f"{name} must be unique and increasing")
    return parsed


def _float_list(
    value: object,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    parsed = tuple(float(item) for item in value)
    if any(not float("-inf") < item < float("inf") for item in parsed):
        raise ValueError(f"{name} must contain finite numbers")
    if minimum is not None and any(item < minimum for item in parsed):
        raise ValueError(f"{name} must not contain values below {minimum}")
    if maximum is not None and any(item > maximum for item in parsed):
        raise ValueError(f"{name} must not contain values above {maximum}")
    return parsed


def annual_event_count_screening_class(annual_event_count: int) -> tuple[str, bool]:
    """Classify predeclared fresh-event annualisation coordinates.

    The first three are plausible screening coordinates for independent
    fresh-state calls.  The latter two deliberately expose frequency
    multiplication stress; neither is a repeated-event technical certificate.
    """

    if annual_event_count in {1, 12, 50}:
        return "plausible_screening", False
    if annual_event_count in {100, 250}:
        return "exposure_multiplier_stress", True
    raise ValueError(
        "annual_event_counts may contain only the predeclared coordinates "
        "{1, 12, 50, 100, 250}"
    )


@dataclass(frozen=True, slots=True)
class TechnicalSpecification:
    scenario_directory: str
    expected_scenario_count: int
    expected_episode_seed_range: tuple[int, int]
    scenario_set_sha256: str
    controller: Literal["robust_mpc"]
    controller_config: str
    controller_config_sha256: str
    technical_certificate_path: str
    technical_certificate_sha256: str
    technical_certificate_manifest: str
    technical_certificate_manifest_sha256: str
    technical_selection_path: str
    technical_selection_sha256: str
    validation_scenario_receipt: str
    validation_scenario_receipt_sha256: str
    locked_id_receipt: str
    locked_id_receipt_sha256: str
    replay_runtime_mode: Literal["current_worktree", "certificate_git_commit"]
    replay_git_commit: str | None
    duration_hours: tuple[int, ...]
    notice_hours: tuple[int, ...]
    reliability_target: float
    confidence_level: float
    event_id: int
    offer_fractions: tuple[float, ...]
    workers: int
    criteria: dict[str, float]

    def __post_init__(self) -> None:
        if self.expected_scenario_count <= 1:
            raise ValueError("expected_scenario_count must exceed one")
        first, last = self.expected_episode_seed_range
        if first < 0 or last < first or last - first + 1 != self.expected_scenario_count:
            raise ValueError("expected_episode_seed_range must exactly match scenario count")
        if self.controller != "robust_mpc":
            raise ValueError("economic v1 only supports the fixed robust_mpc controller")
        if self.replay_runtime_mode == "certificate_git_commit":
            if self.replay_git_commit is None or len(self.replay_git_commit) != 40:
                raise ValueError(
                    "certificate_git_commit replay requires an explicit 40-character git commit"
                )
            try:
                int(self.replay_git_commit, 16)
            except ValueError as error:
                raise ValueError("replay_git_commit must be a hexadecimal git object ID") from error
        elif self.replay_runtime_mode == "current_worktree":
            if self.replay_git_commit is not None:
                raise ValueError("current_worktree replay must set replay_git_commit to null")
        else:
            raise ValueError("unsupported replay_runtime_mode")
        hashes = (
            self.scenario_set_sha256,
            self.controller_config_sha256,
            self.technical_certificate_sha256,
            self.technical_certificate_manifest_sha256,
            self.technical_selection_sha256,
            self.validation_scenario_receipt_sha256,
            self.locked_id_receipt_sha256,
        )
        if any(len(value) != 64 for value in hashes):
            raise ValueError("technical input hashes must be SHA-256 digests")
        if not 0.0 < self.reliability_target < 1.0:
            raise ValueError("reliability_target must lie in (0, 1)")
        if not 0.0 < self.confidence_level < 1.0:
            raise ValueError("confidence_level must lie in (0, 1)")
        if self.event_id < 0:
            raise ValueError("event_id must be non-negative")
        if self.workers <= 0:
            raise ValueError("workers must be positive")
        if any(not 0.0 < fraction <= 1.0 for fraction in self.offer_fractions):
            raise ValueError("offer_fractions must lie in (0, 1]")
        if tuple(sorted(set(self.offer_fractions))) != self.offer_fractions:
            raise ValueError("offer_fractions must be unique and increasing")
        if 1.0 not in self.offer_fractions:
            raise ValueError(
                "offer_fractions must include 1.0, the independently certified ceiling; "
                "lower fractions are development diagnostics only"
            )

    def qualification_for_offer_fraction(self, fraction: float) -> str:
        """Return the evidence class without promoting diagnostic fractions."""

        if abs(float(fraction) - 1.0) <= 1e-12:
            return "independently_certified_ceiling"
        return "development_screened_not_independently_certified"


@dataclass(frozen=True, slots=True)
class LedgerSpecification:
    baseline_type: Literal["paired_no_control_replay"]
    paired_pcc_tolerance_kw: float
    work_conservation_tolerance_gpu_h: float
    include_interval_ledger: bool

    def __post_init__(self) -> None:
        if self.baseline_type != "paired_no_control_replay":
            raise ValueError("economic v1 requires a paired no-control replay")
        if self.paired_pcc_tolerance_kw <= 0.0:
            raise ValueError("paired_pcc_tolerance_kw must be positive")
        if self.work_conservation_tolerance_gpu_h <= 0.0:
            raise ValueError("work_conservation_tolerance_gpu_h must be positive")


@dataclass(frozen=True, slots=True)
class EvaluationSpecification:
    dispatch_sampling: Literal["independent_fresh_event_screening_bootstrap"]
    bootstrap_draws: int
    bootstrap_seed: int
    risk_quantile: float
    annual_event_counts: tuple[int, ...]
    primary_duration_h: int
    primary_notice_h: int
    primary_reliability_target: float
    primary_offer_fraction: float
    primary_capital_case_id: str
    primary_operating_case_id: str
    primary_market_archetype_id: str
    primary_annual_event_count: int
    primary_facility_site_scale_mw: float
    primary_capacity_payment_per_kw_year: float
    primary_performance_payment_per_mwh: float
    primary_regime_exposures: tuple[tuple[str, float, float], ...]

    def __post_init__(self) -> None:
        if self.dispatch_sampling != "independent_fresh_event_screening_bootstrap":
            raise ValueError(
                "economic v1 requires independent_fresh_event_screening_bootstrap; "
                "it is not a continuous annual DR programme"
            )
        if self.bootstrap_draws < 100:
            raise ValueError("bootstrap_draws must be at least 100")
        if self.bootstrap_seed < 0:
            raise ValueError("bootstrap_seed must be non-negative")
        if not 0.0 < self.risk_quantile < 0.5:
            raise ValueError("risk_quantile must lie in (0, 0.5)")
        if self.primary_offer_fraction != 1.0:
            raise ValueError(
                "primary_offer_fraction must equal 1.0 so the main result is the "
                "independently certified Kcert, or zero"
            )
        for annual_event_count in self.annual_event_counts:
            annual_event_count_screening_class(annual_event_count)
        if self.primary_facility_site_scale_mw <= 0.0:
            raise ValueError("primary_facility_site_scale_mw must be positive")
        if self.primary_capacity_payment_per_kw_year != 0.0:
            raise ValueError(
                "primary_capacity_payment_per_kw_year must be the zero-payment reference; "
                "the main boundary reports break-even payment instead of a selected price"
            )
        expected_regimes = {"slack_backed", "reserved_headroom", "throughput_displacing"}
        observed_regimes = {regime for regime, _reserve, _alpha in self.primary_regime_exposures}
        if observed_regimes != expected_regimes or len(self.primary_regime_exposures) != 3:
            raise ValueError("primary_regime_exposures must declare each v1 regime exactly once")
        for regime, reserve, alpha in self.primary_regime_exposures:
            if not 0.0 <= reserve <= 1.0 or not 0.0 <= alpha <= 1.0:
                raise ValueError("primary regime exposures must lie in [0, 1]")
            if regime == "slack_backed" and (reserve != 0.0 or alpha != 0.0):
                raise ValueError("slack-backed primary exposure must be zero")
            if regime == "reserved_headroom" and (reserve <= 0.0 or alpha != 0.0):
                raise ValueError("reserved-headroom primary exposure is invalid")
            if regime == "throughput_displacing" and (reserve != 0.0 or alpha <= 0.0):
                raise ValueError("throughput-displacing primary exposure is invalid")

    def exposure_for(self, regime: str) -> tuple[float, float]:
        matches = [
            (reserve, alpha)
            for declared_regime, reserve, alpha in self.primary_regime_exposures
            if declared_regime == regime
        ]
        if len(matches) != 1:
            raise ValueError(f"primary exposure is absent for {regime}")
        return matches[0]


@dataclass(frozen=True, slots=True)
class ExternalInputSpecification:
    cost_parameter_grid: str
    cost_parameter_grid_sha256: str
    market_archetypes: str
    market_archetypes_sha256: str
    source_register: str
    source_register_sha256: str
    external_parameter_evidence: str
    external_parameter_evidence_sha256: str

    def __post_init__(self) -> None:
        for value in (
            self.cost_parameter_grid_sha256,
            self.market_archetypes_sha256,
            self.source_register_sha256,
            self.external_parameter_evidence_sha256,
        ):
            if len(value) != 64:
                raise ValueError("external input hashes must be SHA-256 digests")


@dataclass(frozen=True, slots=True)
class EconomicParticipationSpecification:
    schema_version: int
    analysis_id: str
    analysis_role: Literal["development_parameterized_screening"]
    monetary_basis: Literal["real_2026_usd"]
    technical: TechnicalSpecification
    ledger: LedgerSpecification
    evaluation: EvaluationSpecification
    inputs: ExternalInputSpecification

    def __post_init__(self) -> None:
        if self.schema_version != 2:
            raise ValueError("unsupported economic-participation schema_version")
        if self.analysis_role != "development_parameterized_screening":
            raise ValueError("v1 is only a development parameterized screening")
        if self.monetary_basis != "real_2026_usd":
            raise ValueError("v1 requires real_2026_usd monetary basis")
        if any("locked" in part.lower() for part in Path(self.technical.scenario_directory).parts):
            raise ValueError("economic screening may not replay a locked scenario directory")
        if self.evaluation.primary_duration_h not in self.technical.duration_hours:
            raise ValueError("primary_duration_h must be in technical.duration_hours")
        if self.evaluation.primary_notice_h not in self.technical.notice_hours:
            raise ValueError("primary_notice_h must be in technical.notice_hours")
        if self.evaluation.primary_offer_fraction not in self.technical.offer_fractions:
            raise ValueError("primary_offer_fraction must be in technical.offer_fractions")
        if self.evaluation.primary_annual_event_count not in self.evaluation.annual_event_counts:
            raise ValueError("primary annual event count must be in annual_event_counts")
        if (
            abs(self.evaluation.primary_reliability_target - self.technical.reliability_target)
            > 1e-12
        ):
            raise ValueError("primary reliability target must match the technical target")

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        technical = result["technical"]
        assert isinstance(technical, dict)
        technical["expected_episode_seed_range"] = list(self.technical.expected_episode_seed_range)
        technical["duration_hours"] = list(self.technical.duration_hours)
        technical["notice_hours"] = list(self.technical.notice_hours)
        technical["offer_fractions"] = list(self.technical.offer_fractions)
        evaluation = result["evaluation"]
        assert isinstance(evaluation, dict)
        evaluation["annual_event_counts"] = list(self.evaluation.annual_event_counts)
        evaluation["primary_regime_exposures"] = {
            regime: {
                "reserved_capacity_fraction": reserve,
                "opportunity_exposure_alpha": alpha,
            }
            for regime, reserve, alpha in self.evaluation.primary_regime_exposures
        }
        return result

    @property
    def sha256(self) -> str:
        return _sha256(self.as_dict())

    def physical_ledger_contract(self) -> dict[str, object]:
        """Return the identity that determines a paired physical replay.

        Economics-only coordinates (cost, market, source register and
        bootstrap/economic evaluation settings) are intentionally absent.  A
        changed physical controller, certificate, scenario set, criteria or
        ledger definition must still produce a different contract hash.
        """

        technical = asdict(self.technical)
        technical["expected_episode_seed_range"] = list(
            self.technical.expected_episode_seed_range
        )
        technical["duration_hours"] = list(self.technical.duration_hours)
        technical["notice_hours"] = list(self.technical.notice_hours)
        technical["offer_fractions"] = list(self.technical.offer_fractions)
        return {
            "contract_schema_version": 1,
            "analysis_id": self.analysis_id,
            "analysis_role": self.analysis_role,
            "technical": technical,
            "ledger": asdict(self.ledger),
        }

    @property
    def physical_ledger_contract_sha256(self) -> str:
        return _sha256(self.physical_ledger_contract())


@dataclass(frozen=True, slots=True)
class CapitalCase:
    case_id: str
    sensitivity_axis: Literal[
        "reference",
        "economic_life",
        "discount_rate",
        "salvage_fraction",
    ]
    economic_life_years: float
    discount_rate: float
    salvage_fraction: float
    installed_cost_per_reserved_kw: float
    annual_om_fraction: float
    fixed_site_enablement_annual_cost: float
    variable_enablement_cost_per_offer_kw: float
    checkpoint_cost_per_event: float


@dataclass(frozen=True, slots=True)
class OperatingCase:
    case_id: str
    value_per_gpu_h: float
    delay_cost_per_gpu_h_h: float
    missed_work_cost_per_gpu_h: float
    terminal_backlog_cost_per_gpu_h: float
    electricity_price_per_kwh: float


@dataclass(frozen=True, slots=True)
class RegimeCase:
    regime: Literal["slack_backed", "reserved_headroom", "throughput_displacing"]
    reserved_capacity_fractions: tuple[float, ...]
    opportunity_exposure_alphas: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class CostParameterGrid:
    schema_version: int
    currency_basis: Literal["real_2026_usd"]
    analysis_status: Literal["illustrative_parameterized_sensitivity"]
    reserved_capacity_basis: Literal["abstract_pcc_side_kw_sensitivity"]
    reference_module_operating_peak_kw: float
    facility_site_scales_mw: tuple[float, ...]
    facility_scale_interpretation: Literal[
        "proportional_reference_module_accounting_sensitivity_no_portfolio_diversification"
    ]
    capital_cases: tuple[CapitalCase, ...]
    operating_cases: tuple[OperatingCase, ...]
    regimes: tuple[RegimeCase, ...]


@dataclass(frozen=True, slots=True)
class MarketArchetype:
    archetype_id: str
    capacity_payment_per_kw_year: tuple[float, ...]
    performance_payment_per_mwh: tuple[float, ...]
    flexible_connection_value_per_year: tuple[float, ...]
    shortfall_penalty_per_mwh: float
    failure_penalty_per_event: float


@dataclass(frozen=True, slots=True)
class MarketArchetypes:
    schema_version: int
    currency_basis: Literal["real_2026_usd"]
    analysis_status: Literal["illustrative_parameterized_sensitivity"]
    archetypes: tuple[MarketArchetype, ...]


def scenario_set_sha256(records: Iterable[Mapping[Any, Any]]) -> str:
    """Hash the exact frozen scenario identity set in canonical seed order."""

    normalized: list[dict[str, object]] = []
    for raw_record in records:
        record = _mapping(raw_record, name="economic scenario record")
        _exact_fields(
            record,
            {"episode_seed", "scenario_id", "scenario_hash"},
            name="economic scenario record",
        )
        seed = int(record["episode_seed"])
        scenario_id = _nonempty_string(record["scenario_id"], name="scenario_id")
        scenario_hash = _nonempty_string(record["scenario_hash"], name="scenario_hash")
        if seed < 0 or len(scenario_hash) != 64:
            raise ValueError("economic scenario record has an invalid seed or SHA-256 hash")
        normalized.append(
            {
                "episode_seed": seed,
                "scenario_id": scenario_id,
                "scenario_hash": scenario_hash,
            }
        )
    normalized.sort(key=lambda item: int(str(item["episode_seed"])))
    if len({int(str(item["episode_seed"])) for item in normalized}) != len(normalized):
        raise ValueError("economic scenario records have duplicate episode seeds")
    if len({str(item["scenario_hash"]) for item in normalized}) != len(normalized):
        raise ValueError("economic scenario records have duplicate scenario hashes")
    return _sha256(normalized)


def _criteria(document: Mapping[str, Any]) -> dict[str, float]:
    _exact_fields(
        document,
        {
            "min_delivery_ratio",
            "min_interval_delivery_ratio",
            "max_deadline_miss_rate",
            "max_rebound_ratio",
            "min_window_peak_relief_fraction",
            "max_terminal_backlog_fraction",
        },
        name="technical.criteria",
    )
    parsed = {key: float(value) for key, value in document.items()}
    if any(not 0.0 <= value <= 1.0 for value in parsed.values()):
        raise ValueError("technical criteria must lie in [0, 1]")
    return parsed


def load_economic_participation_specification(
    path: str | Path,
) -> EconomicParticipationSpecification:
    """Load the complete v1 protocol with no implicit economics defaults."""

    document = _mapping(yaml.safe_load(Path(path).read_text(encoding="utf-8")), name="economics")
    _exact_fields(
        document,
        {
            "schema_version",
            "analysis_id",
            "analysis_role",
            "monetary_basis",
            "technical",
            "ledger",
            "evaluation",
            "inputs",
        },
        name="economics",
    )
    technical = _mapping(document["technical"], name="technical")
    _exact_fields(
        technical,
        {
            "scenario_directory",
            "expected_scenario_count",
            "expected_episode_seed_range",
            "scenario_set_sha256",
            "controller",
            "controller_config",
            "controller_config_sha256",
            "technical_certificate_path",
            "technical_certificate_sha256",
            "technical_certificate_manifest",
            "technical_certificate_manifest_sha256",
            "technical_selection_path",
            "technical_selection_sha256",
            "validation_scenario_receipt",
            "validation_scenario_receipt_sha256",
            "locked_id_receipt",
            "locked_id_receipt_sha256",
            "replay_runtime_mode",
            "replay_git_commit",
            "duration_hours",
            "notice_hours",
            "reliability_target",
            "confidence_level",
            "event_id",
            "offer_fractions",
            "workers",
            "criteria",
        },
        name="technical",
    )
    seeds = _integer_list(
        technical["expected_episode_seed_range"], name="expected_episode_seed_range"
    )
    if len(seeds) != 2:
        raise ValueError("expected_episode_seed_range must contain exactly two integers")
    ledger = _mapping(document["ledger"], name="ledger")
    _exact_fields(
        ledger,
        {
            "baseline_type",
            "paired_pcc_tolerance_kw",
            "work_conservation_tolerance_gpu_h",
            "include_interval_ledger",
        },
        name="ledger",
    )
    evaluation = _mapping(document["evaluation"], name="evaluation")
    _exact_fields(
        evaluation,
        {
            "dispatch_sampling",
            "bootstrap_draws",
            "bootstrap_seed",
            "risk_quantile",
            "annual_event_counts",
            "primary_duration_h",
            "primary_notice_h",
            "primary_reliability_target",
            "primary_offer_fraction",
            "primary_capital_case_id",
            "primary_operating_case_id",
            "primary_market_archetype_id",
            "primary_annual_event_count",
            "primary_facility_site_scale_mw",
            "primary_capacity_payment_per_kw_year",
            "primary_performance_payment_per_mwh",
            "primary_regime_exposures",
        },
        name="evaluation",
    )
    inputs = _mapping(document["inputs"], name="inputs")
    _exact_fields(
        inputs,
        {
            "cost_parameter_grid",
            "cost_parameter_grid_sha256",
            "market_archetypes",
            "market_archetypes_sha256",
            "source_register",
            "source_register_sha256",
            "external_parameter_evidence",
            "external_parameter_evidence_sha256",
        },
        name="inputs",
    )
    primary_exposures_document = _mapping(
        evaluation["primary_regime_exposures"], name="primary_regime_exposures"
    )
    primary_exposures: list[tuple[str, float, float]] = []
    for regime in ("slack_backed", "reserved_headroom", "throughput_displacing"):
        item = _mapping(
            primary_exposures_document.get(regime), name=f"primary_regime_exposures.{regime}"
        )
        _exact_fields(
            item,
            {"reserved_capacity_fraction", "opportunity_exposure_alpha"},
            name=f"primary_regime_exposures.{regime}",
        )
        primary_exposures.append(
            (
                regime,
                float(item["reserved_capacity_fraction"]),
                float(item["opportunity_exposure_alpha"]),
            )
        )
    if set(primary_exposures_document) != {
        "slack_backed",
        "reserved_headroom",
        "throughput_displacing",
    }:
        raise ValueError("primary_regime_exposures has unknown or missing regime keys")
    return EconomicParticipationSpecification(
        schema_version=int(document["schema_version"]),
        analysis_id=_nonempty_string(document["analysis_id"], name="analysis_id"),
        analysis_role=str(document["analysis_role"]),  # type: ignore[arg-type]
        monetary_basis=str(document["monetary_basis"]),  # type: ignore[arg-type]
        technical=TechnicalSpecification(
            scenario_directory=_nonempty_string(
                technical["scenario_directory"], name="scenario_directory"
            ),
            expected_scenario_count=int(technical["expected_scenario_count"]),
            expected_episode_seed_range=(seeds[0], seeds[1]),
            scenario_set_sha256=_nonempty_string(
                technical["scenario_set_sha256"], name="scenario_set_sha256"
            ),
            controller=str(technical["controller"]),  # type: ignore[arg-type]
            controller_config=_nonempty_string(
                technical["controller_config"], name="controller_config"
            ),
            controller_config_sha256=_nonempty_string(
                technical["controller_config_sha256"], name="controller_config_sha256"
            ),
            technical_certificate_path=_nonempty_string(
                technical["technical_certificate_path"], name="technical_certificate_path"
            ),
            technical_certificate_sha256=_nonempty_string(
                technical["technical_certificate_sha256"], name="technical_certificate_sha256"
            ),
            technical_certificate_manifest=_nonempty_string(
                technical["technical_certificate_manifest"],
                name="technical_certificate_manifest",
            ),
            technical_certificate_manifest_sha256=_nonempty_string(
                technical["technical_certificate_manifest_sha256"],
                name="technical_certificate_manifest_sha256",
            ),
            technical_selection_path=_nonempty_string(
                technical["technical_selection_path"], name="technical_selection_path"
            ),
            technical_selection_sha256=_nonempty_string(
                technical["technical_selection_sha256"], name="technical_selection_sha256"
            ),
            validation_scenario_receipt=_nonempty_string(
                technical["validation_scenario_receipt"], name="validation_scenario_receipt"
            ),
            validation_scenario_receipt_sha256=_nonempty_string(
                technical["validation_scenario_receipt_sha256"],
                name="validation_scenario_receipt_sha256",
            ),
            locked_id_receipt=_nonempty_string(
                technical["locked_id_receipt"], name="locked_id_receipt"
            ),
            locked_id_receipt_sha256=_nonempty_string(
                technical["locked_id_receipt_sha256"], name="locked_id_receipt_sha256"
            ),
            replay_runtime_mode=str(technical["replay_runtime_mode"]),  # type: ignore[arg-type]
            replay_git_commit=(
                None
                if technical["replay_git_commit"] is None
                else _nonempty_string(technical["replay_git_commit"], name="replay_git_commit")
            ),
            duration_hours=_integer_list(
                technical["duration_hours"], name="duration_hours", positive=True
            ),
            notice_hours=_integer_list(technical["notice_hours"], name="notice_hours"),
            reliability_target=float(technical["reliability_target"]),
            confidence_level=float(technical["confidence_level"]),
            event_id=int(technical["event_id"]),
            offer_fractions=_float_list(
                technical["offer_fractions"], name="offer_fractions", minimum=0.0, maximum=1.0
            ),
            workers=int(technical["workers"]),
            criteria=_criteria(_mapping(technical["criteria"], name="technical.criteria")),
        ),
        ledger=LedgerSpecification(
            baseline_type=str(ledger["baseline_type"]),  # type: ignore[arg-type]
            paired_pcc_tolerance_kw=float(ledger["paired_pcc_tolerance_kw"]),
            work_conservation_tolerance_gpu_h=float(ledger["work_conservation_tolerance_gpu_h"]),
            include_interval_ledger=bool(ledger["include_interval_ledger"]),
        ),
        evaluation=EvaluationSpecification(
            dispatch_sampling=str(evaluation["dispatch_sampling"]),  # type: ignore[arg-type]
            bootstrap_draws=int(evaluation["bootstrap_draws"]),
            bootstrap_seed=int(evaluation["bootstrap_seed"]),
            risk_quantile=float(evaluation["risk_quantile"]),
            annual_event_counts=_integer_list(
                evaluation["annual_event_counts"], name="annual_event_counts", positive=True
            ),
            primary_duration_h=int(evaluation["primary_duration_h"]),
            primary_notice_h=int(evaluation["primary_notice_h"]),
            primary_reliability_target=float(evaluation["primary_reliability_target"]),
            primary_offer_fraction=float(evaluation["primary_offer_fraction"]),
            primary_capital_case_id=_nonempty_string(
                evaluation["primary_capital_case_id"], name="primary_capital_case_id"
            ),
            primary_operating_case_id=_nonempty_string(
                evaluation["primary_operating_case_id"], name="primary_operating_case_id"
            ),
            primary_market_archetype_id=_nonempty_string(
                evaluation["primary_market_archetype_id"], name="primary_market_archetype_id"
            ),
            primary_annual_event_count=int(evaluation["primary_annual_event_count"]),
            primary_facility_site_scale_mw=float(
                evaluation["primary_facility_site_scale_mw"]
            ),
            primary_capacity_payment_per_kw_year=float(
                evaluation["primary_capacity_payment_per_kw_year"]
            ),
            primary_performance_payment_per_mwh=float(
                evaluation["primary_performance_payment_per_mwh"]
            ),
            primary_regime_exposures=tuple(primary_exposures),
        ),
        inputs=ExternalInputSpecification(
            cost_parameter_grid=_nonempty_string(
                inputs["cost_parameter_grid"], name="cost_parameter_grid"
            ),
            cost_parameter_grid_sha256=_nonempty_string(
                inputs["cost_parameter_grid_sha256"], name="cost_parameter_grid_sha256"
            ),
            market_archetypes=_nonempty_string(
                inputs["market_archetypes"], name="market_archetypes"
            ),
            market_archetypes_sha256=_nonempty_string(
                inputs["market_archetypes_sha256"], name="market_archetypes_sha256"
            ),
            source_register=_nonempty_string(inputs["source_register"], name="source_register"),
            source_register_sha256=_nonempty_string(
                inputs["source_register_sha256"], name="source_register_sha256"
            ),
            external_parameter_evidence=_nonempty_string(
                inputs["external_parameter_evidence"], name="external_parameter_evidence"
            ),
            external_parameter_evidence_sha256=_nonempty_string(
                inputs["external_parameter_evidence_sha256"],
                name="external_parameter_evidence_sha256",
            ),
        ),
    )


def _nonnegative_float(document: Mapping[str, Any], key: str, *, name: str) -> float:
    value = float(document[key])
    if not 0.0 <= value < float("inf"):
        raise ValueError(f"{name}.{key} must be finite and non-negative")
    return value


def load_cost_parameter_grid(path: str | Path) -> CostParameterGrid:
    document = _mapping(yaml.safe_load(Path(path).read_text(encoding="utf-8")), name="cost grid")
    _exact_fields(
        document,
        {
            "schema_version",
            "currency_basis",
            "analysis_status",
            "reserved_capacity_basis",
            "reference_module_operating_peak_kw",
            "facility_site_scales_mw",
            "facility_scale_interpretation",
            "capital_cases",
            "operating_cases",
            "regimes",
        },
        name="cost grid",
    )
    if int(document["schema_version"]) != 2:
        raise ValueError("unsupported cost-parameter-grid schema version")
    capital_raw = document["capital_cases"]
    operating_raw = document["operating_cases"]
    regimes_raw = document["regimes"]
    if not isinstance(capital_raw, list) or not capital_raw:
        raise ValueError("capital_cases must be a non-empty list")
    if not isinstance(operating_raw, list) or not operating_raw:
        raise ValueError("operating_cases must be a non-empty list")
    if not isinstance(regimes_raw, list) or not regimes_raw:
        raise ValueError("regimes must be a non-empty list")
    capital_cases: list[CapitalCase] = []
    for index, raw in enumerate(capital_raw):
        item = _mapping(raw, name=f"capital_cases[{index}]")
        _exact_fields(
            item,
            {
                "case_id",
                "sensitivity_axis",
                "economic_life_years",
                "discount_rate",
                "salvage_fraction",
                "installed_cost_per_reserved_kw",
                "annual_om_fraction",
                "fixed_site_enablement_annual_cost",
                "variable_enablement_cost_per_offer_kw",
                "checkpoint_cost_per_event",
            },
            name=f"capital_cases[{index}]",
        )
        case = CapitalCase(
            case_id=_nonempty_string(item["case_id"], name=f"capital_cases[{index}].case_id"),
            sensitivity_axis=str(item["sensitivity_axis"]),  # type: ignore[arg-type]
            economic_life_years=_nonnegative_float(
                item, "economic_life_years", name=f"capital_cases[{index}]"
            ),
            discount_rate=_nonnegative_float(item, "discount_rate", name=f"capital_cases[{index}]"),
            salvage_fraction=_nonnegative_float(
                item, "salvage_fraction", name=f"capital_cases[{index}]"
            ),
            installed_cost_per_reserved_kw=_nonnegative_float(
                item, "installed_cost_per_reserved_kw", name=f"capital_cases[{index}]"
            ),
            annual_om_fraction=_nonnegative_float(
                item, "annual_om_fraction", name=f"capital_cases[{index}]"
            ),
            fixed_site_enablement_annual_cost=_nonnegative_float(
                item, "fixed_site_enablement_annual_cost", name=f"capital_cases[{index}]"
            ),
            variable_enablement_cost_per_offer_kw=_nonnegative_float(
                item,
                "variable_enablement_cost_per_offer_kw",
                name=f"capital_cases[{index}]",
            ),
            checkpoint_cost_per_event=_nonnegative_float(
                item, "checkpoint_cost_per_event", name=f"capital_cases[{index}]"
            ),
        )
        if case.economic_life_years <= 0.0 or case.salvage_fraction > 1.0:
            raise ValueError("capital case has an invalid life or salvage fraction")
        if case.sensitivity_axis not in {
            "reference",
            "economic_life",
            "discount_rate",
            "salvage_fraction",
        }:
            raise ValueError("capital case has an invalid sensitivity_axis")
        if case.sensitivity_axis == "reference" and not (
            case.economic_life_years == 4.0
            and case.discount_rate == 0.08
            and case.salvage_fraction == 0.10
        ):
            raise ValueError("reference capital case must be 4 years, 8% WACC and 10% salvage")
        if case.sensitivity_axis == "economic_life" and not (
            case.discount_rate == 0.08 and case.salvage_fraction == 0.10
        ):
            raise ValueError("economic-life sensitivity must hold WACC at 8% and salvage at 10%")
        if case.sensitivity_axis == "discount_rate" and not (
            case.economic_life_years == 4.0 and case.salvage_fraction == 0.10
        ):
            raise ValueError(
                "WACC sensitivity must hold economic life at 4 years and salvage at 10%"
            )
        if case.sensitivity_axis == "salvage_fraction" and not (
            case.economic_life_years == 4.0 and case.discount_rate == 0.08
        ):
            raise ValueError(
                "salvage sensitivity must hold economic life at 4 years and WACC at 8%"
            )
        capital_cases.append(case)
    operating_cases: list[OperatingCase] = []
    for index, raw in enumerate(operating_raw):
        item = _mapping(raw, name=f"operating_cases[{index}]")
        _exact_fields(
            item,
            {
                "case_id",
                "value_per_gpu_h",
                "delay_cost_per_gpu_h_h",
                "missed_work_cost_per_gpu_h",
                "terminal_backlog_cost_per_gpu_h",
                "electricity_price_per_kwh",
            },
            name=f"operating_cases[{index}]",
        )
        operating_cases.append(
            OperatingCase(
                case_id=_nonempty_string(item["case_id"], name=f"operating_cases[{index}].case_id"),
                value_per_gpu_h=_nonnegative_float(
                    item, "value_per_gpu_h", name=f"operating_cases[{index}]"
                ),
                delay_cost_per_gpu_h_h=_nonnegative_float(
                    item, "delay_cost_per_gpu_h_h", name=f"operating_cases[{index}]"
                ),
                missed_work_cost_per_gpu_h=_nonnegative_float(
                    item, "missed_work_cost_per_gpu_h", name=f"operating_cases[{index}]"
                ),
                terminal_backlog_cost_per_gpu_h=_nonnegative_float(
                    item, "terminal_backlog_cost_per_gpu_h", name=f"operating_cases[{index}]"
                ),
                electricity_price_per_kwh=_nonnegative_float(
                    item, "electricity_price_per_kwh", name=f"operating_cases[{index}]"
                ),
            )
        )
    regimes: list[RegimeCase] = []
    for index, raw in enumerate(regimes_raw):
        item = _mapping(raw, name=f"regimes[{index}]")
        _exact_fields(
            item,
            {"regime", "reserved_capacity_fractions", "opportunity_exposure_alphas"},
            name=f"regimes[{index}]",
        )
        regime = RegimeCase(
            regime=str(item["regime"]),  # type: ignore[arg-type]
            reserved_capacity_fractions=_float_list(
                item["reserved_capacity_fractions"],
                name=f"regimes[{index}].reserved_capacity_fractions",
                minimum=0.0,
                maximum=1.0,
            ),
            opportunity_exposure_alphas=_float_list(
                item["opportunity_exposure_alphas"],
                name=f"regimes[{index}].opportunity_exposure_alphas",
                minimum=0.0,
                maximum=1.0,
            ),
        )
        if regime.regime == "slack_backed":
            valid = regime.reserved_capacity_fractions == (
                0.0,
            ) and regime.opportunity_exposure_alphas == (0.0,)
        elif regime.regime == "reserved_headroom":
            valid = regime.opportunity_exposure_alphas == (0.0,) and any(
                value > 0.0 for value in regime.reserved_capacity_fractions
            )
        elif regime.regime == "throughput_displacing":
            valid = regime.reserved_capacity_fractions == (0.0,) and any(
                value > 0.0 for value in regime.opportunity_exposure_alphas
            )
        else:
            valid = False
        if not valid:
            raise ValueError(f"regimes[{index}] violates the v1 no-double-counting rule")
        regimes.append(regime)
    if len({case.case_id for case in capital_cases}) != len(capital_cases):
        raise ValueError("capital case IDs must be unique")
    if len({case.case_id for case in operating_cases}) != len(operating_cases):
        raise ValueError("operating case IDs must be unique")
    if len({case.regime for case in regimes}) != len(regimes):
        raise ValueError("regimes must be unique")
    if document["reserved_capacity_basis"] != "abstract_pcc_side_kw_sensitivity":
        raise ValueError("economic v1 reserve coordinate must be abstract_pcc_side_kw_sensitivity")
    reference_module_operating_peak_kw = float(document["reference_module_operating_peak_kw"])
    if not 0.0 < reference_module_operating_peak_kw < float("inf"):
        raise ValueError("reference_module_operating_peak_kw must be finite and positive")
    facility_site_scales_mw = _float_list(
        document["facility_site_scales_mw"],
        name="facility_site_scales_mw",
        minimum=0.0,
    )
    if any(value <= 0.0 for value in facility_site_scales_mw):
        raise ValueError("facility_site_scales_mw must be strictly positive")
    if tuple(sorted(set(facility_site_scales_mw))) != facility_site_scales_mw:
        raise ValueError("facility_site_scales_mw must be unique and increasing")
    facility_scale_interpretation = str(document["facility_scale_interpretation"])
    if (
        facility_scale_interpretation
        != "proportional_reference_module_accounting_sensitivity_no_portfolio_diversification"
    ):
        raise ValueError("facility scale interpretation must state the no-diversification bound")
    return CostParameterGrid(
        schema_version=int(document["schema_version"]),
        currency_basis=str(document["currency_basis"]),  # type: ignore[arg-type]
        analysis_status=str(document["analysis_status"]),  # type: ignore[arg-type]
        reserved_capacity_basis=str(document["reserved_capacity_basis"]),  # type: ignore[arg-type]
        reference_module_operating_peak_kw=reference_module_operating_peak_kw,
        facility_site_scales_mw=facility_site_scales_mw,
        facility_scale_interpretation=facility_scale_interpretation,  # type: ignore[arg-type]
        capital_cases=tuple(capital_cases),
        operating_cases=tuple(operating_cases),
        regimes=tuple(regimes),
    )


def load_market_archetypes(path: str | Path) -> MarketArchetypes:
    document = _mapping(
        yaml.safe_load(Path(path).read_text(encoding="utf-8")), name="market archetypes"
    )
    _exact_fields(
        document,
        {"schema_version", "currency_basis", "analysis_status", "archetypes"},
        name="market archetypes",
    )
    raw_archetypes = document["archetypes"]
    if not isinstance(raw_archetypes, list) or not raw_archetypes:
        raise ValueError("archetypes must be a non-empty list")
    archetypes: list[MarketArchetype] = []
    for index, raw in enumerate(raw_archetypes):
        item = _mapping(raw, name=f"archetypes[{index}]")
        _exact_fields(
            item,
            {
                "archetype_id",
                "capacity_payment_per_kw_year",
                "performance_payment_per_mwh",
                "flexible_connection_value_per_year",
                "shortfall_penalty_per_mwh",
                "failure_penalty_per_event",
            },
            name=f"archetypes[{index}]",
        )
        archetypes.append(
            MarketArchetype(
                archetype_id=_nonempty_string(
                    item["archetype_id"], name=f"archetypes[{index}].archetype_id"
                ),
                capacity_payment_per_kw_year=_float_list(
                    item["capacity_payment_per_kw_year"],
                    name=f"archetypes[{index}].capacity_payment_per_kw_year",
                    minimum=0.0,
                ),
                performance_payment_per_mwh=_float_list(
                    item["performance_payment_per_mwh"],
                    name=f"archetypes[{index}].performance_payment_per_mwh",
                    minimum=0.0,
                ),
                flexible_connection_value_per_year=_float_list(
                    item["flexible_connection_value_per_year"],
                    name=f"archetypes[{index}].flexible_connection_value_per_year",
                    minimum=0.0,
                ),
                shortfall_penalty_per_mwh=_nonnegative_float(
                    item, "shortfall_penalty_per_mwh", name=f"archetypes[{index}]"
                ),
                failure_penalty_per_event=_nonnegative_float(
                    item, "failure_penalty_per_event", name=f"archetypes[{index}]"
                ),
            )
        )
    if len({item.archetype_id for item in archetypes}) != len(archetypes):
        raise ValueError("market archetype IDs must be unique")
    return MarketArchetypes(
        schema_version=int(document["schema_version"]),
        currency_basis=str(document["currency_basis"]),  # type: ignore[arg-type]
        analysis_status=str(document["analysis_status"]),  # type: ignore[arg-type]
        archetypes=tuple(archetypes),
    )


def _verify_declared_input_hashes(paths: Mapping[str, tuple[str, str]]) -> dict[str, str]:
    """Fail closed if declared non-code inputs differ from their protocol hashes."""

    observed: dict[str, str] = {}
    for name, (raw_path, expected) in paths.items():
        path = Path(raw_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"economic input hash mismatch: {name}")
        observed[name] = actual
    return observed


def verify_physical_input_hashes(
    specification: EconomicParticipationSpecification,
) -> dict[str, str]:
    """Verify inputs that can change a paired physical replay."""

    return _verify_declared_input_hashes(
        {
            "controller_config": (
                specification.technical.controller_config,
                specification.technical.controller_config_sha256,
            ),
            "technical_certificate": (
                specification.technical.technical_certificate_path,
                specification.technical.technical_certificate_sha256,
            ),
            "technical_certificate_manifest": (
                specification.technical.technical_certificate_manifest,
                specification.technical.technical_certificate_manifest_sha256,
            ),
            "technical_selection": (
                specification.technical.technical_selection_path,
                specification.technical.technical_selection_sha256,
            ),
            "validation_scenario_receipt": (
                specification.technical.validation_scenario_receipt,
                specification.technical.validation_scenario_receipt_sha256,
            ),
            "locked_id_receipt": (
                specification.technical.locked_id_receipt,
                specification.technical.locked_id_receipt_sha256,
            ),
        }
    )


def verify_economic_input_hashes(
    specification: EconomicParticipationSpecification,
) -> dict[str, str]:
    """Verify economics-only coordinates after a physical ledger is loaded."""

    return _verify_declared_input_hashes(
        {
            "cost_parameter_grid": (
                specification.inputs.cost_parameter_grid,
                specification.inputs.cost_parameter_grid_sha256,
            ),
            "market_archetypes": (
                specification.inputs.market_archetypes,
                specification.inputs.market_archetypes_sha256,
            ),
            "source_register": (
                specification.inputs.source_register,
                specification.inputs.source_register_sha256,
            ),
            "external_parameter_evidence": (
                specification.inputs.external_parameter_evidence,
                specification.inputs.external_parameter_evidence_sha256,
            ),
        }
    )


def verify_external_input_hashes(
    specification: EconomicParticipationSpecification,
) -> dict[str, str]:
    """Verify all declared inputs (legacy convenience union of split contracts)."""

    physical = verify_physical_input_hashes(specification)
    economic = verify_economic_input_hashes(specification)
    if set(physical).intersection(economic):
        raise RuntimeError("physical and economic input-hash namespaces must not overlap")
    return {**physical, **economic}
