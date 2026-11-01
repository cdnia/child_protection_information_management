"""Interface en ligne de commande du projet."""

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from .csv_export import write_consolidated_csv
from .pipeline import STAGES, run_validation
from .workflow import run_consolidation


def _run_validate(project_root: Path) -> int:
    """Valide les données et affiche le résultat de chaque étape."""

    results = run_validation(project_root)

    for stage in STAGES:
        result = results[stage]
        print(f"{stage}: {result.status}")

        for issue in result.issues:
            details: list[str] = []

            if issue.record_number > 0:
                details.append(f"enregistrement {issue.record_number}")

            if issue.field:
                details.append(f"champ {issue.field}")

            location = f" ({', '.join(details)})" if details else ""

            print(f"  [{issue.code}]{location}: {issue.message}")

        if result.status == "SKIPPED":
            print(f"  Motif : {result.reason}")

    if all(result.status == "PASS" for result in results.values()):
        return 0

    return 1


def _run_consolidate(
    project_root: Path,
    output_path: Path | None = None,
) -> int:
    """Valide et consolide le lot, puis affiche ou exporte les résultats."""

    written_path: Path | None = None

    try:
        results = run_consolidation(project_root)

        if output_path is not None:
            written_path = write_consolidated_csv(
                project_root,
                output_path,
                results,
            )

    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    print(f"Lignes consolidées : {len(results)}")

    if written_path is not None:
        if not results:
            print("Aucun résultat consolidé pour ce lot validé.")

        print(f"Export CSV créé : {written_path}")
        return 0

    if not results:
        print("Aucun résultat consolidé pour ce lot validé.")
        return 0

    print("Période | Zone | Activité | Indicateur | Total")

    for row in results:
        print(
            f"{row.reporting_period} | {row.area_code} | "
            f"{row.activity_code} | {row.indicator_code} | "
            f"{row.total_value}"
        )

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Analyse les arguments et exécute la commande demandée."""

    parser = argparse.ArgumentParser(
        prog="python -m child_protection_information_management",
        description="Validation et consolidation des données synthétiques de reporting.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Vérifier les huit fichiers CSV du projet.",
    )

    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Valider, afficher ou exporter les résultats consolidés.",
    )

    for command_parser in (validate_parser, consolidate_parser):
        command_parser.add_argument(
            "--project-root",
            type=Path,
            default=Path.cwd(),
            metavar="PATH",
            help="Répertoire racine contenant le dossier data.",
        )

    consolidate_parser.add_argument(
        "--output",
        type=Path,
        metavar="PATH",
        help="Créer un fichier CSV sans écraser une destination existante.",
    )

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _run_validate(args.project_root)

    if args.command == "consolidate":
        return _run_consolidate(args.project_root, args.output)

    parser.error(f"Commande inconnue : {args.command}")
