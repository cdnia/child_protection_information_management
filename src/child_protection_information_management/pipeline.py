"""Orchestration progressive de la validation des données."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .csv_io import read_csv
from .observation_validation import validate_observations
from .reference_validation import REFERENCE_SCHEMAS, validate_reference_tables
from .submission_validation import validate_revision_chains, validate_submissions
from .validation import ValidationIssue, validate_reports

StageStatus = Literal["PASS", "FAIL", "SKIPPED"]

STAGES = (
    "references",
    "reports",
    "submissions",
    "revision_chains",
    "observations",
)


@dataclass(frozen=True, slots=True)
class StageResult:
    """Résultat d'une étape du processus de validation."""

    status: StageStatus
    issues: tuple[ValidationIssue, ...] = ()
    reason: str = ""


def run_validation(project_root: Path) -> dict[str, StageResult]:
    """Exécute les cinq étapes de validation des données."""

    results = {
        stage: StageResult(
            "SKIPPED",
            reason="Étape non encore intégrée.",
        )
        for stage in STAGES
    }

    references: dict[str, list[dict[str, str]]] = {}
    errors: list[ValidationIssue] = []

    # Lire chaque référentiel en vérifiant sa structure.
    for table_name, columns in REFERENCE_SCHEMAS.items():
        path = project_root / "data" / "reference" / f"{table_name}.csv"

        try:
            references[table_name] = read_csv(path, columns)
        except (OSError, UnicodeError, csv.Error, ValueError) as error:
            errors.append(
                ValidationIssue(
                    0,
                    "",
                    "REFERENCE_READ_ERROR",
                    f"{table_name}.csv : {error}",
                )
            )

    # Les règles métier nécessitent des fichiers lisibles.
    if not errors:
        table_issues = validate_reference_tables(references)

        for table_name, issues in table_issues.items():
            for issue in issues:
                errors.append(
                    ValidationIssue(
                        issue.record_number,
                        issue.field,
                        issue.code,
                        f"{table_name}.csv : {issue.message}",
                    )
                )

    if errors:
        results["references"] = StageResult(
            "FAIL",
            issues=tuple(errors),
        )

        for stage in STAGES[1:]:
            results[stage] = StageResult(
                "SKIPPED",
                reason="Référentiels non valides.",
            )

        return results

    results["references"] = StageResult("PASS")

    # Les rapports dépendent du référentiel des partenaires.
    reports_path = project_root / "data" / "raw" / "reports.csv"

    try:
        reports = read_csv(
            reports_path,
            ("report_id", "partner_id", "reporting_period"),
        )
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        results["reports"] = StageResult(
            "FAIL",
            issues=(
                ValidationIssue(
                    0,
                    "",
                    "REPORT_READ_ERROR",
                    f"reports.csv : {error}",
                ),
            ),
        )
    else:
        partner_ids = {row["partner_id"] for row in references["partners"]}

        report_issues = validate_reports(reports, partner_ids)

        if report_issues:
            results["reports"] = StageResult(
                "FAIL",
                issues=tuple(report_issues),
            )
        else:
            results["reports"] = StageResult("PASS")

    if results["reports"].status == "FAIL":
        for stage in STAGES[2:]:
            results[stage] = StageResult(
                "SKIPPED",
                reason="Rapports non valides.",
            )

        return results

    # Les soumissions dépendent des rapports validés.
    submissions_path = project_root / "data" / "raw" / "submissions.csv"

    try:
        submissions = read_csv(
            submissions_path,
            (
                "submission_id",
                "report_id",
                "revision_no",
                "previous_submission_id",
                "submitted_at",
                "status",
            ),
        )
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        results["submissions"] = StageResult(
            "FAIL",
            issues=(
                ValidationIssue(
                    0,
                    "",
                    "SUBMISSION_READ_ERROR",
                    f"submissions.csv : {error}",
                ),
            ),
        )
    else:
        report_ids = {row["report_id"] for row in reports}
        submission_issues = validate_submissions(
            submissions,
            report_ids,
        )

        if submission_issues:
            results["submissions"] = StageResult(
                "FAIL",
                issues=tuple(submission_issues),
            )
        else:
            results["submissions"] = StageResult("PASS")

    if results["submissions"].status == "FAIL":
        for stage in STAGES[3:]:
            results[stage] = StageResult(
                "SKIPPED",
                reason="Soumissions non valides.",
            )

        return results

    # Contrôler les liens uniquement après validation des soumissions.
    revision_issues = validate_revision_chains(submissions)

    if revision_issues:
        results["revision_chains"] = StageResult(
            "FAIL",
            issues=tuple(revision_issues),
        )
        results["observations"] = StageResult(
            "SKIPPED",
            reason="Chaînes de révision non valides.",
        )
        return results

    results["revision_chains"] = StageResult("PASS")

    # Les observations dépendent de toutes les étapes précédentes.
    observations_path = project_root / "data" / "raw" / "observations.csv"

    try:
        observations = read_csv(
            observations_path,
            (
                "observation_id",
                "submission_id",
                "area_code",
                "activity_code",
                "indicator_code",
                "reported_value",
            ),
        )
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        results["observations"] = StageResult(
            "FAIL",
            issues=(
                ValidationIssue(
                    0,
                    "",
                    "OBSERVATION_READ_ERROR",
                    f"observations.csv : {error}",
                ),
            ),
        )
    else:
        observation_issues = validate_observations(
            observations,
            {row["submission_id"] for row in submissions},
            {row["area_code"] for row in references["areas"]},
            {row["activity_code"] for row in references["activities"]},
            {row["indicator_code"] for row in references["indicators"]},
            {
                (row["activity_code"], row["indicator_code"])
                for row in references["activity_indicators"]
            },
        )

        if observation_issues:
            results["observations"] = StageResult(
                "FAIL",
                issues=tuple(observation_issues),
            )
        else:
            results["observations"] = StageResult("PASS")

    return results
