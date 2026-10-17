"""Tests du processus progressif de validation."""

import csv
import shutil
from pathlib import Path

import pytest

from child_protection_information_management.pipeline import run_validation
from child_protection_information_management.reference_validation import (
    REFERENCE_SCHEMAS,
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Prépare une copie temporaire des fichiers à valider."""

    source = Path(__file__).resolve().parents[1] / "data" / "reference"
    destination = tmp_path / "data" / "reference"
    destination.mkdir(parents=True)

    for table_name in REFERENCE_SCHEMAS:
        filename = f"{table_name}.csv"
        shutil.copyfile(source / filename, destination / filename)

    raw_destination = tmp_path / "data" / "raw"
    raw_destination.mkdir(parents=True)

    for filename in ("reports.csv", "submissions.csv", "observations.csv"):
        shutil.copyfile(
            source.parent / "raw" / filename,
            raw_destination / filename,
        )

    return tmp_path


def test_valid_pipeline_all_stages(project_root: Path) -> None:
    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["references"].issues == ()

    assert results["reports"].status == "PASS"
    assert results["submissions"].status == "PASS"
    assert results["submissions"].issues == ()
    assert results["revision_chains"].status == "PASS"
    assert results["revision_chains"].issues == ()
    assert results["observations"].status == "PASS"
    assert results["observations"].issues == ()


def test_missing_reference_file_blocks_validation(
    project_root: Path,
) -> None:
    path = project_root / "data/reference/partners.csv"
    path.unlink()

    results = run_validation(project_root)

    assert results["references"].status == "FAIL"
    assert any(
        issue.code == "REFERENCE_READ_ERROR" for issue in results["references"].issues
    )

    assert results["reports"].status == "SKIPPED"
    assert results["reports"].reason == "Référentiels non valides."


def test_invalid_reference_header_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/reference/partners.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace(
            "partner_id,partner_name",
            "partner_id,wrong_name",
            1,
        ),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["references"].status == "FAIL"
    assert any(
        issue.code == "REFERENCE_READ_ERROR" for issue in results["references"].issues
    )


def test_unknown_reference_activity_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/reference/activity_indicators.csv"

    with path.open("a", encoding="utf-8") as file:
        file.write("ACT_UNKNOWN,IND_SESSIONS_HELD\n")

    results = run_validation(project_root)

    assert results["references"].status == "FAIL"
    assert any(
        issue.code == "UNKNOWN_REFERENCE_ACTIVITY"
        for issue in results["references"].issues
    )


def test_duplicate_reference_key_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/reference/partners.csv"
    content = path.read_text(encoding="utf-8")
    first_record = content.splitlines()[1]

    path.write_text(
        content + first_record + "\n",
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["references"].status == "FAIL"
    assert any(
        issue.code == "DUPLICATE_REFERENCE_KEY"
        for issue in results["references"].issues
    )


def test_missing_reports_file_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/reports.csv"
    path.unlink()

    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["reports"].status == "FAIL"
    assert any(issue.code == "REPORT_READ_ERROR" for issue in results["reports"].issues)

    for stage in ("submissions", "revision_chains", "observations"):
        assert results[stage].status == "SKIPPED"
        assert results[stage].reason == "Rapports non valides."


def test_invalid_reports_header_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/reports.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace(
            "report_id,partner_id,reporting_period",
            "wrong_id,partner_id,reporting_period",
            1,
        ),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["reports"].status == "FAIL"
    assert any(issue.code == "REPORT_READ_ERROR" for issue in results["reports"].issues)


def test_unknown_report_partner_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/reports.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace(
            "PARTNER_001",
            "PARTNER_UNKNOWN",
            1,
        ),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["reports"].status == "FAIL"
    assert any(issue.code == "UNKNOWN_PARTNER" for issue in results["reports"].issues)


def test_duplicate_partner_period_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/reports.csv"
    lines = path.read_text(encoding="utf-8").splitlines()

    duplicate_fields = lines[1].split(",")
    duplicate_fields[0] = "RPT_999"

    path.write_text(
        "\n".join([*lines, ",".join(duplicate_fields)]) + "\n",
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["reports"].status == "FAIL"
    assert any(
        issue.code == "DUPLICATE_PARTNER_PERIOD" for issue in results["reports"].issues
    )


def test_invalid_reporting_period_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/reports.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace("2025-03", "2025-13", 1),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["reports"].status == "FAIL"
    assert any(issue.code == "INVALID_PERIOD" for issue in results["reports"].issues)


def test_missing_submissions_file_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/submissions.csv"
    path.unlink()

    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["reports"].status == "PASS"
    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "SUBMISSION_READ_ERROR" for issue in results["submissions"].issues
    )

    for stage in ("revision_chains", "observations"):
        assert results[stage].status == "SKIPPED"
        assert results[stage].reason == "Soumissions non valides."


def test_invalid_submissions_header_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/submissions.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace(
        "submission_id",
        "incorrect_id",
        1,
    )

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "SUBMISSION_READ_ERROR" for issue in results["submissions"].issues
    )


def test_unknown_submission_report_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/submissions.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace(
            "SUB_001,RPT_001,1",
            "SUB_001,RPT_UNKNOWN,1",
            1,
        ),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["reports"].status == "PASS"
    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "UNKNOWN_REPORT" for issue in results["submissions"].issues
    )


def test_duplicate_report_revision_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/submissions.csv"
    lines = path.read_text(encoding="utf-8").splitlines()

    duplicate_fields = lines[1].split(",")
    duplicate_fields[0] = "SUB_999"

    path.write_text(
        "\n".join([*lines, ",".join(duplicate_fields)]) + "\n",
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "DUPLICATE_REPORT_REVISION"
        for issue in results["submissions"].issues
    )


def test_invalid_submission_date_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/submissions.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace(
            "2025-04-03T09:00:00Z",
            "2025-02-30T09:00:00Z",
            1,
        ),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "INVALID_SUBMISSION_DATE"
        for issue in results["submissions"].issues
    )


def test_invalid_submission_status_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/submissions.csv"
    content = path.read_text(encoding="utf-8")

    path.write_text(
        content.replace("RECEIVED", "DRAFT", 1),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "INVALID_STATUS" for issue in results["submissions"].issues
    )


def change_submission(
    project_root: Path,
    old: str,
    new: str,
) -> None:
    """Modifie une occurrence dans une copie temporaire des soumissions."""

    path = project_root / "data/raw/submissions.csv"
    content = path.read_text(encoding="utf-8")

    assert content.count(old) == 1

    path.write_text(
        content.replace(old, new, 1),
        encoding="utf-8",
    )


def assert_revision_failure(
    project_root: Path,
    expected_code: str,
) -> None:
    """Vérifie qu'une chaîne invalide bloque les observations."""

    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["reports"].status == "PASS"
    assert results["submissions"].status == "PASS"

    assert results["revision_chains"].status == "FAIL"
    assert expected_code in {issue.code for issue in results["revision_chains"].issues}

    assert results["observations"].status == "SKIPPED"
    assert results["observations"].reason == "Chaînes de révision non valides."


def test_first_revision_cannot_have_previous(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "SUB_001,RPT_001,1,,",
        "SUB_001,RPT_001,1,SUB_003,",
    )

    assert_revision_failure(
        project_root,
        "FIRST_REVISION_HAS_PREVIOUS",
    )


def test_missing_previous_submission_is_detected(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "SUB_002,RPT_001,2,SUB_001,",
        "SUB_002,RPT_001,2,,",
    )

    assert_revision_failure(
        project_root,
        "MISSING_PREVIOUS_SUBMISSION",
    )


def test_unknown_previous_submission_is_detected(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "SUB_002,RPT_001,2,SUB_001,",
        "SUB_002,RPT_001,2,SUB_UNKNOWN,",
    )

    assert_revision_failure(
        project_root,
        "UNKNOWN_PREVIOUS_SUBMISSION",
    )


def test_previous_submission_from_wrong_report_is_detected(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "SUB_002,RPT_001,2,SUB_001,",
        "SUB_002,RPT_001,2,SUB_003,",
    )

    assert_revision_failure(
        project_root,
        "PREVIOUS_SUBMISSION_WRONG_REPORT",
    )


def test_non_consecutive_revision_is_detected(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "SUB_002,RPT_001,2,SUB_001,",
        "SUB_002,RPT_001,3,SUB_001,",
    )

    assert_revision_failure(
        project_root,
        "NON_CONSECUTIVE_REVISION",
    )


def test_non_chronological_revision_is_detected(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "2025-04-07T11:30:00Z",
        "2025-04-02T11:30:00Z",
    )

    assert_revision_failure(
        project_root,
        "NON_CHRONOLOGICAL_REVISION",
    )


def test_invalid_submission_skips_revision_validation(
    project_root: Path,
) -> None:
    change_submission(
        project_root,
        "SUB_002,RPT_001,2,SUB_001,",
        "SUB_002,RPT_001,0,SUB_001,",
    )

    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["reports"].status == "PASS"
    assert results["submissions"].status == "FAIL"
    assert any(
        issue.code == "INVALID_REVISION_NO" for issue in results["submissions"].issues
    )

    assert results["revision_chains"].status == "SKIPPED"
    assert results["revision_chains"].reason == "Soumissions non valides."

    assert results["observations"].status == "SKIPPED"
    assert results["observations"].reason == "Soumissions non valides."


def change_first_observation(
    project_root: Path,
    field: str,
    value: str,
) -> None:
    """Modifie une observation dans une copie temporaire du CSV."""

    path = project_root / "data/raw/observations.csv"

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        assert columns is not None
        rows = list(reader)

    assert rows
    assert field in columns
    rows[0][field] = value

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_missing_observations_file_is_detected(project_root: Path) -> None:
    (project_root / "data/raw/observations.csv").unlink()

    results = run_validation(project_root)

    assert results["revision_chains"].status == "PASS"
    assert results["observations"].status == "FAIL"
    assert "OBSERVATION_READ_ERROR" in {
        issue.code for issue in results["observations"].issues
    }


def test_invalid_observations_header_is_detected(project_root: Path) -> None:
    path = project_root / "data/raw/observations.csv"
    content = path.read_text(encoding="utf-8")
    assert content.startswith("observation_id,submission_id,")

    path.write_text(
        content.replace(
            "observation_id,submission_id,",
            "incorrect_id,submission_id,",
            1,
        ),
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["observations"].status == "FAIL"
    assert "OBSERVATION_READ_ERROR" in {
        issue.code for issue in results["observations"].issues
    }


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("submission_id", "SUB_UNKNOWN", "UNKNOWN_SUBMISSION"),
        ("area_code", "ZONE_UNKNOWN", "UNKNOWN_AREA"),
        ("activity_code", "ACT_UNKNOWN", "UNKNOWN_ACTIVITY"),
        ("indicator_code", "IND_UNKNOWN", "UNKNOWN_INDICATOR"),
    ],
)
def test_unknown_observation_reference_is_detected(
    project_root: Path,
    field: str,
    value: str,
    expected_code: str,
) -> None:
    change_first_observation(project_root, field, value)
    results = run_validation(project_root)

    for stage in ("references", "reports", "submissions", "revision_chains"):
        assert results[stage].status == "PASS"

    assert results["observations"].status == "FAIL"
    assert expected_code in {issue.code for issue in results["observations"].issues}


