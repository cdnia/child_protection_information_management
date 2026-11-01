"""Tests de sérialisation des résultats consolidés en CSV."""

import csv
from io import StringIO
from pathlib import Path

import pytest

from child_protection_information_management.consolidation import (
    ConsolidatedResult,
)
from child_protection_information_management.csv_export import (
    CSV_COLUMNS,
    render_consolidated_csv,
    write_consolidated_csv,
)


def test_empty_results_produce_header_only() -> None:
    """Un résultat vide conserve uniquement l'en-tête."""

    assert render_consolidated_csv([]) == ",".join(CSV_COLUMNS) + "\n"


def test_results_are_sorted() -> None:
    """Les groupes sont exportés dans un ordre déterministe."""

    results = [
        ConsolidatedResult("2025-03", "ZONE_B", "ACT_2", "IND_2", 7),
        ConsolidatedResult("2025-03", "ZONE_A", "ACT_1", "IND_1", 3),
    ]

    assert render_consolidated_csv(results).splitlines() == [
        "reporting_period,area_code,activity_code,indicator_code,total_value",
        "2025-03,ZONE_A,ACT_1,IND_1,3",
        "2025-03,ZONE_B,ACT_2,IND_2,7",
    ]


def test_special_characters_are_quoted() -> None:
    """Le générateur conserve les virgules et guillemets des champs."""

    result = ConsolidatedResult("2025-03", 'ZONE,"A"', "ACT_1", "IND_1", 4)

    content = render_consolidated_csv([result])
    rows = list(csv.reader(StringIO(content, newline="")))

    assert rows[0] == list(CSV_COLUMNS)
    assert rows[1] == [
        "2025-03",
        'ZONE,"A"',
        "ACT_1",
        "IND_1",
        "4",
    ]
    assert "\r" not in content


@pytest.mark.parametrize(
    "area_code",
    ["=1+1", " +SUM(1,1)", "＠DANGEROUS"],
)
def test_formula_prefixes_are_rejected(area_code: str) -> None:
    """Les identifiants pouvant déclencher une formule sont refusés."""

    result = ConsolidatedResult("2025-03", area_code, "ACT_1", "IND_1", 4)

    with pytest.raises(ValueError, match="Préfixe de formule interdit"):
        render_consolidated_csv([result])


@pytest.mark.parametrize("area_code", ["ZONE\nB", "ZONE\tB"])
def test_control_characters_are_rejected(area_code: str) -> None:
    """Les caractères de contrôle ne sont pas exportés."""

    result = ConsolidatedResult("2025-03", area_code, "ACT_1", "IND_1", 4)

    with pytest.raises(ValueError, match="Caractère de contrôle interdit"):
        render_consolidated_csv([result])


def test_input_order_does_not_change_csv() -> None:
    """Inverser les résultats ne modifie pas le contenu CSV."""

    results = [
        ConsolidatedResult("2025-03", "ZONE_B", "ACT_2", "IND_2", 7),
        ConsolidatedResult("2025-03", "ZONE_A", "ACT_1", "IND_1", 3),
    ]

    assert render_consolidated_csv(results) == render_consolidated_csv(
        list(reversed(results))
    )


def test_rendering_does_not_mutate_input() -> None:
    """La sérialisation conserve la liste originale."""

    results = [
        ConsolidatedResult("2025-03", "ZONE_B", "ACT_2", "IND_2", 7),
        ConsolidatedResult("2025-03", "ZONE_A", "ACT_1", "IND_1", 3),
    ]
    original = list(results)

    render_consolidated_csv(results)

    assert results == original


def test_write_creates_exact_csv_and_preserves_source(
    tmp_path: Path,
) -> None:
    """Publie les octets attendus sans modifier les données sources."""

    raw_directory = tmp_path / "data" / "raw"
    raw_directory.mkdir(parents=True)

    source = raw_directory / "observations.csv"
    source.write_bytes(b"synthetic,source\n")
    original_source = source.read_bytes()

    output_directory = tmp_path / "exports"
    output_directory.mkdir()
    output_path = output_directory / "consolidated.csv"

    results = [
        ConsolidatedResult("2025-03", "ZONE_A", "ACT_1", "IND_1", 4),
    ]

    written_path = write_consolidated_csv(
        tmp_path,
        output_path,
        results,
    )

    assert written_path == output_path
    assert output_path.read_bytes() == render_consolidated_csv(results).encode("utf-8")
    assert source.read_bytes() == original_source
    assert list(output_directory.glob(".cpim-export-*.tmp")) == []


def test_write_refuses_existing_destination(
    tmp_path: Path,
) -> None:
    """Une destination existante ne doit jamais être écrasée."""

    output_path = tmp_path / "existing.csv"
    output_path.write_bytes(b"EXISTING CONTENT\n")

    with pytest.raises(FileExistsError, match="déjà existante"):
        write_consolidated_csv(tmp_path, output_path, [])

    assert output_path.read_bytes() == b"EXISTING CONTENT\n"
    assert list(tmp_path.glob(".cpim-export-*.tmp")) == []


