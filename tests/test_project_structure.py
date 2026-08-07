"""Pruebas mínimas de la estructura del proyecto."""

from pathlib import Path


def test_required_project_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    required = (
        "app.py",
        "README.md",
        "requirements.txt",
        "scripts/download_data.py",
        "scripts/check_setup.py",
        "scripts/run_quality_checks.py",
        "src/data_loader.py",
        "src/validations.py",
        "src/forecasting.py",
        "src/purchase_analysis.py",
        "tests/test_data_validation.py",
        "tests/test_forecasting.py",
        "tests/test_purchase_analysis.py",
        "tests/test_integration_official_data.py",
    )

    missing = [item for item in required if not (root / item).exists()]
    assert not missing, f"Faltan archivos obligatorios: {missing}"
