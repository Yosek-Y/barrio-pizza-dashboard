"""Pruebas del motor de necesidad y alertas de la Fase 3."""

from __future__ import annotations

import pandas as pd

from src.data_loader import DataBundle
from src.forecasting import build_baseline_forecast
from src.purchase_analysis import analyze_orders


def _bundle(
    *,
    projected_consumption: float = 100.0,
    inventory: float = 10.0,
    format_size: float = 25.0,
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
                "unidad_base_por_formato": [format_size],
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


def _analyze(data: DataBundle) -> pd.DataFrame:
    forecast = build_baseline_forecast(data)
    return analyze_orders(data, forecast).analysis


def test_normal_rounding_is_correct_not_overorder() -> None:
    # Necesidad: 100 - 10 = 90 kg. Cuatro sacos = 100 kg. Sobran 10 kg,
    # pero es menos que un saco completo de 25 kg y por eso es correcto.
    row = _analyze(_bundle(ordered_formats=4)).iloc[0]

    assert row["necesidad_real"] == 90.0
    assert row["formatos_recomendados"] == 4
    assert row["cantidad_recomendada_unidad_base"] == 100.0
    assert row["excedente_sobre_necesidad"] == 10.0
    assert row["estado"] == "CORRECTO"


def test_order_below_recommended_formats_is_shortage() -> None:
    row = _analyze(_bundle(ordered_formats=3)).iloc[0]

    assert row["estado"] == "FALTANTE"
    assert row["faltante_unidad_base"] == 15.0
    assert row["diferencia_formatos"] == -1.0
    assert "riesgo de quiebre" in row["mensaje"]


def test_one_extra_complete_format_is_overorder() -> None:
    row = _analyze(_bundle(ordered_formats=5)).iloc[0]

    assert row["estado"] == "SOBREPEDIDO"
    assert row["diferencia_formatos"] == 1.0
    assert row["excedente_sobre_recomendacion"] == 25.0
    assert "Reducir 1 formato" in row["accion_recomendada"]


def test_absent_line_with_positive_need_is_omitted() -> None:
    row = _analyze(_bundle(include_order=False)).iloc[0]

    assert not bool(row["orden_presente"])
    assert row["estado"] == "OMITIDO"
    assert row["formatos_recomendados"] == 4
    assert "omitió Harina 00" in row["mensaje"]


def test_no_purchase_needed_and_absent_line_is_correct() -> None:
    row = _analyze(
        _bundle(projected_consumption=50, inventory=60, include_order=False)
    ).iloc[0]

    assert row["necesidad_real"] == 0.0
    assert row["formatos_recomendados"] == 0
    assert row["estado"] == "CORRECTO"
    assert "no se necesita comprar" in row["mensaje"]


def test_exact_multiple_and_extra_format_respect_boundary() -> None:
    correct = _analyze(
        _bundle(projected_consumption=60, inventory=10, ordered_formats=2)
    ).iloc[0]
    over = _analyze(
        _bundle(projected_consumption=60, inventory=10, ordered_formats=3)
    ).iloc[0]

    assert correct["necesidad_real"] == 50.0
    assert correct["estado"] == "CORRECTO"
    assert over["estado"] == "SOBREPEDIDO"
    assert over["excedente_sobre_recomendacion"] == 25.0


def test_fractional_purchase_format_is_invalid() -> None:
    row = _analyze(_bundle(ordered_formats=3.5)).iloc[0]

    assert row["estado"] == "DATO_INVALIDO"
    assert "fracción de formato" in row["mensaje"]


def test_unknown_order_is_preserved_as_invalid_data() -> None:
    unknown_order = pd.DataFrame(
        {
            "sucursal": ["Sucursal A"],
            "ingrediente_id": ["aji_chombo"],
            "cantidad_formatos": [3.0],
        }
    )
    result = _analyze(_bundle(extra_orders=unknown_order))
    unknown = result.loc[result["ingrediente_id"].eq("aji_chombo")].iloc[0]

    assert unknown["estado"] == "DATO_INVALIDO"
    assert unknown["prioridad"] == "CRÍTICA"
    assert "no existe en el catálogo" in unknown["mensaje"]


def test_result_summary_counts_statuses() -> None:
    data = _bundle(ordered_formats=3)
    result = analyze_orders(data, build_baseline_forecast(data))

    assert result.total_rows == 1
    assert result.actionable_count == 1
    assert result.alert_count == 1
    assert result.summary()["FALTANTE"] == 1
