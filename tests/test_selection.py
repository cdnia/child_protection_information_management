"""Tests de sélection des soumissions approuvées."""

from pathlib import Path

import pytest

from child_protection_information_management.csv_io import read_csv
from child_protection_information_management.selection import (
    select_latest_approved_submissions,
)

SUBMISSION_COLUMNS = (
    "submission_id",
    "report_id",
    "revision_no",
    "previous_submission_id",
    "submitted_at",
    "status",
)


@pytest.fixture
def submissions() -> list[dict[str, str]]:
    """Charge les soumissions synthétiques du projet."""

    path = Path(__file__).resolve().parents[1] / "data" / "raw" / "submissions.csv"

    return read_csv(path, SUBMISSION_COLUMNS)


def test_selects_expected_synthetic_submissions(
    submissions: list[dict[str, str]],
) -> None:
    """Sélectionne les révisions approuvées du jeu synthétique."""

    assert select_latest_approved_submissions(submissions) == {
        "RPT_001": "SUB_002",
        "RPT_002": "SUB_003",
        "RPT_003": "SUB_005",
    }


def test_selection_is_independent_of_row_order(
    submissions: list[dict[str, str]],
) -> None:
    """La sélection ne dépend pas de l'ordre des lignes CSV."""

    selected = select_latest_approved_submissions(list(reversed(submissions)))

    assert selected == {
        "RPT_001": "SUB_002",
        "RPT_002": "SUB_003",
        "RPT_003": "SUB_005",
    }


@pytest.mark.parametrize(
    "status",
    ["RECEIVED", "UNDER_REVIEW", "REJECTED"],
)
def test_unapproved_revision_does_not_replace_approved(
    submissions: list[dict[str, str]],
    status: str,
) -> None:
    """Une révision non approuvée ne remplace pas la précédente."""

    revision = next(row for row in submissions if row["submission_id"] == "SUB_004")
    revision["status"] = status

    selected = select_latest_approved_submissions(submissions)

    assert selected["RPT_002"] == "SUB_003"


def test_excludes_report_without_approved_revision(
    submissions: list[dict[str, str]],
) -> None:
    """Exclut les rapports sans soumission approuvée."""

    revision = next(row for row in submissions if row["submission_id"] == "SUB_003")
    revision["status"] = "REJECTED"

    selected = select_latest_approved_submissions(submissions)

    assert "RPT_002" not in selected
    assert selected["RPT_001"] == "SUB_002"
    assert selected["RPT_003"] == "SUB_005"


def test_empty_input_selects_nothing() -> None:
    """Une liste vide ne produit aucune sélection."""

    assert select_latest_approved_submissions([]) == {}


def test_revision_numbers_are_compared_numerically() -> None:
    """La révision 10 doit être retenue plutôt que la révision 2."""

    submissions = [
        {
            "submission_id": f"SUB_{revision:03d}",
            "report_id": "RPT_001",
            "revision_no": str(revision),
            "previous_submission_id": (
                f"SUB_{revision - 1:03d}" if revision > 1 else ""
            ),
            "submitted_at": f"2025-04-{revision:02d}T09:00:00Z",
            "status": "APPROVED",
        }
        for revision in range(1, 11)
    ]

    assert select_latest_approved_submissions(submissions) == {"RPT_001": "SUB_010"}


def test_selection_does_not_modify_source_data(
    submissions: list[dict[str, str]],
) -> None:
    """La sélection conserve les enregistrements d'origine."""

    original = [row.copy() for row in submissions]

    select_latest_approved_submissions(submissions)

    assert submissions == original
