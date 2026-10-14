"""Validation des informations de base des soumissions."""

import re
from datetime import datetime

from .validation import ValidationIssue

ALLOWED_STATUSES = frozenset({"RECEIVED", "UNDER_REVIEW", "APPROVED", "REJECTED"})


def is_valid_utc_timestamp(value: str) -> bool:
    """Vérifie une date au format YYYY-MM-DDTHH:MM:SSZ."""

    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"

    if re.fullmatch(pattern, value) is None:
        return False

    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False

    return True


def validate_submissions(
    submissions: list[dict[str, str]],
    report_ids: set[str],
) -> list[ValidationIssue]:
    """Vérifie les identifiants, dates, révisions et statuts."""

    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    seen_revisions: set[tuple[str, int]] = set()

    for record_number, submission in enumerate(submissions, start=1):
        submission_id = submission["submission_id"]
        report_id = submission["report_id"]
        revision_no = submission["revision_no"]
        submitted_at = submission["submitted_at"]
        status = submission["status"]

        if not submission_id.strip():
            issues.append(
                ValidationIssue(
                    record_number,
                    "submission_id",
                    "MISSING_SUBMISSION_ID",
                    "Identifiant de soumission manquant.",
                )
            )
        elif submission_id in seen_ids:
            issues.append(
                ValidationIssue(
                    record_number,
                    "submission_id",
                    "DUPLICATE_SUBMISSION_ID",
                    f"Identifiant déjà utilisé : {submission_id}.",
                )
            )
        else:
            seen_ids.add(submission_id)

        if not report_id.strip():
            issues.append(
                ValidationIssue(
                    record_number,
                    "report_id",
                    "MISSING_REPORT_ID",
                    "Identifiant de rapport manquant.",
                )
            )
        elif report_id not in report_ids:
            issues.append(
                ValidationIssue(
                    record_number,
                    "report_id",
                    "UNKNOWN_REPORT",
                    f"Rapport inconnu : {report_id}.",
                )
            )

        if re.fullmatch(r"[1-9][0-9]*", revision_no) is None:
            issues.append(
                ValidationIssue(
                    record_number,
                    "revision_no",
                    "INVALID_REVISION_NO",
                    f"Numéro de révision invalide : {revision_no!r}.",
                )
            )
        elif report_id.strip():
            key = (report_id, int(revision_no))

            if key in seen_revisions:
                issues.append(
                    ValidationIssue(
                        record_number,
                        "revision_no",
                        "DUPLICATE_REPORT_REVISION",
                        "Numéro de révision déjà utilisé pour ce rapport.",
                    )
                )
            else:
                seen_revisions.add(key)

        if not is_valid_utc_timestamp(submitted_at):
            issues.append(
                ValidationIssue(
                    record_number,
                    "submitted_at",
                    "INVALID_SUBMISSION_DATE",
                    f"Date de transmission invalide : {submitted_at!r}.",
                )
            )

        if status not in ALLOWED_STATUSES:
            issues.append(
                ValidationIssue(
                    record_number,
                    "status",
                    "INVALID_STATUS",
                    f"Statut inconnu : {status!r}.",
                )
            )

    return issues


def validate_revision_chains(
    submissions: list[dict[str, str]],
) -> list[ValidationIssue]:
    """Vérifie les liens et la chronologie entre les révisions valides."""

    issues: list[ValidationIssue] = []
    by_id = {row["submission_id"]: row for row in submissions}

    for record_number, submission in enumerate(submissions, start=1):
        submission_id = submission["submission_id"]
        revision_text = submission["revision_no"]
        previous_id = submission["previous_submission_id"]

        # Les champs de base doivent être vérifiés auparavant
        # avec validate_submissions().
        if re.fullmatch(r"[1-9][0-9]*", revision_text) is None:
            continue

        revision = int(revision_text)

        if revision == 1:
            if previous_id:
                issues.append(
                    ValidationIssue(
                        record_number,
                        "previous_submission_id",
                        "FIRST_REVISION_HAS_PREVIOUS",
                        f"La première révision {submission_id} "
                        "ne doit pas avoir de précédente.",
                    )
                )
            continue

        if not previous_id:
            issues.append(
                ValidationIssue(
                    record_number,
                    "previous_submission_id",
                    "MISSING_PREVIOUS_SUBMISSION",
                    f"Révision précédente manquante pour {submission_id}.",
                )
            )
            continue

        previous = by_id.get(previous_id)

        if previous is None:
            issues.append(
                ValidationIssue(
                    record_number,
                    "previous_submission_id",
                    "UNKNOWN_PREVIOUS_SUBMISSION",
                    f"Soumission précédente inconnue : {previous_id}.",
                )
            )
            continue

        if previous["report_id"] != submission["report_id"]:
            issues.append(
                ValidationIssue(
                    record_number,
                    "previous_submission_id",
                    "PREVIOUS_SUBMISSION_WRONG_REPORT",
                    f"La soumission {previous_id} appartient à un autre rapport.",
                )
            )

        previous_revision = previous["revision_no"]

        if (
            re.fullmatch(r"[1-9][0-9]*", previous_revision) is not None
            and int(previous_revision) != revision - 1
        ):
            issues.append(
                ValidationIssue(
                    record_number,
                    "revision_no",
                    "NON_CONSECUTIVE_REVISION",
                    f"La révision {revision} ne suit pas "
                    f"la révision {previous_revision}.",
                )
            )

        if is_valid_utc_timestamp(
            submission["submitted_at"]
        ) and is_valid_utc_timestamp(previous["submitted_at"]):
            current_time = datetime.strptime(
                submission["submitted_at"],
                "%Y-%m-%dT%H:%M:%SZ",
            )
            previous_time = datetime.strptime(
                previous["submitted_at"],
                "%Y-%m-%dT%H:%M:%SZ",
            )

            if current_time <= previous_time:
                issues.append(
                    ValidationIssue(
                        record_number,
                        "submitted_at",
                        "NON_CHRONOLOGICAL_REVISION",
                        f"La révision {submission_id} n'est pas "
                        f"postérieure à {previous_id}.",
                    )
                )

    return issues
