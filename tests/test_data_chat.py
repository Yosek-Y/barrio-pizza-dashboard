"""Pruebas de PizzIA sin depender de servicios externos."""

from src.anomaly_detection import detect_cross_branch_anomalies
from src.data_chat import answer_locally, build_chat_context, context_to_prompt
from src.data_loader import load_data_bundle
from src.forecasting import build_smart_forecast
from src.purchase_analysis import analyze_orders
from src.validations import validate_data


def _scenario():
    bundle = load_data_bundle()
    report = validate_data(bundle)
    forecast = build_smart_forecast(report.cleaned_data)
    purchase = analyze_orders(report.cleaned_data, forecast)
    anomalies = detect_cross_branch_anomalies(purchase.analysis)
    return forecast, purchase, anomalies


def test_chat_context_is_grounded_in_active_dashboard_data() -> None:
    forecast, purchase, anomalies = _scenario()
    context = build_chat_context(
        purchase.analysis,
        forecast.projections,
        anomalies.anomalies,
        purchase.supplier_summary(),
        active_order_source="Orden original",
    )
    assert context["fuente_orden_activa"] == "Orden original"
    assert context["lineas_con_alerta"]
    assert context["pronosticos"]
    assert context["anomalias"]


def test_chat_context_serializes_as_spanish_json() -> None:
    forecast, purchase, anomalies = _scenario()
    context = build_chat_context(
        purchase.analysis,
        forecast.projections,
        anomalies.anomalies,
        purchase.supplier_summary(),
        active_order_source="Orden original",
    )
    prompt = context_to_prompt(context)
    assert "Brisas del Golf" in prompt
    assert "mozzarella" in prompt.lower()


def test_local_chat_can_identify_branch_with_most_alerts() -> None:
    _, purchase, anomalies = _scenario()
    answer = answer_locally(
        "¿Qué sucursal tiene más alertas?",
        purchase.analysis,
        anomalies.anomalies,
        purchase.supplier_summary(),
    )
    assert answer.mode == "local"
    assert "alerta" in answer.text.lower()
    assert any(branch in answer.text for branch in purchase.analysis["sucursal"].unique())


def test_local_chat_can_explain_specific_ingredient() -> None:
    _, purchase, anomalies = _scenario()
    answer = answer_locally(
        "¿Qué pasa con la mozzarella de Brisas del Golf?",
        purchase.analysis,
        anomalies.anomalies,
        purchase.supplier_summary(),
    )
    text = answer.text.lower()
    assert "brisas del golf" in text
    assert "mozzarella" in text
    assert "omit" in text


def test_local_chat_reports_anomalies() -> None:
    _, purchase, anomalies = _scenario()
    answer = answer_locally(
        "¿Qué anomalías detectaste?",
        purchase.analysis,
        anomalies.anomalies,
        purchase.supplier_summary(),
    )
    assert str(len(anomalies.anomalies)) in answer.text
    assert "anomal" in answer.text.lower()