def test_unauthorized_activity_indicator_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/reference/activity_indicators.csv"
    lines = path.read_text(encoding="utf-8").splitlines()

    pair = "ACT_COMMUNITY_AWARENESS,IND_SESSIONS_HELD"
    assert pair in lines

    lines.remove(pair)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    results = run_validation(project_root)

    assert results["references"].status == "PASS"
    assert results["revision_chains"].status == "PASS"
    assert results["observations"].status == "FAIL"
    assert "UNAUTHORIZED_ACTIVITY_INDICATOR" in {
        issue.code for issue in results["observations"].issues
    }


def test_duplicate_observation_id_is_detected(
    project_root: Path,
) -> None:
    change_first_observation(project_root, "observation_id", "OBS_002")
    results = run_validation(project_root)

    assert results["observations"].status == "FAIL"
    assert "DUPLICATE_OBSERVATION_ID" in {
        issue.code for issue in results["observations"].issues
    }


def test_duplicate_observation_key_is_detected(
    project_root: Path,
) -> None:
    path = project_root / "data/raw/observations.csv"
    lines = path.read_text(encoding="utf-8").splitlines()

    first_id, remaining_fields = lines[1].split(",", 1)
    assert first_id == "OBS_001"

    duplicated_record = f"OBS_DUPLICATE,{remaining_fields}"

    path.write_text(
        "\n".join([*lines, duplicated_record]) + "\n",
        encoding="utf-8",
    )

    results = run_validation(project_root)

    assert results["observations"].status == "FAIL"
    assert "DUPLICATE_OBSERVATION_KEY" in {
        issue.code for issue in results["observations"].issues
    }


@pytest.mark.parametrize(
    ("value", "expected_code"),
    [
        ("-1", "INVALID_REPORTED_VALUE"),
        ("", "MISSING_REPORTED_VALUE"),
    ],
)
def test_invalid_observation_value_is_detected(
    project_root: Path,
    value: str,
    expected_code: str,
) -> None:
    change_first_observation(project_root, "reported_value", value)
    results = run_validation(project_root)

    assert results["observations"].status == "FAIL"
    assert expected_code in {issue.code for issue in results["observations"].issues}


def test_zero_observation_value_is_accepted(
    project_root: Path,
) -> None:
    change_first_observation(project_root, "reported_value", "0")
    results = run_validation(project_root)

    assert all(result.status == "PASS" for result in results.values())
