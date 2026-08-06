"""Carga centralizada de los archivos CSV del reto de Barrio Pizza."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "datos"

DATASET_FILES = {
    "ingredientes": "ingredientes.csv",
    "consumo_historico": "consumo_historico.csv",
    "inventario_actual": "inventario_actual.csv",
    "orden_compra": "orden_compra_semana.csv",
}


@dataclass(frozen=True)
class DataBundle:
    """Agrupa los cuatro conjuntos de datos usados por la aplicación."""

    ingredientes: pd.DataFrame
    consumo_historico: pd.DataFrame
    inventario_actual: pd.DataFrame
    orden_compra: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        """Devuelve los datasets con nombres estables para recorrerlos."""
        return {
            "ingredientes": self.ingredientes,
            "consumo_historico": self.consumo_historico,
            "inventario_actual": self.inventario_actual,
            "orden_compra": self.orden_compra,
        }

    @property
    def total_rows(self) -> int:
        """Cantidad total de registros cargados entre todos los archivos."""
        return sum(len(frame) for frame in self.as_dict().values())


def _normalize_text(frame: pd.DataFrame) -> pd.DataFrame:
    """Limpia espacios accidentales sin modificar el significado de los datos."""
    normalized = frame.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]

    for column in normalized.select_dtypes(include=["string", "object"]).columns:
        normalized[column] = normalized[column].astype("string").str.strip()
        normalized[column] = normalized[column].replace("", pd.NA)

    return normalized


def read_csv(filename: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Lee un CSV como texto para validar antes de convertir valores numéricos."""
    path = data_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró '{filename}' en '{data_dir}'. "
            "Ejecuta: python scripts/download_data.py"
        )

    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", dtype="string")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"No se pudo leer correctamente '{filename}': {exc}") from exc

    return _normalize_text(frame)


def load_data_bundle(data_dir: Path = DATA_DIR) -> DataBundle:
    """Carga los cuatro archivos obligatorios y devuelve un paquete de datos."""
    loaded = {
        dataset: read_csv(filename, data_dir)
        for dataset, filename in DATASET_FILES.items()
    }
    return DataBundle(**loaded)
