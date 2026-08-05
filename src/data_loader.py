"""Carga de los archivos CSV del reto."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "datos"


def read_csv(filename: str) -> pd.DataFrame:
    """Lee un CSV de la carpeta de datos usando UTF-8 con BOM."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Ejecuta: python scripts/download_data.py"
        )
    return pd.read_csv(path, encoding="utf-8-sig")
