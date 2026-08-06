"""Proyección base del consumo semanal de Barrio Pizza.

La Fase 2 usa un promedio simple como línea base. Es un método deliberadamente
transparente: permite comprobar los cálculos y después comparar métodos más
avanzados sin asumir que lo complejo siempre es mejor.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data_loader import DataBundle

FORECAST_REQUIRED_COLUMNS = {
    "sucursal",
    "ingrediente_id",
    "semana",
    "consumo_unidad_base",
}

FORECAST_COLUMNS = (
    "sucursal",
    "ingrediente_id",
    "nombre",
    "proveedor",
    "unidad_base",
    "semanas_disponibles",
    "observaciones_validas",
    "consumo_minimo",
    "consumo_maximo",
    "consumo_promedio",
    "consumo_proyectado",
    "historico_completo",
    "metodo_proyeccion",
)


@dataclass(frozen=True)
class ForecastResult:
    """Resultado reproducible de la proyección de la semana siguiente."""

    projections: pd.DataFrame

    @property
    def total_projections(self) -> int:
        """Cantidad de combinaciones sucursal–ingrediente proyectadas."""
        return len(self.projections)

    @property
    def incomplete_count(self) -> int:
        """Cantidad de proyecciones calculadas con menos de seis semanas."""
        if self.projections.empty or "historico_completo" not in self.projections:
            return 0
        return int((~self.projections["historico_completo"]).sum())

    @property
    def branch_count(self) -> int:
        """Cantidad de sucursales presentes en el resultado."""
        if self.projections.empty:
            return 0
        return int(self.projections["sucursal"].nunique())

    @property
    def ingredient_count(self) -> int:
        """Cantidad de ingredientes distintos presentes en el resultado."""
        if self.projections.empty:
            return 0
        return int(self.projections["ingrediente_id"].nunique())


def _empty_forecast() -> pd.DataFrame:
    """Crea una tabla vacía con el mismo contrato que una proyección real."""
    return pd.DataFrame(columns=FORECAST_COLUMNS)


def build_baseline_forecast(data: DataBundle) -> ForecastResult:
    """Proyecta la próxima semana mediante el promedio histórico disponible.

    Reglas de esta fase:
    - La unidad no se transforma: consumo y proyección permanecen en unidad base.
    - Se usa el promedio de las observaciones numéricas disponibles.
    - Un histórico incompleto puede proyectarse, pero queda marcado para revisión.
    - Una combinación sin ninguna observación válida no genera una proyección.
    """
    history = data.consumo_historico.copy()
    missing = FORECAST_REQUIRED_COLUMNS.difference(history.columns)
    if missing:
        raise ValueError(
            "No se puede proyectar porque faltan columnas en consumo_historico: "
            f"{', '.join(sorted(missing))}."
        )

    history["consumo_unidad_base"] = pd.to_numeric(
        history["consumo_unidad_base"], errors="coerce"
    ).astype("Float64")

    grouped = (
        history.groupby(["sucursal", "ingrediente_id"], dropna=False)
        .agg(
            semanas_disponibles=("semana", "nunique"),
            observaciones_validas=("consumo_unidad_base", "count"),
            consumo_minimo=("consumo_unidad_base", "min"),
            consumo_maximo=("consumo_unidad_base", "max"),
            consumo_promedio=("consumo_unidad_base", "mean"),
        )
        .reset_index()
    )

    # Sin una observación numérica no existe una base honesta para proyectar.
    grouped = grouped.loc[grouped["observaciones_validas"] > 0].copy()
    if grouped.empty:
        return ForecastResult(_empty_forecast())

    grouped["consumo_proyectado"] = grouped["consumo_promedio"]
    grouped["historico_completo"] = (
        grouped["semanas_disponibles"].eq(6)
        & grouped["observaciones_validas"].eq(6)
    )
    grouped["metodo_proyeccion"] = "Promedio simple"

    catalog_columns = [
        column
        for column in ("ingrediente_id", "nombre", "proveedor", "unidad_base")
        if column in data.ingredientes.columns
    ]
    catalog = data.ingredientes[catalog_columns].drop_duplicates("ingrediente_id")
    result = grouped.merge(catalog, on="ingrediente_id", how="left", validate="many_to_one")

    for column in ("consumo_minimo", "consumo_maximo", "consumo_promedio", "consumo_proyectado"):
        result[column] = result[column].astype("Float64").round(2)

    result["semanas_disponibles"] = result["semanas_disponibles"].astype("Int64")
    result["observaciones_validas"] = result["observaciones_validas"].astype("Int64")
    result["historico_completo"] = result["historico_completo"].astype(bool)

    result = result.reindex(columns=FORECAST_COLUMNS)
    result = result.sort_values(
        ["sucursal", "nombre", "ingrediente_id"],
        na_position="last",
    ).reset_index(drop=True)

    return ForecastResult(result)


def get_history_with_projection(
    data: DataBundle,
    forecast: ForecastResult,
    branch: str,
    ingredient_id: str,
) -> pd.DataFrame:
    """Devuelve S1–S6 y agrega S7 como punto proyectado para una gráfica."""
    history = data.consumo_historico.loc[
        data.consumo_historico["sucursal"].eq(branch)
        & data.consumo_historico["ingrediente_id"].eq(ingredient_id),
        ["semana", "consumo_unidad_base"],
    ].copy()

    history["numero_semana"] = pd.to_numeric(
        history["semana"].astype("string").str.extract(r"(\d+)", expand=False),
        errors="coerce",
    )
    history["consumo_unidad_base"] = pd.to_numeric(
        history["consumo_unidad_base"], errors="coerce"
    )
    history = history.sort_values("numero_semana")
    history["tipo"] = "Histórico"

    projected = forecast.projections.loc[
        forecast.projections["sucursal"].eq(branch)
        & forecast.projections["ingrediente_id"].eq(ingredient_id),
        "consumo_proyectado",
    ]
    if projected.empty:
        return history[["semana", "consumo_unidad_base", "tipo"]].reset_index(drop=True)

    projection_row = pd.DataFrame(
        {
            "semana": ["S7 (proyección)"],
            "consumo_unidad_base": [float(projected.iloc[0])],
            "tipo": ["Proyección"],
        }
    )
    return pd.concat(
        [history[["semana", "consumo_unidad_base", "tipo"]], projection_row],
        ignore_index=True,
    )
