"""Tests des règles de validation des rapports."""

from pathlib import Path

import pytest

from child_protection_information_management.csv_io import read_csv
from child_protection_information_management.validation import validate_reports


def make_report(
    report_id: str = "RPT_001",
    partner_id: str = "PARTNER_001",
    period: str = "2025-03",
) -> dict[str, str]:
    return {
        "report_id": report_id,
        "partner_id": partner_id,
        "reporting_period": period,
    }


def test_accepts_valid_report() -> None:
    issues = validate_reports(
        [make_report()],
        {"PARTNER_001"},
    )

    assert issues == []


def test_rejects_missing_report_id() -> None:
    issues = validate_reports(
        [make_report(report_id="")],
        {"PARTNER_001"},
    )

    assert any(issue.code == "MISSING_REPORT_ID" for issue in issues)


def test_rejects_duplicate_report_id() -> None:
    reports = [
        make_report(),
        make_report(period="2025-04"),
    ]

    issues = validate_reports(reports, {"PARTNER_001"})

    assert any(issue.code == "DUPLICATE_REPORT_ID" for issue in issues)


def test_rejects_unknown_partner() -> None:
    issues = validate_reports(
        [make_report(partner_id="PARTNER_999")],
        {"PARTNER_001"},
    )

    assert any(issue.code == "UNKNOWN_PARTNER" for issue in issues)


@pytest.mark.parametrize(
    "bad_period",
    ["2025-13", "2025-3"],
)
def test_rejects_invalid_period(bad_period: str) -> None:
    issues = validate_reports(
        [make_report(period=bad_period)],
        {"PARTNER_001"},
    )

    assert any(issue.code == "INVALID_PERIOD" for issue in issues)


def test_rejects_duplicate_partner_period() -> None:
    reports = [
        make_report(report_id="RPT_001"),
        make_report(report_id="RPT_002"),
    ]

    issues = validate_reports(reports, {"PARTNER_001"})

    assert any(issue.code == "DUPLICATE_PARTNER_PERIOD" for issue in issues)


def test_real_synthetic_reports_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]

    reports = read_csv(
        root / "data/raw/reports.csv",
        ("report_id", "partner_id", "reporting_period"),
    )

    partners = read_csv(
        root / "data/reference/partners.csv",
        ("partner_id", "partner_name"),
    )

    partner_ids = {partner["partner_id"] for partner in partners}

    issues = validate_reports(reports, partner_ids)

    assert issues == []
