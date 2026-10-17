"""Tests de la lecture des fichiers CSV."""

from pathlib import Path

import pytest

from child_protection_information_management.csv_io import read_csv

REPORT_COLUMNS = ("report_id", "partner_id", "reporting_period")


def make_file(tmp_path: Path, content: str) -> Path:
    """Crée un fichier CSV temporaire pour un test."""
    path = tmp_path / "reports.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_reads_valid_file(tmp_path: Path) -> None:
    path = make_file(
        tmp_path,
        "report_id,partner_id,reporting_period\nRPT_001,PARTNER_001,2025-03\n",
    )

    records = read_csv(path, REPORT_COLUMNS)

    assert records == [
        {
            "report_id": "RPT_001",
            "partner_id": "PARTNER_001",
            "reporting_period": "2025-03",
        }
    ]


def test_rejects_incorrect_header(tmp_path: Path) -> None:
    path = make_file(
        tmp_path,
        "report_id,partner_id\nRPT_001,PARTNER_001\n",
    )

    with pytest.raises(ValueError, match="colonnes inattendues"):
        read_csv(path, REPORT_COLUMNS)


@pytest.mark.parametrize(
    "row",
    [
        "RPT_001,PARTNER_001\n",
        "RPT_001,PARTNER_001,2025-03,EXTRA\n",
    ],
)
def test_rejects_incorrect_row_size(
    tmp_path: Path,
    row: str,
) -> None:
    path = make_file(
        tmp_path,
        "report_id,partner_id,reporting_period\n" + row,
    )

    with pytest.raises(ValueError, match="colonnes"):
        read_csv(path, REPORT_COLUMNS)


def test_rejects_empty_file(tmp_path: Path) -> None:
    path = make_file(tmp_path, "")

    with pytest.raises(ValueError, match="colonnes inattendues"):
        read_csv(path, REPORT_COLUMNS)


def test_supports_quoted_commas(tmp_path: Path) -> None:
    path = make_file(
        tmp_path,
        'partner_id,partner_name\nPARTNER_001,"Organisation, A"\n',
    )

    records = read_csv(
        path,
        ("partner_id", "partner_name"),
    )

    assert records == [
        {
            "partner_id": "PARTNER_001",
            "partner_name": "Organisation, A",
        }
    ]


def test_raises_if_file_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        read_csv(path, REPORT_COLUMNS)


@pytest.mark.parametrize(
    ("extra_before", "extra_after"),
    [
        ("\n", ""),
        ("", "\n"),
        ("", "   \n"),
    ],
)
def test_rejects_blank_or_whitespace_only_lines(
    tmp_path: Path,
    extra_before: str,
    extra_after: str,
) -> None:
    """Rejette les lignes sans colonnes CSV valides."""

    path = make_file(
        tmp_path,
        "report_id,partner_id,reporting_period\n"
        f"{extra_before}"
        "RPT_001,PARTNER_001,2025-03\n"
        f"{extra_after}",
    )

    with pytest.raises(ValueError, match="colonnes"):
        read_csv(path, REPORT_COLUMNS)


def test_header_only_returns_no_records(tmp_path: Path) -> None:
    """Laisse à l'orchestrateur le contrôle des données absentes."""

    path = make_file(
        tmp_path,
        "report_id,partner_id,reporting_period\n",
    )

    assert read_csv(path, REPORT_COLUMNS) == []


def test_preserves_empty_field_for_business_validation(
    tmp_path: Path,
) -> None:
    """Préserve un champ vide pour que le validateur métier l'examine."""

    path = make_file(
        tmp_path,
        "report_id,partner_id,reporting_period\nRPT_001,,2025-03\n",
    )

    records = read_csv(path, REPORT_COLUMNS)

    assert len(records) == 1
    assert records[0]["partner_id"] == ""
