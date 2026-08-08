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
        "src/order_workspace.py",
        "src/anomaly_detection.py",
        "src/data_chat.py",
        "src/redistribution.py",
        "assets/Anomalias_barrio.jpg",
        "assets/pizzia_icon.png",
        "tests/test_data_validation.py",
        "tests/test_forecasting.py",
        "tests/test_purchase_analysis.py",
        "tests/test_integration_official_data.py",
        "tests/test_order_workspace.py",
        "tests/test_cross_branch_anomalies.py",
        "tests/test_data_chat.py",
        "tests/test_redistribution.py",
    )

    missing = [item for item in required if not (root / item).exists()]
    assert not missing, f"Faltan archivos obligatorios: {missing}"
