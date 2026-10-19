"""Tests de consolidation des observations validées."""

from pathlib import Path

import pytest

from child_protection_information_management.consolidation import (
    ConsolidatedResult,
    consolidate_observations,
)
from child_protection_information_management.csv_io import read_csv

Rows = list[dict[str, str]]
Datasets = tuple[Rows, Rows, Rows]


@pytest.fixture
def datasets() -> Datasets:
    """Charge les fichiers synthétiques sans modifier les sources."""

    root = Path(__file__).resolve().parents[1] / "data" / "raw"
    return (
        read_csv(root / "reports.csv", ("report_id", "partner_id", "reporting_period")),
        read_csv(
            root / "submissions.csv",
            (
                "submission_id",
                "report_id",
                "revision_no",
                "previous_submission_id",
                "submitted_at",
                "status",
            ),
        ),
        read_csv(
            root / "observations.csv",
            (
                "observation_id",
                "submission_id",
                "area_code",
                "activity_code",
                "indicator_code",
                "reported_value",
            ),
        ),
    )


def test_synthetic_totals(datasets: Datasets) -> None:
    """Retrouve les totaux du jeu synthétique après sélection."""

    reports, submissions, observations = datasets
    results = consolidate_observations(reports, submissions, observations)

    assert len(results) == 12
    assert (
        sum(
            row.total_value
            for row in results
            if row.indicator_code == "IND_SESSIONS_HELD"
        )
        == 28
    )
    assert (
        sum(
            row.total_value
            for row in results
            if row.indicator_code == "IND_PARTICIPATIONS"
        )
        == 652
    )
    assert {row.reporting_period for row in results} == {"2025-03"}


def test_old_and_pending_revisions_are_excluded(datasets: Datasets) -> None:
    """Exclut les anciennes observations et la correction non approuvée."""

    reports, submissions, observations = datasets
    results = consolidate_observations(reports, submissions, observations)
    values = {
        (row.area_code, row.activity_code, row.indicator_code): row.total_value
        for row in results
    }

    assert values["ZONE_A", "ACT_COMMUNITY_AWARENESS", "IND_PARTICIPATIONS"] == 220
    assert values["ZONE_B", "ACT_COMMUNITY_AWARENESS", "IND_SESSIONS_HELD"] == 6


def test_new_approval_replaces_previous_approval(datasets: Datasets) -> None:
    """Remplace les résultats précédents après approbation d'une correction."""

    reports, submissions, observations = datasets
    revision = next(row for row in submissions if row["submission_id"] == "SUB_004")
    revision["status"] = "APPROVED"
    results = consolidate_observations(reports, submissions, observations)

    assert (
        sum(
            row.total_value
            for row in results
            if row.indicator_code == "IND_SESSIONS_HELD"
        )
        == 29
    )
    assert (
        sum(
            row.total_value
            for row in results
            if row.indicator_code == "IND_PARTICIPATIONS"
        )
        == 682
    )


def test_matching_groups_from_different_partners_are_summed(
    datasets: Datasets,
) -> None:
    """Additionne deux déclarations compatibles de partenaires distincts."""

    reports, submissions, observations = datasets
    observation = next(
        row for row in observations if row["observation_id"] == "OBS_018"
    )
    observation["area_code"] = "ZONE_A"
    results = consolidate_observations(reports, submissions, observations)

    assert (
        ConsolidatedResult(
            "2025-03", "ZONE_A", "ACT_COMMUNITY_AWARENESS", "IND_PARTICIPATIONS", 320
        )
        in results
    )
    assert len(results) == 11


def test_reports_without_approval_are_excluded(datasets: Datasets) -> None:
    """Ignore les résultats d'un rapport sans approbation."""

    reports, submissions, observations = datasets
    revision = next(row for row in submissions if row["submission_id"] == "SUB_003")
    revision["status"] = "REJECTED"
    results = consolidate_observations(reports, submissions, observations)

    assert len(results) == 8
    assert (
        sum(
            row.total_value
            for row in results
            if row.indicator_code == "IND_SESSIONS_HELD"
        )
        == 19
    )
    assert (
        sum(
            row.total_value
            for row in results
            if row.indicator_code == "IND_PARTICIPATIONS"
        )
        == 427
    )


def test_result_order_is_stable(datasets: Datasets) -> None:
    """L'ordre des fichiers sources ne change pas les lignes produites."""

    reports, submissions, observations = datasets
    expected = consolidate_observations(reports, submissions, observations)
    actual = consolidate_observations(
        list(reversed(reports)),
        list(reversed(submissions)),
        list(reversed(observations)),
    )

    assert actual == expected


def test_zero_value_is_preserved(datasets: Datasets) -> None:
    """Conserve une observation nulle dans le résultat consolidé."""

    reports, submissions, observations = datasets
    observation = next(
        row for row in observations if row["observation_id"] == "OBS_005"
    )
    observation["reported_value"] = "0"

    results = consolidate_observations(reports, submissions, observations)

    assert (
        ConsolidatedResult(
            "2025-03", "ZONE_A", "ACT_COMMUNITY_AWARENESS", "IND_SESSIONS_HELD", 0
        )
        in results
    )
    assert len(results) == 12


def test_different_reporting_periods_are_not_merged(datasets: Datasets) -> None:
    """Ne mélange pas les résultats de deux périodes de reporting."""

    reports, submissions, observations = datasets
    report = next(row for row in reports if row["report_id"] == "RPT_003")
    report["reporting_period"] = "2025-04"

    results = consolidate_observations(reports, submissions, observations)

    assert {row.reporting_period for row in results} == {"2025-03", "2025-04"}
    assert (
        sum(
            row.total_value
            for row in results
            if row.reporting_period == "2025-03"
            and row.indicator_code == "IND_SESSIONS_HELD"
        )
        == 22
    )
    assert (
        sum(
            row.total_value
            for row in results
            if row.reporting_period == "2025-04"
            and row.indicator_code == "IND_SESSIONS_HELD"
        )
        == 6
    )


def test_no_approved_submissions_returns_no_results(datasets: Datasets) -> None:
    """Ne produit aucun résultat en l'absence d'approbation."""

    reports, submissions, observations = datasets
    for submission in submissions:
        submission["status"] = "REJECTED"

    assert consolidate_observations(reports, submissions, observations) == []


def test_consolidation_does_not_mutate_sources(datasets: Datasets) -> None:
    """Ne modifie aucune des trois tables sources."""

    reports, submissions, observations = datasets
    original_reports = [row.copy() for row in reports]
    original_submissions = [row.copy() for row in submissions]
    original_observations = [row.copy() for row in observations]

    consolidate_observations(reports, submissions, observations)

    assert reports == original_reports
    assert submissions == original_submissions
    assert observations == original_observations
