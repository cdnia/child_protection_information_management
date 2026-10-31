"""Tests de l'interface en ligne de commande."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from child_protection_information_management.reference_validation import (
    REFERENCE_SCHEMAS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_STAGES = (
    "references",
    "reports",
    "submissions",
    "revision_chains",
    "observations",
)


@pytest.fixture
def dataset_root(tmp_path: Path) -> Path:
    """Copie les huit CSV synthétiques dans un dossier temporaire."""

    reference_destination = tmp_path / "data" / "reference"
    raw_destination = tmp_path / "data" / "raw"

    reference_destination.mkdir(parents=True)
    raw_destination.mkdir(parents=True)

    for table_name in REFERENCE_SCHEMAS:
        filename = f"{table_name}.csv"

        shutil.copyfile(
            PROJECT_ROOT / "data" / "reference" / filename,
            reference_destination / filename,
        )

    for filename in ("reports.csv", "submissions.csv", "observations.csv"):
        shutil.copyfile(
            PROJECT_ROOT / "data" / "raw" / filename,
            raw_destination / filename,
        )

    return tmp_path


def run_cli(
    *arguments: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Exécute le véritable point d'entrée Python de la CLI."""

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "child_protection_information_management",
            *arguments,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_cli_help(tmp_path: Path) -> None:
    """L'aide doit être disponible sans fichier de données."""

    result = run_cli("--help", cwd=tmp_path)

    assert result.returncode == 0
    assert "usage: python -m child_protection_information_management" in result.stdout
    assert "validate" in result.stdout
    assert result.stderr == ""


