"""Pruebas integrales con los cuatro CSV oficiales del reto de Barrio Pizza."""

from __future__ import annotations

import pytest

from src.data_loader import load_data_bundle
from src.forecasting import build_baseline_forecast
from src.purchase_analysis import analyze_orders
from src.validations import validate_data


@pytest.fixture(scope="module")
def official_analysis():
    data = load_data_bundle()
    report = validate_data(data)
    assert not report.has_errors
    forecast = build_baseline_forecast(report.cleaned_data)
    result = analyze_orders(report.cleaned_data, forecast)
    return report, forecast, result.analysis


def _row(analysis, branch: str, ingredient: str):
    rows = analysis.loc[
        analysis["sucursal"].eq(branch)
        & analysis["ingrediente_id"].eq(ingredient)
    ]
    assert len(rows) == 1, f"Se esperaba una sola fila para {branch} / {ingredient}"
    return rows.iloc[0]


def test_official_files_have_only_the_two_expected_validation_warnings(official_analysis) -> None:
    report, _, _ = official_analysis

    assert not report.errors
    assert {issue.code for issue in report.warnings} == {
        "INGREDIENTE_DESCONOCIDO",
        "LINEA_ORDEN_OMITIDA",
    }


def test_official_status_distribution_is_stable(official_analysis) -> None:
    _, _, analysis = official_analysis

    assert analysis["estado"].value_counts().to_dict() == {
        "CORRECTO": 83,
        "FALTANTE": 2,
        "SOBREPEDIDO": 2,
        "DATO_INVALIDO": 1,
        "OMITIDO": 1,
    }


def test_brisa_mozzarella_is_detected_as_omitted(official_analysis) -> None:
    _, _, analysis = official_analysis
    row = _row(analysis, "Brisas del Golf", "mozzarella")

    assert row["estado"] == "OMITIDO"
    assert row["formatos_solicitados"] == 0
    assert row["formatos_recomendados"] == 18
    assert "agregar 18 formato(s)" in row["mensaje"]


def test_costa_del_este_unknown_aji_chombo_is_preserved(official_analysis) -> None:
    _, _, analysis = official_analysis
    row = _row(analysis, "Costa del Este", "aji_chombo")

    assert row["estado"] == "DATO_INVALIDO"
    assert row["prioridad"] == "CRÍTICA"
    assert "no existe en el catálogo" in row["mensaje"]


def test_known_shortages_and_overorders_are_detected(official_analysis) -> None:
    _, _, analysis = official_analysis

    assert _row(analysis, "Costa del Este", "harina")["estado"] == "FALTANTE"
    assert _row(analysis, "Marbella", "pepperoni")["estado"] == "FALTANTE"
    assert _row(analysis, "Brisas del Golf", "cebolla")["estado"] == "SOBREPEDIDO"
    assert _row(analysis, "Via Argentina", "albahaca")["estado"] == "SOBREPEDIDO"


def test_marbellas_pepperoni_outlier_remains_visible_in_baseline(official_analysis) -> None:
    _, forecast, _ = official_analysis
    row = forecast.projections.loc[
        forecast.projections["sucursal"].eq("Marbella")
        & forecast.projections["ingrediente_id"].eq("pepperoni")
    ].iloc[0]

    assert row["consumo_maximo"] == pytest.approx(150.0)
    assert row["consumo_proyectado"] == pytest.approx(49.17, abs=0.01)
    assert row["metodo_proyeccion"] == "Promedio simple"
