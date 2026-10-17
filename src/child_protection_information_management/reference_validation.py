"""Vérification des cinq tables de référence du projet."""

from .validation import ValidationIssue

REFERENCE_SCHEMAS: dict[str, tuple[str, ...]] = {
    "partners": ("partner_id", "partner_name"),
    "areas": ("area_code", "area_name", "area_type"),
    "activities": (
        "activity_code",
        "activity_name",
        "activity_description",
    ),
    "indicators": (
        "indicator_code",
        "indicator_name",
        "indicator_definition",
        "measure_unit",
        "aggregation_method",
    ),
    "activity_indicators": ("activity_code", "indicator_code"),
}

REFERENCE_KEYS: dict[str, tuple[str, ...]] = {
    "partners": ("partner_id",),
    "areas": ("area_code",),
    "activities": ("activity_code",),
    "indicators": ("indicator_code",),
    "activity_indicators": ("activity_code", "indicator_code"),
}

ALLOWED_AREA_TYPES = frozenset({"SIMULATED_ZONE"})
ALLOWED_AGGREGATION_METHODS = frozenset({"SUM"})


def validate_reference_tables(
    tables: dict[str, list[dict[str, str]]],
) -> dict[str, list[ValidationIssue]]:
    """Contrôle les champs requis, clés et liens entre référentiels."""

    issues: dict[str, list[ValidationIssue]] = {name: [] for name in REFERENCE_SCHEMAS}

    for name, columns in REFERENCE_SCHEMAS.items():
        if name not in tables:
            issues[name].append(
                ValidationIssue(
                    0,
                    "",
                    "MISSING_REFERENCE_TABLE",
                    f"Table absente : {name}.",
                )
            )
            continue

        records = tables[name]

        if not records:
            issues[name].append(
                ValidationIssue(
                    0,
                    "",
                    "EMPTY_REFERENCE_TABLE",
                    f"Table vide : {name}.",
                )
            )

        seen: set[tuple[str, ...]] = set()
        key_fields = REFERENCE_KEYS[name]

        for record_number, record in enumerate(records, start=1):
            for column in columns:
                if not record.get(column, "").strip():
                    issues[name].append(
                        ValidationIssue(
                            record_number,
                            column,
                            "MISSING_REFERENCE_VALUE",
                            f"Champ obligatoire vide : {column}.",
                        )
                    )

            if name == "areas":
                area_type = record.get("area_type", "")

                if area_type.strip() and area_type not in ALLOWED_AREA_TYPES:
                    issues[name].append(
                        ValidationIssue(
                            record_number,
                            "area_type",
                            "INVALID_AREA_TYPE",
                            f"Type de zone non autorisé : {area_type}.",
                        )
                    )

            if name == "indicators":
                aggregation_method = record.get("aggregation_method", "")

                if (
                    aggregation_method.strip()
                    and aggregation_method not in ALLOWED_AGGREGATION_METHODS
                ):
                    issues[name].append(
                        ValidationIssue(
                            record_number,
                            "aggregation_method",
                            "INVALID_AGGREGATION_METHOD",
                            (
                                "Méthode d'agrégation non autorisée : "
                                f"{aggregation_method}."
                            ),
                        )
                    )

            key = tuple(record.get(field, "") for field in key_fields)

            if not all(value.strip() for value in key):
                continue

            if key in seen:
                issues[name].append(
                    ValidationIssue(
                        record_number,
                        ", ".join(key_fields),
                        "DUPLICATE_REFERENCE_KEY",
                        f"Clé déjà utilisée : {key}.",
                    )
                )
            else:
                seen.add(key)

    if "activities" in tables and "indicators" in tables:
        activities = {row.get("activity_code", "") for row in tables["activities"]}
        indicators = {row.get("indicator_code", "") for row in tables["indicators"]}

        for record_number, link in enumerate(
            tables.get("activity_indicators", []),
            start=1,
        ):
            activity = link.get("activity_code", "")
            indicator = link.get("indicator_code", "")

            if activity.strip() and activity not in activities:
                issues["activity_indicators"].append(
                    ValidationIssue(
                        record_number,
                        "activity_code",
                        "UNKNOWN_REFERENCE_ACTIVITY",
                        f"Activité inexistante : {activity}.",
                    )
                )

            if indicator.strip() and indicator not in indicators:
                issues["activity_indicators"].append(
                    ValidationIssue(
                        record_number,
                        "indicator_code",
                        "UNKNOWN_REFERENCE_INDICATOR",
                        f"Indicateur inexistant : {indicator}.",
                    )
                )

    return issues
