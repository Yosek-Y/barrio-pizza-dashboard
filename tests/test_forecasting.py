"""Pruebas de la proyección base implementada en la Fase 2."""

from __future__ import annotations

import pandas as pd

from src.data_loader import DataBundle
from src.forecasting import build_baseline_forecast, get_history_with_projection


def _bundle(history_rows: list[dict[str, object]]) -> DataBundle:
    return DataBundle(
        ingredientes=pd.DataFrame(
            {
                "ingrediente_id": ["harina", "mozzarella"],
                "nombre": ["Harina 00", "Mozzarella"],
                "proveedor": ["Molinos", "Distribuidora"],
                "unidad_base": ["kg", "kg"],
                "formato_compra": ["Saco 25 kg", "Caja 10 kg"],
                "unidad_base_por_formato": [25.0, 10.0],
                "es_perecedero": ["No", "Si"],
            }
        ),
        consumo_historico=pd.DataFrame(history_rows),
        inventario_actual=pd.DataFrame(
            columns=["sucursal", "ingrediente_id", "stock_actual_unidad_base"]
        ),
        orden_compra=pd.DataFrame(
            columns=["sucursal", "ingrediente_id", "cantidad_formatos"]
        ),
    )


def test_six_week_average_is_used_as_projection() -> None:
    rows = [
        {
            "sucursal": "Sucursal A",
            "ingrediente_id": "harina",
            "semana": f"S{week}",
            "consumo_unidad_base": value,
        }
        for week, value in enumerate([10, 20, 30, 40, 50, 60], start=1)
    ]

    result = build_baseline_forecast(_bundle(rows))
    projection = result.projections.iloc[0]

    assert projection["consumo_proyectado"] == 35.0
    assert projection["consumo_minimo"] == 10.0
    assert projection["consumo_maximo"] == 60.0
    assert projection["semanas_disponibles"] == 6
    assert bool(projection["historico_completo"])


def test_incomplete_history_is_projected_and_marked() -> None:
    rows = [
        {
            "sucursal": "Sucursal A",
            "ingrediente_id": "mozzarella",
            "semana": f"S{week}",
            "consumo_unidad_base": value,
        }
        for week, value in enumerate([20, 30, 40], start=1)
    ]

    result = build_baseline_forecast(_bundle(rows))
    projection = result.projections.iloc[0]

    assert projection["consumo_proyectado"] == 30.0
    assert projection["semanas_disponibles"] == 3
    assert not bool(projection["historico_completo"])
    assert result.incomplete_count == 1


def test_catalog_metadata_is_added_to_projection() -> None:
    rows = [
        {
            "sucursal": "Sucursal A",
            "ingrediente_id": "harina",
            "semana": f"S{week}",
            "consumo_unidad_base": 100,
        }
        for week in range(1, 7)
    ]

    result = build_baseline_forecast(_bundle(rows))
    projection = result.projections.iloc[0]

    assert projection["nombre"] == "Harina 00"
    assert projection["proveedor"] == "Molinos"
    assert projection["unidad_base"] == "kg"
    assert projection["metodo_proyeccion"] == "Promedio simple"


def test_group_without_numeric_observations_is_excluded() -> None:
    rows = [
        {
            "sucursal": "Sucursal A",
            "ingrediente_id": "harina",
            "semana": "S1",
            "consumo_unidad_base": pd.NA,
        }
    ]

    result = build_baseline_forecast(_bundle(rows))

    assert result.projections.empty
    assert result.total_projections == 0


def test_history_chart_contains_s7_projection() -> None:
    rows = [
        {
            "sucursal": "Sucursal A",
            "ingrediente_id": "harina",
            "semana": f"S{week}",
            "consumo_unidad_base": 100 + week,
        }
        for week in range(1, 7)
    ]
    data = _bundle(rows)
    result = build_baseline_forecast(data)

    detail = get_history_with_projection(data, result, "Sucursal A", "harina")

    assert len(detail) == 7
    assert detail.iloc[-1]["semana"] == "S7 (proyección)"
    assert detail.iloc[-1]["tipo"] == "Proyección"