def test_cli_requires_command() -> None:
    """L'absence de sous-commande doit être signalée."""

    result = run_cli()

    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_cli_rejects_unknown_command() -> None:
    """Une sous-commande inconnue doit être rejetée."""

    result = run_cli("unknown-command")

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_cli_valid_dataset(dataset_root: Path) -> None:
    """Un jeu valide doit réussir les cinq étapes."""

    result = run_cli(
        "validate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 0
    assert result.stderr == ""

    assert result.stdout.splitlines() == [f"{stage}: PASS" for stage in EXPECTED_STAGES]


def test_cli_uses_current_directory(dataset_root: Path) -> None:
    """Sans option, la CLI utilise le répertoire courant."""

    result = run_cli("validate", cwd=dataset_root)

    assert result.returncode == 0
    assert "observations: PASS" in result.stdout


def test_cli_explicit_root_from_another_directory(
    dataset_root: Path,
    tmp_path: Path,
) -> None:
    """Un chemin explicite fonctionne depuis un autre répertoire."""

    external_directory = tmp_path / "external"
    external_directory.mkdir()

    result = run_cli(
        "validate",
        "--project-root",
        str(dataset_root),
        cwd=external_directory,
    )

    assert result.returncode == 0
    assert "references: PASS" in result.stdout
    assert "observations: PASS" in result.stdout


def test_cli_missing_reference_blocks_following_stages(
    dataset_root: Path,
) -> None:
    """Un référentiel absent provoque FAIL puis SKIPPED."""

    path = dataset_root / "data" / "reference" / "partners.csv"
    path.unlink()

    result = run_cli(
        "validate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 1
    assert "references: FAIL" in result.stdout
    assert "[REFERENCE_READ_ERROR]" in result.stdout

    for stage in EXPECTED_STAGES[1:]:
        assert f"{stage}: SKIPPED" in result.stdout

    assert "Motif : Référentiels non valides." in result.stdout


def test_cli_missing_reports_blocks_following_stages(
    dataset_root: Path,
) -> None:
    """Un fichier de rapports absent bloque ses dépendances."""

    path = dataset_root / "data" / "raw" / "reports.csv"
    path.unlink()

    result = run_cli(
        "validate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 1
    assert "references: PASS" in result.stdout
    assert "reports: FAIL" in result.stdout
    assert "[REPORT_READ_ERROR]" in result.stdout

    for stage in EXPECTED_STAGES[2:]:
        assert f"{stage}: SKIPPED" in result.stdout

    assert "Motif : Rapports non valides." in result.stdout


def test_cli_displays_observation_issue_details(
    dataset_root: Path,
) -> None:
    """Les anomalies doivent conserver leur localisation."""

    path = dataset_root / "data" / "raw" / "observations.csv"
    content = path.read_text(encoding="utf-8")

    original = "OBS_001,SUB_001,ZONE_A,"
    replacement = "OBS_001,SUB_UNKNOWN,ZONE_A,"

    assert content.count(original) == 1

    path.write_text(
        content.replace(original, replacement, 1),
        encoding="utf-8",
    )

    result = run_cli(
        "validate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 1

    for stage in EXPECTED_STAGES[:-1]:
        assert f"{stage}: PASS" in result.stdout

    assert "observations: FAIL" in result.stdout
    assert "[UNKNOWN_SUBMISSION]" in result.stdout
    assert "enregistrement 1" in result.stdout
    assert "champ submission_id" in result.stdout


def test_cli_rejects_nonexistent_project_root(
    tmp_path: Path,
) -> None:
    """Une racine inexistante doit produire une validation échouée."""

    missing_root = tmp_path / "missing-project"

    result = run_cli(
        "validate",
        "--project-root",
        str(missing_root),
    )

    assert result.returncode == 1
    assert "references: FAIL" in result.stdout
    assert "[REFERENCE_READ_ERROR]" in result.stdout


def test_cli_does_not_modify_source_csv(
    dataset_root: Path,
) -> None:
    """La validation ne doit modifier aucun fichier de données."""

    paths = sorted((dataset_root / "data").rglob("*.csv"))

    assert len(paths) == 8

    before = {path: path.read_bytes() for path in paths}

    result = run_cli(
        "validate",
        "--project-root",
        str(dataset_root),
    )

    after = {path: path.read_bytes() for path in paths}

    assert result.returncode == 0
    assert after == before


def test_cli_consolidate_help() -> None:
    """La sous-commande présente sa propre aide."""

    result = run_cli("consolidate", "--help")

    assert result.returncode == 0
    assert "consolidate" in result.stdout
    assert "--project-root" in result.stdout
    assert result.stderr == ""


def test_cli_consolidate_valid_dataset(dataset_root: Path) -> None:
    """La CLI restitue les résultats synthétiques attendus."""

    result = run_cli(
        "consolidate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 0
    assert result.stderr == ""

    lines = result.stdout.splitlines()

    assert lines[:2] == [
        "Lignes consolidées : 12",
        "Période | Zone | Activité | Indicateur | Total",
    ]

    rows = [line.split(" | ") for line in lines[2:]]

    assert len(rows) == 12
    assert all(len(row) == 5 for row in rows)
    assert all(row[0] == "2025-03" for row in rows)

    assert rows == sorted(rows, key=lambda row: tuple(row[:4]))

    assert sum(int(row[4]) for row in rows if row[3] == "IND_SESSIONS_HELD") == 28

    assert sum(int(row[4]) for row in rows if row[3] == "IND_PARTICIPATIONS") == 652


def test_cli_consolidate_uses_current_directory(
    dataset_root: Path,
) -> None:
    """La racine par défaut correspond au répertoire courant."""

    result = run_cli("consolidate", cwd=dataset_root)

    assert result.returncode == 0
    assert "Lignes consolidées : 12" in result.stdout
    assert result.stderr == ""


def test_cli_consolidate_explicit_root_from_another_directory(
    dataset_root: Path,
    tmp_path: Path,
) -> None:
    """Une racine explicite fonctionne hors du dossier des données."""

    external_directory = tmp_path / "external"
    external_directory.mkdir()

    result = run_cli(
        "consolidate",
        "--project-root",
        str(dataset_root),
        cwd=external_directory,
    )

    assert result.returncode == 0
    assert "Lignes consolidées : 12" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("relative_path", "original", "replacement", "expected_code"),
    [
        (
            "data/reference/areas.csv",
            "SIMULATED_ZONE",
            "UNKNOWN_TYPE",
            "INVALID_AREA_TYPE",
        ),
        (
            "data/raw/reports.csv",
            "PARTNER_001",
            "PARTNER_UNKNOWN",
            "UNKNOWN_PARTNER",
        ),
        (
            "data/raw/observations.csv",
            "OBS_001,SUB_001,ZONE_A,",
            "OBS_001,SUB_UNKNOWN,ZONE_A,",
            "UNKNOWN_SUBMISSION",
        ),
    ],
)
def test_cli_consolidate_rejects_invalid_data(
    dataset_root: Path,
    relative_path: str,
    original: str,
    replacement: str,
    expected_code: str,
) -> None:
    """La CLI refuse un lot invalide sans produire de résultats."""

    path = dataset_root / relative_path
    content = path.read_text(encoding="utf-8")

    assert original in content

    path.write_text(
        content.replace(original, replacement, 1),
        encoding="utf-8",
    )

    result = run_cli(
        "consolidate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Consolidation refusée" in result.stderr
    assert expected_code in result.stderr


def test_cli_consolidate_missing_observations(
    dataset_root: Path,
) -> None:
    """Un fichier d'observations manquant bloque la consolidation."""

    path = dataset_root / "data" / "raw" / "observations.csv"
    path.unlink()

    result = run_cli(
        "consolidate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "OBSERVATION_READ_ERROR" in result.stderr


def test_cli_consolidate_without_approvals(
    dataset_root: Path,
) -> None:
    """Un lot valide sans approbation ne produit aucun résultat."""

    path = dataset_root / "data" / "raw" / "submissions.csv"
    content = path.read_text(encoding="utf-8")

    assert content.count("APPROVED") == 4

    path.write_text(
        content.replace("APPROVED", "REJECTED"),
        encoding="utf-8",
    )

    result = run_cli(
        "consolidate",
        "--project-root",
        str(dataset_root),
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "Lignes consolidées : 0",
        "Aucun résultat consolidé pour ce lot validé.",
    ]


def test_cli_consolidate_unknown_argument() -> None:
    """Une option inconnue doit être rejetée par argparse."""

    result = run_cli("consolidate", "--unknown-option")

    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_cli_consolidate_nonexistent_project_root(
    tmp_path: Path,
) -> None:
    """Une racine inexistante entraîne un refus explicite."""

    missing_root = tmp_path / "missing-project"

    result = run_cli(
        "consolidate",
        "--project-root",
        str(missing_root),
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "REFERENCE_READ_ERROR" in result.stderr


def test_cli_consolidate_does_not_modify_csv(
    dataset_root: Path,
) -> None:
    """La consolidation ne modifie aucun CSV source."""

    paths = sorted((dataset_root / "data").rglob("*.csv"))

    assert len(paths) == 8

    before = {path: path.read_bytes() for path in paths}

    result = run_cli(
        "consolidate",
        "--project-root",
        str(dataset_root),
    )

    after = {path: path.read_bytes() for path in paths}

    assert result.returncode == 0
    assert after == before


def test_cli_consolidate_output_is_deterministic(
    dataset_root: Path,
) -> None:
    """Deux exécutions sur les mêmes données produisent la même sortie."""

    arguments = (
        "consolidate",
        "--project-root",
        str(dataset_root),
    )

    first = run_cli(*arguments)
    second = run_cli(*arguments)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == ""
