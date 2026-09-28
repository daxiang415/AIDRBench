"""Schema and referential-integrity tests for external economic evidence."""

from __future__ import annotations

import re

import pandas as pd

SOURCE_REGISTER = "data/economics/source_register.csv"
EVIDENCE_REGISTER = "data/economics/external_parameter_evidence.csv"

EVIDENCE_COLUMNS = (
    "evidence_id",
    "input_id",
    "parameter_family",
    "source_title",
    "source_organization",
    "source_url",
    "publication_or_reporting_year",
    "access_date",
    "observed_value",
    "unit",
    "currency_year",
    "support_level",
    "replaceability",
    "permitted_use",
    "forbidden_interpretation",
)


def test_external_parameter_evidence_schema_and_nonempty_values() -> None:
    evidence = pd.read_csv(EVIDENCE_REGISTER, dtype=str, keep_default_na=False)

    assert tuple(evidence.columns) == EVIDENCE_COLUMNS
    assert not evidence.empty
    assert not (evidence.apply(lambda column: column.str.strip()) == "").any().any()
    assert evidence["evidence_id"].is_unique
    assert all(re.fullmatch(r"[A-Z0-9_]+", item) for item in evidence["evidence_id"])
    assert set(evidence["support_level"]) <= {
        "direct_market_observation",
        "external_range_anchor",
        "context_only",
    }
    assert set(evidence["replaceability"]) <= {
        "product_overlay_only",
        "sensitivity_only",
        "not_convertible",
    }
    assert evidence["access_date"].eq("2026-09-04").all()


def test_external_parameter_evidence_has_one_url_per_row_and_known_inputs() -> None:
    evidence = pd.read_csv(EVIDENCE_REGISTER, dtype=str, keep_default_na=False)
    register = pd.read_csv(SOURCE_REGISTER, dtype=str, keep_default_na=False)

    assert set(evidence["input_id"]) <= set(register["input_id"])
    assert evidence["source_url"].str.startswith("https://").all()
    assert evidence["source_url"].str.count("https://").eq(1).all()
    assert not evidence["source_url"].str.contains(r"\s\|\s", regex=True).any()


def test_source_register_evidence_references_resolve_or_are_explicitly_absent() -> None:
    evidence = pd.read_csv(EVIDENCE_REGISTER, dtype=str, keep_default_na=False)
    register = pd.read_csv(SOURCE_REGISTER, dtype=str, keep_default_na=False)
    evidence_ids = set(evidence["evidence_id"])

    for row in register.itertuples(index=False):
        reference = row.external_evidence_reference
        if reference in {
            "not_applicable_internal_certificate",
            "no_transferable_external_cost_evidence_identified",
        }:
            continue
        referenced_ids = {item.strip() for item in reference.split(";")}
        assert referenced_ids
        assert referenced_ids <= evidence_ids
        assert set(
            evidence.loc[evidence["evidence_id"].isin(referenced_ids), "input_id"]
        ) == {row.input_id}


def test_external_parameter_evidence_has_no_duplicate_records() -> None:
    evidence = pd.read_csv(EVIDENCE_REGISTER, dtype=str, keep_default_na=False)

    comparison_columns = [
        "input_id",
        "parameter_family",
        "source_url",
        "observed_value",
        "unit",
    ]
    assert not evidence.duplicated(subset=comparison_columns).any()
