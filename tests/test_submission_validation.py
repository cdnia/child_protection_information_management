"""Tests de validation des soumissions."""

from pathlib import Path

import pytest

from child_protection_information_management.csv_io import read_csv
from child_protection_information_management.submission_validation import (
    validate_revision_chains,
    validate_submission_periods,
    validate_submissions,
)


def make_submission(
    submission_id: str = "SUB_001",
    report_id: str = "RPT_001",
    revision_no: str = "1",
    submitted_at: str = "2025-04-03T09:00:00Z",
    status: str = "APPROVED",
) -> dict[str, str]:
    return {
        "submission_id": submission_id,
        "report_id": report_id,
        "revision_no": revision_no,
        "previous_submission_id": "",
        "submitted_at": submitted_at,
        "status": status,
    }


def get_issue_codes(*submissions: dict[str, str]) -> set[str]:
    issues = validate_submissions(
        list(submissions),
        {"RPT_001"},
    )
    return {issue.code for issue in issues}


def test_accepts_valid_submission() -> None:
    assert get_issue_codes(make_submission()) == set()


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"submission_id": ""}, "MISSING_SUBMISSION_ID"),
        ({"report_id": ""}, "MISSING_REPORT_ID"),
        ({"report_id": "RPT_999"}, "UNKNOWN_REPORT"),
        ({"revision_no": "0"}, "INVALID_REVISION_NO"),
        ({"revision_no": "-1"}, "INVALID_REVISION_NO"),
        ({"revision_no": "abc"}, "INVALID_REVISION_NO"),
        (
            {"submitted_at": "2025-04-31T09:00:00Z"},
            "INVALID_SUBMISSION_DATE",
        ),
        (
            {"submitted_at": "2025-04-03T25:00:00Z"},
            "INVALID_SUBMISSION_DATE",
        ),
        (
            {"submitted_at": "2025-04-03 09:00:00"},
            "INVALID_SUBMISSION_DATE",
        ),
        ({"status": "PENDING"}, "INVALID_STATUS"),
    ],
)
def test_rejects_invalid_fields(
    changes: dict[str, str],
    expected_code: str,
) -> None:
    submission = make_submission()
    submission.update(changes)

    assert expected_code in get_issue_codes(submission)


def test_rejects_duplicate_submission_id() -> None:
    first = make_submission()
    second = make_submission(revision_no="2")

    assert "DUPLICATE_SUBMISSION_ID" in get_issue_codes(first, second)


def test_rejects_duplicate_report_revision() -> None:
    first = make_submission()
    second = make_submission(submission_id="SUB_002")

    assert "DUPLICATE_REPORT_REVISION" in get_issue_codes(first, second)


def test_synthetic_submissions_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]

    submissions = read_csv(
        root / "data/raw/submissions.csv",
        (
            "submission_id",
            "report_id",
            "revision_no",
            "previous_submission_id",
            "submitted_at",
            "status",
        ),
    )

    reports = read_csv(
        root / "data/raw/reports.csv",
        ("report_id", "partner_id", "reporting_period"),
    )

    report_ids = {report["report_id"] for report in reports}

    issues = validate_submissions(submissions, report_ids)

    assert issues == []


def make_revision_pair() -> tuple[dict[str, str], dict[str, str]]:
    """Construit deux révisions cohérentes d'un même rapport."""

    initial = make_submission()

    correction = make_submission(
        submission_id="SUB_002",
        revision_no="2",
        submitted_at="2025-04-07T11:30:00Z",
    )
    correction["previous_submission_id"] = "SUB_001"

    return initial, correction


def get_revision_issue_codes(
    *submissions: dict[str, str],
) -> set[str]:
    issues = validate_revision_chains(list(submissions))
    return {issue.code for issue in issues}


def test_accepts_valid_revision_chain() -> None:
    initial, correction = make_revision_pair()

    assert get_revision_issue_codes(initial, correction) == set()


def test_rejects_previous_on_first_revision() -> None:
    initial = make_submission()
    initial["previous_submission_id"] = "SUB_999"

    assert "FIRST_REVISION_HAS_PREVIOUS" in get_revision_issue_codes(initial)


