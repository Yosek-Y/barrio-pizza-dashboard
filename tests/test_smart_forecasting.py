"""Pruebas del pronóstico adaptativo de la Fase 6.1."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_loader import DataBundle, load_data_bundle
from src.forecasting import build_smart_forecast
from src.validations import validate_data


ROOT = Path(__file__).resolve().parents[1]


def _bundle(values: list[float]) -> DataBundle:
    return DataBundle(
        ingredientes=pd.DataFrame(
            {
                "ingrediente_id": ["producto"],
                "nombre": ["Producto"],
                "proveedor": ["Proveedor"],
                "unidad_base": ["kg"],
                "formato_compra": ["Caja"],
                "unidad_base_por_formato": [10.0],
                "es_perecedero": ["Si"],
            }
        ),
        consumo_historico=pd.DataFrame(
            {
                "sucursal": ["Sucursal A"] * len(values),
                "ingrediente_id": ["producto"] * len(values),
                "semana": [f"S{i}" for i in range(1, len(values) + 1)],
                "consumo_unidad_base": values,
            }
        ),
        inventario_actual=pd.DataFrame(
            columns=["sucursal", "ingrediente_id", "stock_actual_unidad_base"]
        ),
        orden_compra=pd.DataFrame(
            columns=["sucursal", "ingrediente_id", "cantidad_formatos"]
        ),
    )


def test_smart_forecast_ignores_single_extreme_outlier() -> None:
    result = build_smart_forecast(_bundle([28, 30, 150, 27, 29, 31]))
    row = result.projections.iloc[0]

    assert row["consumo_proyectado_base"] == 49.17
    assert row["consumo_proyectado"] == 29.0
    assert row["outliers_detectados"] == 1
    assert row["metodo_proyeccion"] == "Promedio robusto · atípicos excluidos"


def test_smart_forecast_detects_clear_growth_trend() -> None:
    result = build_smart_forecast(_bundle([240, 255, 268, 284, 300, 316]))
    row = result.projections.iloc[0]

    assert row["metodo_proyeccion"] == "Tendencia lineal"
    assert row["outliers_detectados"] == 0
    assert row["r2_tendencia"] >= 0.99
    assert 329.0 <= row["consumo_proyectado"] <= 331.0
    assert row["consumo_proyectado"] > row["consumo_proyectado_base"]


def test_smart_forecast_keeps_mean_when_history_is_stable() -> None:
    result = build_smart_forecast(_bundle([30, 31, 29, 30, 32, 30]))
    row = result.projections.iloc[0]

    assert row["metodo_proyeccion"] == "Promedio estable"
    assert row["outliers_detectados"] == 0
    assert row["consumo_proyectado"] == row["consumo_proyectado_base"]


def test_official_data_exposes_the_two_intelligent_cases() -> None:
    report = validate_data(load_data_bundle(ROOT / "datos"))
    result = build_smart_forecast(report.cleaned_data)

    changed = result.projections.loc[
        ~result.projections["metodo_proyeccion"].eq("Promedio estable"),
        ["sucursal", "ingrediente_id", "metodo_proyeccion"],
    ]

    assert len(changed) == 2
    cases = {
        (row.sucursal, row.ingrediente_id): row.metodo_proyeccion
        for row in changed.itertuples(index=False)
    }
    assert cases[("Marbella", "pepperoni")] == "Promedio robusto · atípicos excluidos"
    assert cases[("Costa del Este", "harina")] == "Tendencia lineal"
