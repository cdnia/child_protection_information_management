"""Orchestration de la validation et de la consolidation."""

from pathlib import Path

from .consolidation import ConsolidatedResult, consolidate_observations
from .csv_io import read_csv
from .pipeline import run_validation


def run_consolidation(project_root: Path) -> list[ConsolidatedResult]:
    """Valide un lot avant de consolider ses observations."""

    validation_results = run_validation(project_root)

    for stage, result in validation_results.items():
        if result.status == "FAIL":
            codes = ", ".join(issue.code for issue in result.issues)
            raise ValueError(f"Consolidation refusée : {stage} ({codes}).")

    if any(result.status != "PASS" for result in validation_results.values()):
        raise ValueError("Consolidation refusée : validation incomplète.")

    raw_directory = project_root / "data" / "raw"

    reports = read_csv(
        raw_directory / "reports.csv",
        ("report_id", "partner_id", "reporting_period"),
    )

    submissions = read_csv(
        raw_directory / "submissions.csv",
        (
            "submission_id",
            "report_id",
            "revision_no",
            "previous_submission_id",
            "submitted_at",
            "status",
        ),
    )

    observations = read_csv(
        raw_directory / "observations.csv",
        (
            "observation_id",
            "submission_id",
            "area_code",
            "activity_code",
            "indicator_code",
            "reported_value",
        ),
    )

    return consolidate_observations(
        reports,
        submissions,
        observations,
    )