def test_rejects_missing_previous_revision() -> None:
    initial, correction = make_revision_pair()
    correction["previous_submission_id"] = ""

    assert "MISSING_PREVIOUS_SUBMISSION" in get_revision_issue_codes(
        initial, correction
    )


def test_rejects_unknown_previous_submission() -> None:
    initial, correction = make_revision_pair()
    correction["previous_submission_id"] = "SUB_999"

    assert "UNKNOWN_PREVIOUS_SUBMISSION" in get_revision_issue_codes(
        initial, correction
    )


def test_rejects_previous_from_another_report() -> None:
    initial, correction = make_revision_pair()
    correction["report_id"] = "RPT_002"

    assert "PREVIOUS_SUBMISSION_WRONG_REPORT" in get_revision_issue_codes(
        initial, correction
    )


def test_rejects_nonconsecutive_revision() -> None:
    initial, correction = make_revision_pair()
    correction["revision_no"] = "3"

    assert "NON_CONSECUTIVE_REVISION" in get_revision_issue_codes(initial, correction)


@pytest.mark.parametrize(
    "incorrect_date",
    [
        "2025-04-03T08:00:00Z",
        "2025-04-03T09:00:00Z",
    ],
)
def test_rejects_nonchronological_revision(
    incorrect_date: str,
) -> None:
    initial, correction = make_revision_pair()
    correction["submitted_at"] = incorrect_date

    assert "NON_CHRONOLOGICAL_REVISION" in get_revision_issue_codes(initial, correction)


def test_revision_validation_is_independent_of_row_order() -> None:
    initial, correction = make_revision_pair()

    assert get_revision_issue_codes(correction, initial) == set()


def test_synthetic_revision_chains_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]

    submissions = read_csv(
        root / "data/raw/submissions.csv",
        (
            "submission_id",
            "report_id",
            "revision_no",
            "previous_submission_id",
            "submitted_at",
            "status",
        ),
    )

    assert validate_revision_chains(submissions) == []


@pytest.mark.parametrize(
    ("reporting_period", "submitted_at", "expected_codes"),
    [
        (
            "2025-03",
            "2025-02-28T23:59:59Z",
            {"SUBMISSION_BEFORE_REPORT_PERIOD"},
        ),
        ("2025-03", "2025-03-01T00:00:00Z", set()),
        ("2025-03", "2025-03-01T00:00:01Z", set()),
        ("2025-03", "2025-03-31T23:59:59Z", set()),
        ("2025-03", "2025-04-03T09:00:00Z", set()),
        (
            "2025-01",
            "2024-12-31T23:59:59Z",
            {"SUBMISSION_BEFORE_REPORT_PERIOD"},
        ),
        (
            "2025-12",
            "2025-11-30T23:59:59Z",
            {"SUBMISSION_BEFORE_REPORT_PERIOD"},
        ),
        ("2025-12", "2026-01-01T00:00:00Z", set()),
    ],
)
def test_submission_period_boundaries(
    reporting_period: str,
    submitted_at: str,
    expected_codes: set[str],
) -> None:
    """Vérifie les limites mensuelles et les changements d'année."""

    submission = make_submission(submitted_at=submitted_at)
    reports = [
        {
            "report_id": "RPT_001",
            "reporting_period": reporting_period,
        }
    ]

    issues = validate_submission_periods([submission], reports)

    assert {issue.code for issue in issues} == expected_codes

    if expected_codes:
        assert len(issues) == 1
        assert issues[0].record_number == 1
        assert issues[0].field == "submitted_at"


def test_submission_period_uses_matching_report() -> None:
    """Compare chaque soumission à son propre rapport."""

    submission = make_submission(
        report_id="RPT_002",
        submitted_at="2025-02-01T09:00:00Z",
    )
    reports = [
        {
            "report_id": "RPT_001",
            "reporting_period": "2025-01",
        },
        {
            "report_id": "RPT_002",
            "reporting_period": "2025-03",
        },
    ]

    issues = validate_submission_periods([submission], reports)

    assert len(issues) == 1
    assert issues[0].code == "SUBMISSION_BEFORE_REPORT_PERIOD"
    assert issues[0].record_number == 1
    assert issues[0].field == "submitted_at"
