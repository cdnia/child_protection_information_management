"""Validation des rapports logiques des partenaires."""

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Décrit une anomalie détectée dans un enregistrement."""

    record_number: int
    field: str
    code: str
    message: str


def is_valid_period(value: str) -> bool:
    """Vérifie qu'une période respecte le format YYYY-MM."""

    if re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) is None:
        return False

    try:
        date.fromisoformat(f"{value}-01")
    except ValueError:
        return False

    return True


def validate_reports(
    reports: list[dict[str, str]],
    partner_ids: set[str],
) -> list[ValidationIssue]:
    """Vérifie les règles métier des rapports logiques."""

    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    seen_partner_periods: set[tuple[str, str]] = set()

    for record_number, report in enumerate(reports, start=1):
        report_id = report["report_id"]
        partner_id = report["partner_id"]
        period = report["reporting_period"]

        if not report_id.strip():
            issues.append(
                ValidationIssue(
                    record_number,
                    "report_id",
                    "MISSING_REPORT_ID",
                    "Identifiant de rapport manquant.",
                )
            )
        elif report_id in seen_ids:
            issues.append(
                ValidationIssue(
                    record_number,
                    "report_id",
                    "DUPLICATE_REPORT_ID",
                    f"Identifiant déjà utilisé : {report_id}.",
                )
            )
        else:
            seen_ids.add(report_id)

        if not partner_id.strip():
            issues.append(
                ValidationIssue(
                    record_number,
                    "partner_id",
                    "MISSING_PARTNER_ID",
                    "Identifiant de partenaire manquant.",
                )
            )
        elif partner_id not in partner_ids:
            issues.append(
                ValidationIssue(
                    record_number,
                    "partner_id",
                    "UNKNOWN_PARTNER",
                    f"Partenaire inconnu : {partner_id}.",
                )
            )

        period_valid = is_valid_period(period)

        if not period_valid:
            issues.append(
                ValidationIssue(
                    record_number,
                    "reporting_period",
                    "INVALID_PERIOD",
                    f"Période invalide : {period!r}.",
                )
            )

        if partner_id.strip() and period_valid:
            key = (partner_id, period)

            if key in seen_partner_periods:
                issues.append(
                    ValidationIssue(
                        record_number,
                        "reporting_period",
                        "DUPLICATE_PARTNER_PERIOD",
                        "Un rapport existe déjà pour ce partenaire et cette période.",
                    )
                )
            else:
                seen_partner_periods.add(key)

    return issues
