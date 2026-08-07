"""Pruebas de salidas operativas introducidas en la Fase 4."""

from __future__ import annotations

import pandas as pd

from src.data_loader import DataBundle
from src.forecasting import build_baseline_forecast
from src.purchase_analysis import analyze_orders


def _bundle(
    *,
    projected_consumption: float = 100.0,
    inventory: float = 10.0,
    ordered_formats: float | None = 4.0,
    include_order: bool = True,
    extra_orders: pd.DataFrame | None = None,
) -> DataBundle:
    history = pd.DataFrame(
        {
            "sucursal": ["Sucursal A"] * 6,
            "ingrediente_id": ["harina"] * 6,
            "semana": [f"S{week}" for week in range(1, 7)],
            "consumo_unidad_base": [projected_consumption] * 6,
        }
    )
    orders = pd.DataFrame(columns=["sucursal", "ingrediente_id", "cantidad_formatos"])
    if include_order:
        orders = pd.DataFrame(
            {
                "sucursal": ["Sucursal A"],
                "ingrediente_id": ["harina"],
                "cantidad_formatos": [ordered_formats],
            }
        )
    if extra_orders is not None:
        orders = pd.concat([orders, extra_orders], ignore_index=True)

    return DataBundle(
        ingredientes=pd.DataFrame(
            {
                "ingrediente_id": ["harina"],
                "nombre": ["Harina 00"],
                "proveedor": ["Molinos"],
                "unidad_base": ["kg"],
                "formato_compra": ["Saco 25 kg"],
                "unidad_base_por_formato": [25.0],
                "es_perecedero": ["No"],
            }
        ),
        consumo_historico=history,
        inventario_actual=pd.DataFrame(
            {
                "sucursal": ["Sucursal A"],
                "ingrediente_id": ["harina"],
                "stock_actual_unidad_base": [inventory],
            }
        ),
        orden_compra=orders,
    )


def test_corrected_order_keeps_recommended_lines_only() -> None:
    unknown_order = pd.DataFrame(
        {
            "sucursal": ["Sucursal A"],
            "ingrediente_id": ["aji_chombo"],
            "cantidad_formatos": [3.0],
        }
    )
    data = _bundle(ordered_formats=3.0, extra_orders=unknown_order)
    result = analyze_orders(data, build_baseline_forecast(data))

    corrected = result.corrected_order()

    assert len(corrected) == 1
    row = corrected.iloc[0]
    assert row["nombre"] == "Harina 00"
    assert row["formatos_solicitados"] == 3.0
    assert row["formatos_recomendados"] == 4.0
    assert row["ajuste_formatos"] == 1.0


def test_supplier_summary_aggregates_corrected_output() -> None:
    data = _bundle(ordered_formats=5.0)
    result = analyze_orders(data, build_baseline_forecast(data))

    summary = result.supplier_summary()

    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["proveedor"] == "Molinos"
    assert row["sucursal"] == "Sucursal A"
    assert row["lineas"] == 1
    assert row["formatos_actuales"] == 5.0
    assert row["formatos_recomendados"] == 4.0
    assert row["ajuste_neto_formatos"] == -1.0
    assert row["lineas_con_cambio"] == 1
