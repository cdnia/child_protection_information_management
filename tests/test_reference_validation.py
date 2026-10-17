"""Tests des cinq référentiels synthétiques."""

from copy import deepcopy
from pathlib import Path

from child_protection_information_management.csv_io import read_csv
from child_protection_information_management.reference_validation import (
    REFERENCE_SCHEMAS,
    validate_reference_tables,
)


def make_references() -> dict[str, list[dict[str, str]]]:
    """Crée cinq petits référentiels cohérents pour les tests."""

    return {
        "partners": [
            {
                "partner_id": "PARTNER_001",
                "partner_name": "Organisation A",
            },
        ],
        "areas": [
            {
                "area_code": "ZONE_A",
                "area_name": "Zone A",
                "area_type": "SIMULATED_ZONE",
            },
        ],
        "activities": [
            {
                "activity_code": "ACT_A",
                "activity_name": "Activité A",
                "activity_description": "Exercice fictif",
            },
        ],
        "indicators": [
            {
                "indicator_code": "IND_A",
                "indicator_name": "Séances",
                "indicator_definition": "Nombre de séances",
                "measure_unit": "SESSION",
                "aggregation_method": "SUM",
            },
        ],
        "activity_indicators": [
            {
                "activity_code": "ACT_A",
                "indicator_code": "IND_A",
            },
        ],
    }


def issue_codes(
    references: dict[str, list[dict[str, str]]],
    table: str,
) -> set[str]:
    return {issue.code for issue in validate_reference_tables(references)[table]}


def test_accepts_valid_reference_tables() -> None:
    issues = validate_reference_tables(make_references())

    assert all(not table_issues for table_issues in issues.values())


def test_rejects_duplicate_keys_in_each_table() -> None:
    for table in REFERENCE_SCHEMAS:
        references = make_references()
        references[table].append(references[table][0].copy())

        assert "DUPLICATE_REFERENCE_KEY" in issue_codes(references, table), table


def test_rejects_missing_primary_identifier() -> None:
    references = make_references()
    references["partners"][0]["partner_id"] = " "

    assert "MISSING_REFERENCE_VALUE" in issue_codes(references, "partners")


def test_rejects_missing_description() -> None:
    references = make_references()
    references["indicators"][0]["indicator_definition"] = ""

    assert "MISSING_REFERENCE_VALUE" in issue_codes(references, "indicators")


def test_rejects_unknown_activity_in_link_table() -> None:
    references = make_references()
    references["activity_indicators"][0]["activity_code"] = "ACT_UNKNOWN"

    assert "UNKNOWN_REFERENCE_ACTIVITY" in issue_codes(
        references, "activity_indicators"
    )


def test_rejects_unknown_indicator_in_link_table() -> None:
    references = make_references()
    references["activity_indicators"][0]["indicator_code"] = "IND_UNKNOWN"

    assert "UNKNOWN_REFERENCE_INDICATOR" in issue_codes(
        references, "activity_indicators"
    )


def test_rejects_missing_reference_table() -> None:
    references = make_references()
    del references["areas"]

    assert "MISSING_REFERENCE_TABLE" in issue_codes(references, "areas")


def test_rejects_empty_reference_table() -> None:
    references = make_references()
    references["indicators"] = []

    assert "EMPTY_REFERENCE_TABLE" in issue_codes(references, "indicators")


def test_does_not_modify_reference_data() -> None:
    references = make_references()
    original = deepcopy(references)

    validate_reference_tables(references)

    assert references == original


def test_existing_synthetic_references_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]

    references = {
        name: read_csv(
            root / "data/reference" / f"{name}.csv",
            columns,
        )
        for name, columns in REFERENCE_SCHEMAS.items()
    }

    issues = validate_reference_tables(references)

    assert all(not table_issues for table_issues in issues.values()), issues


def test_rejects_unsupported_area_type() -> None:
    """Rejette un type de zone non défini dans le prototype."""

    references = make_references()
    references["areas"][0]["area_type"] = "UNKNOWN_TYPE"

    assert "INVALID_AREA_TYPE" in issue_codes(references, "areas")


def test_rejects_unsupported_aggregation_method() -> None:
    """Rejette une méthode d'agrégation non autorisée."""

    references = make_references()
    references["indicators"][0]["aggregation_method"] = "AVERAGE"

    assert "INVALID_AGGREGATION_METHOD" in issue_codes(
        references,
        "indicators",
    )


def test_rejects_incorrect_unit_for_sessions() -> None:
    """Rejette une unité incompatible avec les séances."""

    references = make_references()
    references["indicators"][0]["indicator_code"] = "IND_SESSIONS_HELD"
    references["indicators"][0]["measure_unit"] = "PARTICIPATION"
    references["activity_indicators"][0]["indicator_code"] = "IND_SESSIONS_HELD"

    assert "INVALID_INDICATOR_UNIT" in issue_codes(
        references,
        "indicators",
    )


def test_rejects_incorrect_unit_for_participations() -> None:
    """Rejette une unité incompatible avec les participations."""

    references = make_references()
    references["indicators"][0]["indicator_code"] = "IND_PARTICIPATIONS"
    references["indicators"][0]["measure_unit"] = "SESSION"
    references["activity_indicators"][0]["indicator_code"] = "IND_PARTICIPATIONS"

    assert "INVALID_INDICATOR_UNIT" in issue_codes(
        references,
        "indicators",
    )
