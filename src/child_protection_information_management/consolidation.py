"""Consolidation des observations issues des soumissions approuvées."""

from dataclasses import dataclass

from .selection import select_latest_approved_submissions


@dataclass(frozen=True, slots=True)
class ConsolidatedResult:
    """Total d'un indicateur pour un mois, une zone et une activité."""

    reporting_period: str
    area_code: str
    activity_code: str
    indicator_code: str
    total_value: int


def consolidate_observations(
    reports: list[dict[str, str]],
    submissions: list[dict[str, str]],
    observations: list[dict[str, str]],
) -> list[ConsolidatedResult]:
    """Regroupe les observations validées des révisions approuvées retenues."""

    latest_approved = select_latest_approved_submissions(submissions)
    report_by_submission = {
        submission_id: report_id for report_id, submission_id in latest_approved.items()
    }
    period_by_report = {
        report["report_id"]: report["reporting_period"] for report in reports
    }
    totals: dict[tuple[str, str, str, str], int] = {}

    for observation in observations:
        report_id = report_by_submission.get(observation["submission_id"])
        if report_id is None:
            continue

        key = (
            period_by_report[report_id],
            observation["area_code"],
            observation["activity_code"],
            observation["indicator_code"],
        )
        totals[key] = totals.get(key, 0) + int(observation["reported_value"])

    return [
        ConsolidatedResult(period, area, activity, indicator, total)
        for (period, area, activity, indicator), total in sorted(totals.items())
    ]
