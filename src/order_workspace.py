"""Herramientas para cargar, editar y reemplazar la orden semanal activa."""

from __future__ import annotations

import pandas as pd

from src.data_loader import DataBundle

ORDER_COLUMNS = ("sucursal", "ingrediente_id", "cantidad_formatos")


def missing_order_columns(frame: pd.DataFrame) -> tuple[str, ...]:
    """Devuelve columnas obligatorias faltantes en una orden cargada."""
    normalized_columns = {str(column).strip() for column in frame.columns}
    return tuple(column for column in ORDER_COLUMNS if column not in normalized_columns)


def normalize_order_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normaliza una orden y conserva únicamente las columnas que consume el motor.

    Las filas completamente vacías se descartan. Los valores de texto se limpian,
    pero la conversión numérica queda en manos del validador central para que los
    errores sigan apareciendo como hallazgos del dashboard.
    """
    normalized = frame.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]

    missing = missing_order_columns(normalized)
    if missing:
        raise ValueError(
            "Faltan columnas obligatorias en la orden: " + ", ".join(missing)
        )

    normalized = normalized.loc[:, list(ORDER_COLUMNS)].copy()

    for column in ("sucursal", "ingrediente_id"):
        normalized[column] = normalized[column].astype("string").str.strip()
        normalized[column] = normalized[column].replace("", pd.NA)

    # El editor puede entregar números o texto. Conservamos el dato y dejamos que
    # validate_data aplique las reglas oficiales de cantidad, negativos y enteros.
    quantity = normalized["cantidad_formatos"]
    if pd.api.types.is_string_dtype(quantity) or quantity.dtype == object:
        quantity = quantity.astype("string").str.strip().replace("", pd.NA)
    normalized["cantidad_formatos"] = quantity

    empty_row = normalized[list(ORDER_COLUMNS)].isna().all(axis=1)
    normalized = normalized.loc[~empty_row].reset_index(drop=True)
    return normalized


def with_order(base: DataBundle, order: pd.DataFrame) -> DataBundle:
    """Crea un paquete de datos igual al original, sustituyendo solo la orden."""
    return DataBundle(
        ingredientes=base.ingredientes.copy(),
        consumo_historico=base.consumo_historico.copy(),
        inventario_actual=base.inventario_actual.copy(),
        orden_compra=normalize_order_frame(order),
    )


def editor_frame(order: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    """Agrega el nombre del ingrediente para que la edición sea más amigable."""
    normalized = normalize_order_frame(order)
    names = catalog[["ingrediente_id", "nombre"]].drop_duplicates("ingrediente_id")
    result = normalized.merge(names, on="ingrediente_id", how="left")
    return result[["sucursal", "ingrediente_id", "nombre", "cantidad_formatos"]]
