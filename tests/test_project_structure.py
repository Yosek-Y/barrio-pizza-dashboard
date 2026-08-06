"""Pruebas mínimas de la estructura del proyecto."""

from pathlib import Path


def test_required_project_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    required = (
        "app.py",
        "README.md",
        "ROADMAP.md",
        "requirements.txt",
        "scripts/download_data.py",
        "scripts/check_setup.py",
        "SETUP_WINDOWS.md",
        "src/data_loader.py",
        "src/validations.py",
        "tests/test_data_validation.py",
    )

    missing = [item for item in required if not (root / item).exists()]
    assert not missing, f"Faltan archivos obligatorios: {missing}"
