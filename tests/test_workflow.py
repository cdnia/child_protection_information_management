"""Tests du parcours de validation et de consolidation."""

import shutil
from pathlib import Path

import pytest

from child_protection_information_management.reference_validation import (
    REFERENCE_SCHEMAS,
)
from child_protection_information_management.workflow import run_consolidation


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Copie les huit fichiers CSV dans un dossier temporaire."""

    source = Path(__file__).resolve().parents[1] / "data"
    reference_directory = tmp_path / "data" / "reference"
    raw_directory = tmp_path / "data" / "raw"

    reference_directory.mkdir(parents=True)
    raw_directory.mkdir(parents=True)

    for table_name in REFERENCE_SCHEMAS:
        filename = f"{table_name}.csv"
        shutil.copyfile(
            source / "reference" / filename,
            reference_directory / filename,
        )

    for filename in ("reports.csv", "submissions.csv", "observations.csv"):
        shutil.copyfile(
            source / "raw" / filename,
            raw_directory / filename,
        )

    return tmp_path


def test_valid_project_is_consolidated(project_root: Path) -> None:
    """Consolide un lot qui a réussi les cinq validations."""

    results = run_consolidation(project_root)

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


@pytest.mark.parametrize(
    ("relative_path", "original", "replacement", "expected_code"),
    [
        (
            "data/reference/areas.csv",
            "SIMULATED_ZONE",
            "UNKNOWN_TYPE",
            "INVALID_AREA_TYPE",
        ),
        (
            "data/raw/reports.csv",
            "PARTNER_001",
            "PARTNER_UNKNOWN",
            "UNKNOWN_PARTNER",
        ),
        (
            "data/raw/submissions.csv",
            "2025-04-03T09:00:00Z",
            "2025-02-28T23:59:59Z",
            "SUBMISSION_BEFORE_REPORT_PERIOD",
        ),
        (
            "data/raw/observations.csv",
            "SUB_001",
            "SUB_UNKNOWN",
            "UNKNOWN_SUBMISSION",
        ),
    ],
)
def test_invalid_data_prevents_consolidation(
    project_root: Path,
    relative_path: str,
    original: str,
    replacement: str,
    expected_code: str,
) -> None:
    """Refuse la consolidation lorsqu'une validation échoue."""

    path = project_root / relative_path
    content = path.read_text(encoding="utf-8")
    assert original in content

    path.write_text(
        content.replace(original, replacement, 1),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=expected_code):
        run_consolidation(project_root)


def test_missing_observations_prevent_consolidation(
    project_root: Path,
) -> None:
    """Refuse de calculer lorsque le fichier des observations manque."""

    path = project_root / "data/raw/observations.csv"
    path.unlink()

    with pytest.raises(ValueError, match="OBSERVATION_READ_ERROR"):
        run_consolidation(project_root)


def test_valid_project_without_approvals_returns_no_results(
    project_root: Path,
) -> None:
    """Un lot valide sans approbation ne produit aucun résultat consolidé."""

    path = project_root / "data/raw/submissions.csv"
    content = path.read_text(encoding="utf-8")

    assert content.count("APPROVED") == 4
    path.write_text(
        content.replace("APPROVED", "REJECTED"),
        encoding="utf-8",
    )

    assert run_consolidation(project_root) == []
