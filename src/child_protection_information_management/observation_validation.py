"""Validation métier des observations déclarées par les partenaires."""

import re

from .validation import ValidationIssue


def validate_observations(
    observations: list[dict[str, str]],
    submission_ids: set[str],
    area_codes: set[str],
    activity_codes: set[str],
    indicator_codes: set[str],
    allowed_pairs: set[tuple[str, str]],
) -> list[ValidationIssue]:
    """Vérifie les identifiants, références et valeurs des observations."""

    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()

    references = (
        (
            "submission_id",
            submission_ids,
            "MISSING_SUBMISSION_ID",
            "UNKNOWN_SUBMISSION",
        ),
        (
            "area_code",
            area_codes,
            "MISSING_AREA_CODE",
            "UNKNOWN_AREA",
        ),
        (
            "activity_code",
            activity_codes,
            "MISSING_ACTIVITY_CODE",
            "UNKNOWN_ACTIVITY",
        ),
        (
            "indicator_code",
            indicator_codes,
            "MISSING_INDICATOR_CODE",
            "UNKNOWN_INDICATOR",
        ),
    )

    for record_number, observation in enumerate(observations, start=1):
        observation_id = observation["observation_id"]

        if not observation_id.strip():
            issues.append(
                ValidationIssue(
                    record_number,
                    "observation_id",
                    "MISSING_OBSERVATION_ID",
                    "Identifiant d'observation manquant.",
                )
            )
        elif observation_id in seen_ids:
            issues.append(
                ValidationIssue(
                    record_number,
                    "observation_id",
                    "DUPLICATE_OBSERVATION_ID",
                    f"Identifiant déjà utilisé : {observation_id}.",
                )
            )
        else:
            seen_ids.add(observation_id)

        for field, known_values, missing_code, unknown_code in references:
            value = observation[field]

            if not value.strip():
                issues.append(
                    ValidationIssue(
                        record_number,
                        field,
                        missing_code,
                        f"Valeur obligatoire manquante : {field}.",
                    )
                )
            elif value not in known_values:
                issues.append(
                    ValidationIssue(
                        record_number,
                        field,
                        unknown_code,
                        f"Référence inconnue : {value}.",
                    )
                )

        activity = observation["activity_code"]
        indicator = observation["indicator_code"]

        if (
            activity in activity_codes
            and indicator in indicator_codes
            and (activity, indicator) not in allowed_pairs
        ):
            issues.append(
                ValidationIssue(
                    record_number,
                    "indicator_code",
                    "UNAUTHORIZED_ACTIVITY_INDICATOR",
                    "Association activité-indicateur non autorisée.",
                )
            )

        key = (
            observation["submission_id"],
            observation["area_code"],
            activity,
            indicator,
        )

        if all(value.strip() for value in key):
            if key in seen_keys:
                issues.append(
                    ValidationIssue(
                        record_number,
                        "observation_id",
                        "DUPLICATE_OBSERVATION_KEY",
                        "Observation déjà déclarée pour cette "
                        "soumission, zone, activité et indicateur.",
                    )
                )
            else:
                seen_keys.add(key)

        reported_value = observation["reported_value"]

        if not reported_value.strip():
            issues.append(
                ValidationIssue(
                    record_number,
                    "reported_value",
                    "MISSING_REPORTED_VALUE",
                    "Valeur déclarée manquante.",
                )
            )
        elif re.fullmatch(r"[0-9]+", reported_value) is None:
            issues.append(
                ValidationIssue(
                    record_number,
                    "reported_value",
                    "INVALID_REPORTED_VALUE",
                    f"Valeur déclarée invalide : {reported_value!r}.",
                )
            )

    return issues
