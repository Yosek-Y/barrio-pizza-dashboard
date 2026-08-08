"""Pronósticos de consumo semanal para Barrio Pizza.

Se conservan dos métodos:
- ``build_baseline_forecast``: promedio simple, útil como referencia auditable.
- ``build_smart_forecast``: método adaptativo que detecta semanas atípicas y
  tendencias claras antes de decidir cómo proyectar la siguiente semana.

El método inteligente está diseñado para historiales cortos (seis semanas), por
lo que evita modelos pesados que podrían sobreajustar los datos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
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

SMART_FORECAST_COLUMNS = FORECAST_COLUMNS + (
    "consumo_proyectado_base",
    "ajuste_vs_promedio",
    "outliers_detectados",
    "tendencia_semanal",
    "r2_tendencia",
    "confianza_proyeccion",
)

SMART_OUTLIER_THRESHOLD = 3.5
SMART_TREND_MIN_R2 = 0.80
SMART_TREND_MIN_RELATIVE_SLOPE = 0.03


@dataclass(frozen=True)
class ForecastResult:
    """Resultado reproducible de la proyección de la semana siguiente."""

    projections: pd.DataFrame

    @property
    def total_projections(self) -> int:
        return len(self.projections)

    @property
    def incomplete_count(self) -> int:
        if self.projections.empty or "historico_completo" not in self.projections:
            return 0
        return int((~self.projections["historico_completo"]).sum())

    @property
    def branch_count(self) -> int:
        if self.projections.empty:
            return 0
        return int(self.projections["sucursal"].nunique())

    @property
    def ingredient_count(self) -> int:
        if self.projections.empty:
            return 0
        return int(self.projections["ingrediente_id"].nunique())


def _empty_forecast(columns: tuple[str, ...] = FORECAST_COLUMNS) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _validated_history(data: DataBundle) -> pd.DataFrame:
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
    history["numero_semana"] = pd.to_numeric(
        history["semana"].astype("string").str.extract(r"(\d+)", expand=False),
        errors="coerce",
    ).astype("Float64")
    return history


def _catalog_metadata(data: DataBundle) -> pd.DataFrame:
    catalog_columns = [
        column
        for column in ("ingrediente_id", "nombre", "proveedor", "unidad_base")
        if column in data.ingredientes.columns
    ]
    return data.ingredientes[catalog_columns].drop_duplicates("ingrediente_id")


def _finalize_forecast(
    grouped: pd.DataFrame,
    data: DataBundle,
    columns: tuple[str, ...],
) -> ForecastResult:
    if grouped.empty:
        return ForecastResult(_empty_forecast(columns))

    result = grouped.merge(
        _catalog_metadata(data),
        on="ingrediente_id",
        how="left",
        validate="many_to_one",
    )

    numeric_round_columns = (
        "consumo_minimo",
        "consumo_maximo",
        "consumo_promedio",
        "consumo_proyectado",
        "consumo_proyectado_base",
        "ajuste_vs_promedio",
        "tendencia_semanal",
        "r2_tendencia",
    )
    for column in numeric_round_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").astype("Float64").round(2)

    for column in ("semanas_disponibles", "observaciones_validas", "outliers_detectados"):
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")

    result["historico_completo"] = result["historico_completo"].astype(bool)
    result = result.reindex(columns=columns)
    result = result.sort_values(
        ["sucursal", "nombre", "ingrediente_id"],
        na_position="last",
    ).reset_index(drop=True)
    return ForecastResult(result)


def build_baseline_forecast(data: DataBundle) -> ForecastResult:
    """Proyecta la próxima semana mediante el promedio histórico disponible."""
    history = _validated_history(data)

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

    grouped = grouped.loc[grouped["observaciones_validas"] > 0].copy()
    if grouped.empty:
        return ForecastResult(_empty_forecast())

    grouped["consumo_proyectado"] = grouped["consumo_promedio"]
    grouped["historico_completo"] = (
        grouped["semanas_disponibles"].eq(6)
        & grouped["observaciones_validas"].eq(6)
    )
    grouped["metodo_proyeccion"] = "Promedio simple"
    return _finalize_forecast(grouped, data, FORECAST_COLUMNS)


def _modified_z_outlier_mask(values: np.ndarray) -> np.ndarray:
    """Marca outliers usando z-score modificado basado en mediana y MAD.

    Es más estable que media/desviación para historiales pequeños. Si el MAD es
    cero, no se elimina ningún punto: con tan pocas semanas preferimos ser
    conservadores antes que descartar datos por una regla ambigua.
    """
    if len(values) < 4:
        return np.zeros(len(values), dtype=bool)

    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad <= 1e-12:
        return np.zeros(len(values), dtype=bool)

    modified_z = 0.6745 * (values - median) / mad
    mask = np.abs(modified_z) > SMART_OUTLIER_THRESHOLD

    # Nunca permitimos que la regla elimine más de un tercio del histórico.
    if int(mask.sum()) > max(1, len(values) // 3):
        return np.zeros(len(values), dtype=bool)
    return mask


def _linear_trend(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Devuelve pendiente, R² y predicción de la semana siguiente."""
    if len(y) < 4 or len(np.unique(x)) < 2:
        return 0.0, 0.0, float(np.mean(y))

    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual = float(np.sum((y - fitted) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 0.0 if total <= 1e-12 else max(0.0, min(1.0, 1.0 - residual / total))
    next_week = float(np.nanmax(x) + 1.0)
    prediction = float(intercept + slope * next_week)
    return float(slope), r2, max(0.0, prediction)


def _smart_group_projection(group: pd.DataFrame) -> dict[str, object] | None:
    ordered = group.dropna(subset=["consumo_unidad_base"]).copy()
    if ordered.empty:
        return None

    ordered = ordered.sort_values(["numero_semana", "semana"], na_position="last")
    y = ordered["consumo_unidad_base"].astype(float).to_numpy()
    x = ordered["numero_semana"].astype(float).to_numpy()

    valid_week_numbers = np.isfinite(x)
    if not valid_week_numbers.all():
        # Fallback ordenado 1..n si alguna etiqueta semanal no contiene número.
        x = np.arange(1, len(y) + 1, dtype=float)

    baseline = float(np.mean(y))
    outlier_mask = _modified_z_outlier_mask(y)
    clean_x = x[~outlier_mask]
    clean_y = y[~outlier_mask]

    slope, r2, trend_prediction = _linear_trend(clean_x, clean_y)
    reference = max(abs(float(np.median(clean_y))), 1e-9)
    relative_slope = abs(slope) / reference

    if int(outlier_mask.sum()) > 0:
        projected = float(np.mean(clean_y))
        method = "Promedio robusto · atípicos excluidos"
        confidence = "Alta" if len(clean_y) >= 5 else "Media"
    elif (
        len(clean_y) >= 4
        and r2 >= SMART_TREND_MIN_R2
        and relative_slope >= SMART_TREND_MIN_RELATIVE_SLOPE
    ):
        projected = trend_prediction
        method = "Tendencia lineal"
        confidence = "Alta" if len(clean_y) >= 6 and r2 >= 0.90 else "Media"
    else:
        projected = baseline
        method = "Promedio estable"
        confidence = "Alta" if len(clean_y) >= 6 else "Media"

    complete = int(ordered["semana"].nunique()) == 6 and len(y) == 6
    if not complete and confidence == "Alta":
        confidence = "Media"
    if len(y) < 3:
        confidence = "Baja"

    return {
        "sucursal": group["sucursal"].iloc[0],
        "ingrediente_id": group["ingrediente_id"].iloc[0],
        "semanas_disponibles": int(ordered["semana"].nunique()),
        "observaciones_validas": int(len(y)),
        "consumo_minimo": float(np.min(y)),
        "consumo_maximo": float(np.max(y)),
        "consumo_promedio": baseline,
        "consumo_proyectado": projected,
        "historico_completo": complete,
        "metodo_proyeccion": method,
        "consumo_proyectado_base": baseline,
        "ajuste_vs_promedio": projected - baseline,
        "outliers_detectados": int(outlier_mask.sum()),
        "tendencia_semanal": slope,
        "r2_tendencia": r2,
        "confianza_proyeccion": confidence,
    }


def build_smart_forecast(data: DataBundle) -> ForecastResult:
    """Pronóstico adaptativo para historiales cortos.

    Decisión por combinación sucursal–ingrediente:
    1. Detecta semanas atípicas con z-score modificado (mediana + MAD).
    2. Si existe un atípico, proyecta con el promedio del histórico limpio.
    3. Si no hay atípicos y existe una tendencia fuerte (R² >= 0.80 y pendiente
       >= 3% del nivel típico por semana), extrapola una semana con regresión.
    4. En cualquier otro caso conserva el promedio, evitando sobreajuste.

    Se mantiene ``consumo_proyectado_base`` para que la gerente pueda ver cuánto
    cambió la recomendación frente al método simple.
    """
    history = _validated_history(data)
    rows: list[dict[str, object]] = []
    for _, group in history.groupby(["sucursal", "ingrediente_id"], dropna=False):
        projection = _smart_group_projection(group)
        if projection is not None:
            rows.append(projection)

    if not rows:
        return ForecastResult(_empty_forecast(SMART_FORECAST_COLUMNS))

    return _finalize_forecast(pd.DataFrame(rows), data, SMART_FORECAST_COLUMNS)


def get_history_with_projection(
    data: DataBundle,
    forecast: ForecastResult,
    branch: str,
    ingredient_id: str,
) -> pd.DataFrame:
    """Devuelve el histórico y agrega la siguiente semana como proyección."""
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
