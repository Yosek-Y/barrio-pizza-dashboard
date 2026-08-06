"""Comprueba que el entorno local esté preparado para ejecutar el proyecto."""

from __future__ import annotations

import importlib
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "datos"
REQUIRED_DATA_FILES = (
    "ingredientes.csv",
    "consumo_historico.csv",
    "inventario_actual.csv",
    "orden_compra_semana.csv",
)
REQUIRED_PACKAGES = ("streamlit", "pandas", "numpy", "plotly", "pytest")


def show_status(ok: bool, message: str) -> None:
    """Imprime un resultado fácil de reconocer en la terminal."""
    symbol = "OK" if ok else "FALTA"
    print(f"[{symbol}] {message}")


def main() -> int:
    """Ejecuta todas las comprobaciones y devuelve un código de salida."""
    print("\n=== Verificación del entorno de Barrio Pizza ===\n")

    python_ok = sys.version_info >= (3, 11)
    show_status(
        python_ok,
        f"Python {sys.version.split()[0]} "
        f"({'compatible' if python_ok else 'se requiere Python 3.11 o superior'})",
    )

    packages_ok = True
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package)
            installed_version = version(package)
            show_status(True, f"{package} {installed_version}")
        except (ImportError, PackageNotFoundError):
            packages_ok = False
            show_status(False, f"{package} no está instalado")

    data_ok = True
    for filename in REQUIRED_DATA_FILES:
        exists = (DATA_DIR / filename).exists()
        data_ok &= exists
        show_status(exists, f"datos/{filename}")

    print()
    if python_ok and packages_ok and data_ok:
        print("Todo está listo. Ejecuta: python -m streamlit run app.py")
        return 0

    if not packages_ok:
        print("Instala las dependencias con: python -m pip install -r requirements.txt")
    if not data_ok:
        print("Descarga los datos con: python scripts/download_data.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
