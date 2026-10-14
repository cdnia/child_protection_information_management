"""Fonctions de lecture des fichiers de données."""

import csv
from pathlib import Path


def read_csv(
    path: Path,
    expected_columns: tuple[str, ...],
) -> list[dict[str, str]]:
    """Lit un fichier CSV et vérifie la structure de ses colonnes."""

    records: list[dict[str, str]] = []

    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file, strict=True)
        header = next(reader, None)

        if header != list(expected_columns):
            raise ValueError(
                f"{path}: colonnes inattendues. "
                f"Attendu : {list(expected_columns)} ; "
                f"reçu : {header}"
            )

        for row in reader:
            if len(row) != len(expected_columns):
                raise ValueError(
                    f"{path}: ligne {reader.line_num}, "
                    f"{len(row)} colonnes au lieu de "
                    f"{len(expected_columns)}"
                )

            record = dict(zip(expected_columns, row, strict=True))
            records.append(record)

    return records
