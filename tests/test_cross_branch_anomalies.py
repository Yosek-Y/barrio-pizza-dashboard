"""Pruebas de detección de órdenes atípicas entre sucursales (Fase 6.3)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.anomaly_detection import detect_cross_branch_anomalies
from src.data_loader import load_data_bundle
from src.forecasting import build_smart_forecast
from src.order_workspace import with_order
from src.purchase_analysis import analyze_orders
from src.validations import validate_data


ROOT = Path(__file__).resolve().parents[1]


def _analysis_from_coverages(coverages: list[float]) -> pd.DataFrame:
    branches = ["A", "B", "C", "D"]
    projected = 100.0
    inventory = 20.0
    requested = [(coverage * projected) - inventory for coverage in coverages]
    return pd.DataFrame(
        {
            "sucursal": branches,
            "ingrediente_id": ["producto"] * 4,
            "nombre": ["Producto"] * 4,
            "proveedor": ["Proveedor"] * 4,
            "unidad_base": ["kg"] * 4,
            "es_perecedero": ["Si"] * 4,
            "consumo_proyectado": [projected] * 4,
            "inventario_actual": [inventory] * 4,
            "cantidad_solicitada_unidad_base": requested,
            "formatos_solicitados": [1, 1, 1, 1],
            "formatos_recomendados": [1, 1, 1, 1],
            "estado": ["CORRECTO"] * 4,
            "prioridad": ["OK"] * 4,
        }
    )


def test_detects_unusually_high_post_purchase_coverage() -> None:
    result = detect_cross_branch_anomalies(_analysis_from_coverages([1.0, 1.05, 0.95, 3.0]))
    assert result.anomaly_count == 1
    row = result.anomalies.iloc[0]
    assert row["sucursal"] == "D"
    assert row["tipo_anomalia"] == "COBERTURA_ALTA"
    assert row["factor_vs_pares"] >= 2.5


def test_detects_unusually_low_post_purchase_coverage() -> None:
    result = detect_cross_branch_anomalies(_analysis_from_coverages([1.0, 1.05, 0.95, 0.2]))
    assert result.anomaly_count == 1
    row = result.anomalies.iloc[0]
    assert row["sucursal"] == "D"
    assert row["tipo_anomalia"] == "COBERTURA_BAJA"
    assert row["factor_vs_pares"] <= 0.25


def test_official_order_exposes_expected_cross_branch_cases() -> None:
    report = validate_data(load_data_bundle(ROOT / "datos"))
    forecast = build_smart_forecast(report.cleaned_data)
    analysis = analyze_orders(report.cleaned_data, forecast).analysis
    result = detect_cross_branch_anomalies(analysis)

    cases = {
        (row.sucursal, row.ingrediente_id): row.tipo_anomalia
        for row in result.anomalies.itertuples(index=False)
    }
    assert result.anomaly_count == 4
    assert cases[("Via Argentina", "albahaca")] == "COBERTURA_ALTA"
    assert cases[("Brisas del Golf", "cebolla")] == "COBERTURA_ALTA"
    assert cases[("Costa del Este", "harina")] == "COBERTURA_BAJA"
    assert cases[("Brisas del Golf", "mozzarella")] == "COBERTURA_BAJA"


def test_corrected_order_removes_cross_branch_anomalies() -> None:
    base = load_data_bundle(ROOT / "datos")
    report = validate_data(base)
    forecast = build_smart_forecast(report.cleaned_data)
    result = analyze_orders(report.cleaned_data, forecast)

    corrected = result.corrected_order()[
        ["sucursal", "ingrediente_id", "formatos_recomendados"]
    ].rename(columns={"formatos_recomendados": "cantidad_formatos"})

    corrected_report = validate_data(with_order(base, corrected))
    corrected_forecast = build_smart_forecast(corrected_report.cleaned_data)
    corrected_analysis = analyze_orders(
        corrected_report.cleaned_data, corrected_forecast
    ).analysis

    anomalies = detect_cross_branch_anomalies(corrected_analysis)
    assert anomalies.anomaly_count == 0