@pytest.mark.parametrize(
    "relative_path",
    [
        "data/raw/consolidated.csv",
        "exports/../data/raw/consolidated.csv",
    ],
)
def test_write_refuses_source_directory(
    tmp_path: Path,
    relative_path: str,
) -> None:
    """Un export ne doit pas être publié dans data/."""

    raw_directory = tmp_path / "data" / "raw"
    raw_directory.mkdir(parents=True)

    output_path = tmp_path / relative_path

    with pytest.raises(ValueError, match="données sources"):
        write_consolidated_csv(tmp_path, output_path, [])

    assert list(raw_directory.iterdir()) == []


def test_write_refuses_symlink_into_source_directory(
    tmp_path: Path,
) -> None:
    """Un lien symbolique ne doit pas contourner la protection."""

    raw_directory = tmp_path / "data" / "raw"
    raw_directory.mkdir(parents=True)

    alias = tmp_path / "export_alias"
    alias.symlink_to(raw_directory, target_is_directory=True)

    with pytest.raises(ValueError, match="données sources"):
        write_consolidated_csv(
            tmp_path,
            alias / "consolidated.csv",
            [],
        )

    assert list(raw_directory.iterdir()) == []


def test_write_refuses_existing_destination_symlink(
    tmp_path: Path,
) -> None:
    """Un lien symbolique existant ne doit pas être remplacé."""

    original = tmp_path / "original.csv"
    original.write_bytes(b"ORIGINAL\n")

    alias = tmp_path / "alias.csv"
    alias.symlink_to(original)

    with pytest.raises(FileExistsError, match="déjà existante"):
        write_consolidated_csv(tmp_path, alias, [])

    assert alias.is_symlink()
    assert original.read_bytes() == b"ORIGINAL\n"


def test_write_refuses_missing_parent_directory(
    tmp_path: Path,
) -> None:
    """Le générateur ne crée pas automatiquement de répertoires."""

    output_path = tmp_path / "missing" / "consolidated.csv"

    with pytest.raises(FileNotFoundError, match="Dossier de sortie"):
        write_consolidated_csv(tmp_path, output_path, [])

    assert not output_path.exists()
    assert not output_path.parent.exists()


def test_write_cleans_temporary_file_after_publish_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un échec de publication ne laisse pas de fichier temporaire."""

    def failing_link(*args: object, **kwargs: object) -> None:
        raise PermissionError("simulated publication failure")

    monkeypatch.setattr(
        "child_protection_information_management.csv_export.os.link",
        failing_link,
    )

    output_path = tmp_path / "consolidated.csv"

    with pytest.raises(
        PermissionError,
        match="simulated publication failure",
    ):
        write_consolidated_csv(tmp_path, output_path, [])

    assert not output_path.exists()
    assert list(tmp_path.glob(".cpim-export-*.tmp")) == []


def test_write_empty_results_produces_header_only(
    tmp_path: Path,
) -> None:
    """Aucune approbation ne doit produire de fausses valeurs zéro."""

    output_path = tmp_path / "empty.csv"

    write_consolidated_csv(tmp_path, output_path, [])

    assert output_path.read_bytes() == (",".join(CSV_COLUMNS) + "\n").encode("utf-8")


def test_write_is_byte_identical_for_reordered_results(
    tmp_path: Path,
) -> None:
    """L'ordre initial ne change pas les octets de l'export."""

    results = [
        ConsolidatedResult("2025-03", "ZONE_B", "ACT_2", "IND_2", 7),
        ConsolidatedResult("2025-03", "ZONE_A", "ACT_1", "IND_1", 3),
    ]

    first_output = tmp_path / "first.csv"
    second_output = tmp_path / "second.csv"

    write_consolidated_csv(tmp_path, first_output, results)
    write_consolidated_csv(
        tmp_path,
        second_output,
        list(reversed(results)),
    )

    assert first_output.read_bytes() == second_output.read_bytes()


def test_render_rejects_negative_total() -> None:
    """Un total négatif ne peut pas être exporté."""

    result = ConsolidatedResult("2025-03", "ZONE_A", "ACT_1", "IND_1", -1)

    with pytest.raises(ValueError, match="Total négatif"):
        render_consolidated_csv([result])


def test_render_rejects_null_character() -> None:
    """Un caractère NUL ne doit pas apparaître dans un identifiant."""

    result = ConsolidatedResult("2025-03", "ZONE_A\x00", "ACT_1", "IND_1", 4)

    with pytest.raises(ValueError, match="Caractère de contrôle"):
        render_consolidated_csv([result])


@pytest.mark.parametrize(
    "area_code",
    [
        "ZONE_A;=1+1;",
        "ZONE_A; +SUM(1,1);",
        "ZONE_A;SAFE",
    ],
)
def test_semicolon_in_identifier_is_rejected(area_code: str) -> None:
    """Refuse un séparateur alternatif dans un identifiant exporté."""

    result = ConsolidatedResult("2025-03", area_code, "ACT_1", "IND_1", 4)

    with pytest.raises(ValueError, match="Point-virgule interdit"):
        render_consolidated_csv([result])
