"""Sérialisation et écriture contrôlée des résultats consolidés en CSV."""

import csv
import os
from collections.abc import Sequence
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from .consolidation import ConsolidatedResult

CSV_COLUMNS = (
    "reporting_period",
    "area_code",
    "activity_code",
    "indicator_code",
    "total_value",
)

FORMULA_PREFIXES = ("=", "+", "-", "@", "＝", "＋", "－", "＠")


def _validate_text_cell(field_name: str, value: str) -> None:
    """Refuse les valeurs pouvant être dangereuses dans un tableur."""

    if any(character in value for character in ("\x00", "\t", "\r", "\n")):
        raise ValueError(f"Caractère de contrôle interdit dans {field_name}.")

    if ";" in value:
        raise ValueError(f"Point-virgule interdit dans {field_name}.")

    if value.lstrip().startswith(FORMULA_PREFIXES):
        raise ValueError(f"Préfixe de formule interdit dans {field_name}.")


def render_consolidated_csv(
    results: Sequence[ConsolidatedResult],
) -> str:
    """Produit un CSV stable en mémoire, sans accéder au disque."""

    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)

    ordered_results = sorted(
        results,
        key=lambda row: (
            row.reporting_period,
            row.area_code,
            row.activity_code,
            row.indicator_code,
            row.total_value,
        ),
    )

    for row in ordered_results:
        text_cells = (
            row.reporting_period,
            row.area_code,
            row.activity_code,
            row.indicator_code,
        )

        for field_name, value in zip(CSV_COLUMNS[:4], text_cells, strict=True):
            _validate_text_cell(field_name, value)

        if row.total_value < 0:
            raise ValueError("Total négatif interdit dans l'export.")

        writer.writerow((*text_cells, row.total_value))

    return output.getvalue()


def write_consolidated_csv(
    project_root: Path,
    output_path: Path,
    results: Sequence[ConsolidatedResult],
) -> Path:
    """Publie un CSV complet sans écraser un fichier existant."""

    normalized_data = Path(os.path.abspath(project_root / "data"))
    normalized_output = Path(os.path.abspath(output_path))

    real_data = (project_root / "data").resolve()
    real_output = output_path.resolve()

    if normalized_output.is_relative_to(normalized_data) or real_output.is_relative_to(
        real_data
    ):
        raise ValueError("Export refusé : destination située dans les données sources.")

    if not output_path.parent.is_dir():
        raise FileNotFoundError(
            f"Dossier de sortie absent ou invalide : {output_path.parent}"
        )

    payload = render_consolidated_csv(results).encode("utf-8")

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=output_path.parent,
            prefix=".cpim-export-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        assert temporary_path is not None

        try:
            os.link(
                temporary_path,
                output_path,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise FileExistsError(
                f"Destination déjà existante : {output_path}"
            ) from error

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return output_path
