"""Interface en ligne de commande du projet."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from .pipeline import STAGES, run_validation


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


def main(argv: Sequence[str] | None = None) -> int:
    """Analyse les arguments et exécute la commande demandée."""

    parser = argparse.ArgumentParser(
        prog="python -m child_protection_information_management",
        description="Validation des données synthétiques de reporting.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Vérifier les huit fichiers CSV du projet.",
    )

    validate_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        metavar="PATH",
        help="Répertoire racine contenant le dossier data.",
    )

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _run_validate(args.project_root)

    parser.error(f"Commande inconnue : {args.command}")
