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
