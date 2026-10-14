"""Tests des règles métier des observations."""

from pathlib import Path

import pytest

from child_protection_information_management.csv_io import read_csv
from child_protection_information_management.observation_validation import (
    validate_observations,
)

SUBMISSIONS = {"SUB_001", "SUB_002"}
AREAS = {"ZONE_A", "ZONE_B"}
ACTIVITIES = {"ACT_COMMUNITY_AWARENESS", "ACT_GROUP_PSYCHOSOCIAL"}
INDICATORS = {"IND_SESSIONS_HELD", "IND_PARTICIPATIONS"}
ALLOWED_PAIRS = {
    (activity, indicator) for activity in ACTIVITIES for indicator in INDICATORS
}


def make_observation(**changes: str) -> dict[str, str]:
    observation = {
        "observation_id": "OBS_001",
        "submission_id": "SUB_001",
        "area_code": "ZONE_A",
        "activity_code": "ACT_COMMUNITY_AWARENESS",
        "indicator_code": "IND_SESSIONS_HELD",
        "reported_value": "8",
    }
    observation.update(changes)
    return observation


def get_issue_codes(
    *observations: dict[str, str],
    allowed_pairs: set[tuple[str, str]] | None = None,
) -> set[str]:
    pairs = ALLOWED_PAIRS if allowed_pairs is None else allowed_pairs

    issues = validate_observations(
        list(observations),
        SUBMISSIONS,
        AREAS,
        ACTIVITIES,
        INDICATORS,
        pairs,
    )
    return {issue.code for issue in issues}


def test_accepts_valid_observation() -> None:
    assert get_issue_codes(make_observation()) == set()


def test_accepts_zero_value() -> None:
    assert get_issue_codes(make_observation(reported_value="0")) == set()


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"submission_id": ""}, "MISSING_SUBMISSION_ID"),
        ({"submission_id": "SUB_999"}, "UNKNOWN_SUBMISSION"),
        ({"area_code": ""}, "MISSING_AREA_CODE"),
        ({"area_code": "ZONE_X"}, "UNKNOWN_AREA"),
        ({"activity_code": ""}, "MISSING_ACTIVITY_CODE"),
        ({"activity_code": "ACT_UNKNOWN"}, "UNKNOWN_ACTIVITY"),
        ({"indicator_code": ""}, "MISSING_INDICATOR_CODE"),
        ({"indicator_code": "IND_UNKNOWN"}, "UNKNOWN_INDICATOR"),
    ],
)
def test_rejects_invalid_references(
    changes: dict[str, str],
    expected_code: str,
) -> None:
    assert expected_code in get_issue_codes(make_observation(**changes))


def test_rejects_missing_observation_id() -> None:
    observation = make_observation(observation_id="")

    assert "MISSING_OBSERVATION_ID" in get_issue_codes(observation)


def test_rejects_duplicate_observation_id() -> None:
    first = make_observation()
    second = make_observation(
        indicator_code="IND_PARTICIPATIONS",
    )

    assert "DUPLICATE_OBSERVATION_ID" in get_issue_codes(first, second)


def test_rejects_duplicate_business_key() -> None:
    first = make_observation()
    second = make_observation(observation_id="OBS_002")

    assert "DUPLICATE_OBSERVATION_KEY" in get_issue_codes(first, second)


def test_rejects_unauthorized_activity_indicator() -> None:
    observation = make_observation(
        indicator_code="IND_PARTICIPATIONS",
    )

    restricted_pairs = {
        ("ACT_COMMUNITY_AWARENESS", "IND_SESSIONS_HELD"),
    }

    assert "UNAUTHORIZED_ACTIVITY_INDICATOR" in get_issue_codes(
        observation,
        allowed_pairs=restricted_pairs,
    )


@pytest.mark.parametrize(
    ("value", "expected_code"),
    [
        ("-1", "INVALID_REPORTED_VALUE"),
        ("12.5", "INVALID_REPORTED_VALUE"),
        ("abc", "INVALID_REPORTED_VALUE"),
        ("+2", "INVALID_REPORTED_VALUE"),
        (" 2 ", "INVALID_REPORTED_VALUE"),
        ("", "MISSING_REPORTED_VALUE"),
    ],
)
def test_rejects_invalid_reported_value(
    value: str,
    expected_code: str,
) -> None:
    assert expected_code in get_issue_codes(make_observation(reported_value=value))


def test_synthetic_observations_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    raw = root / "data/raw"
    reference = root / "data/reference"

    observations = read_csv(
        raw / "observations.csv",
        (
            "observation_id",
            "submission_id",
            "area_code",
            "activity_code",
            "indicator_code",
            "reported_value",
        ),
    )

    submissions = read_csv(
        raw / "submissions.csv",
        (
            "submission_id",
            "report_id",
            "revision_no",
            "previous_submission_id",
            "submitted_at",
            "status",
        ),
    )

    areas = read_csv(
        reference / "areas.csv",
        ("area_code", "area_name", "area_type"),
    )

    activities = read_csv(
        reference / "activities.csv",
        ("activity_code", "activity_name", "activity_description"),
    )

    indicators = read_csv(
        reference / "indicators.csv",
        (
            "indicator_code",
            "indicator_name",
            "indicator_definition",
            "measure_unit",
            "aggregation_method",
        ),
    )

    activity_indicators = read_csv(
        reference / "activity_indicators.csv",
        ("activity_code", "indicator_code"),
    )

    issues = validate_observations(
        observations,
        {row["submission_id"] for row in submissions},
        {row["area_code"] for row in areas},
        {row["activity_code"] for row in activities},
        {row["indicator_code"] for row in indicators},
        {(row["activity_code"], row["indicator_code"]) for row in activity_indicators},
    )

    assert issues == []
    assert len(observations) == 20
