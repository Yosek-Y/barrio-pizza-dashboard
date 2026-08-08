from __future__ import annotations

import pandas as pd

from src.redistribution import optimize_redistribution


def _row(branch: str, *, inventory: float, projected: float, ordered: float, recommended: float, fmt: float, state: str = "CORRECTO") -> dict[str, object]:
    return {
        "sucursal": branch,
        "ingrediente_id": "queso",
        "nombre": "Queso",
        "proveedor": "Proveedor",
        "unidad_base": "kg",
        "formato_compra": "Caja",
        "unidad_base_por_formato": fmt,
        "es_perecedero": "Sí",
        "consumo_proyectado": projected,
        "inventario_actual": inventory,
        "cantidad_solicitada_unidad_base": ordered,
        "cantidad_recomendada_unidad_base": recommended,
        "formatos_solicitados": ordered / fmt,
        "formatos_recomendados": recommended / fmt,
        "estado": state,
    }


def test_redistribution_can_avoid_a_purchase_format() -> None:
    analysis = pd.DataFrame([
        _row("Donante", inventory=2, projected=10, ordered=10, recommended=10, fmt=10),  # 2 kg de redondeo
        _row("Destino", inventory=0, projected=11, ordered=0, recommended=20, fmt=10, state="FALTANTE"),
    ])

    result = optimize_redistribution(analysis)

    assert result.transfer_count == 1
    assert result.formats_avoided == 1
    assert result.receivers.iloc[0]["formatos_adicionales_antes"] == 2
    assert result.receivers.iloc[0]["formatos_adicionales_despues"] == 1
    assert result.transfers.iloc[0]["tipo_origen"] == "REDONDEO_FORMATO"


def test_redistribution_ignores_transfers_that_do_not_reduce_formats() -> None:
    analysis = pd.DataFrame([
        _row("Donante", inventory=1, projected=10, ordered=10, recommended=10, fmt=10),
        _row("Destino", inventory=0, projected=19, ordered=0, recommended=20, fmt=10, state="FALTANTE"),
    ])

    result = optimize_redistribution(analysis)

    assert result.transfers.empty
    assert result.formats_avoided == 0


def test_reassignment_of_overordered_formats_is_high_viability() -> None:
    analysis = pd.DataFrame([
        _row("Donante", inventory=0, projected=10, ordered=30, recommended=10, fmt=10, state="SOBREPEDIDO"),
        _row("Destino", inventory=0, projected=20, ordered=0, recommended=20, fmt=10, state="OMITIDO"),
    ])

    result = optimize_redistribution(analysis)

    assert result.formats_avoided == 2
    assert set(result.transfers["tipo_origen"]) == {"REASIGNAR_PEDIDO"}
    assert set(result.transfers["viabilidad"]) == {"ALTA"}


def test_no_cross_ingredient_transfer() -> None:
    donor = _row("Donante", inventory=0, projected=10, ordered=30, recommended=10, fmt=10, state="SOBREPEDIDO")
    receiver = _row("Destino", inventory=0, projected=20, ordered=0, recommended=20, fmt=10, state="OMITIDO")
    receiver["ingrediente_id"] = "harina"
    receiver["nombre"] = "Harina"

    result = optimize_redistribution(pd.DataFrame([donor, receiver]))

    assert result.transfers.empty


def test_official_data_finds_network_savings() -> None:
    from src.data_loader import load_data_bundle
    from src.forecasting import build_smart_forecast
    from src.purchase_analysis import analyze_orders
    from src.validations import validate_data

    report = validate_data(load_data_bundle())
    forecast = build_smart_forecast(report.cleaned_data)
    purchase = analyze_orders(report.cleaned_data, forecast)
    result = optimize_redistribution(purchase.analysis)

    assert result.formats_avoided == 3
    assert result.product_count == 2
    assert result.benefited_branch_count == 2
    assert {"harina", "mozzarella"}.issubset(set(result.receivers["ingrediente_id"]))
