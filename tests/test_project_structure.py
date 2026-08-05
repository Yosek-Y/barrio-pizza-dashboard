"""Pruebas mínimas de la estructura inicial."""

from pathlib import Path


def test_required_project_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    required = (
        "app.py",
        "README.md",
        "ROADMAP.md",
        "requirements.txt",
        "scripts/download_data.py",
        "src/data_loader.py",
    )

    missing = [item for item in required if not (root / item).exists()]
    assert not missing, f"Faltan archivos obligatorios: {missing}"
