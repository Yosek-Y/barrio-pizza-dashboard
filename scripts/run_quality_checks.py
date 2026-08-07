"""Chequeo integral rápido sobre los CSV oficiales de Barrio Pizza."""

# ruff: noqa: E402, I001

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_data_bundle
from src.forecasting import build_baseline_forecast
from src.purchase_analysis import analyze_orders
from src.validations import validate_data

EXPECTED_WARNINGS = {"INGREDIENTE_DESCONOCIDO", "LINEA_ORDEN_OMITIDA"}
EXPECTED_STATUS_COUNTS = {
    "CORRECTO": 83,
    "FALTANTE": 2,
    "SOBREPEDIDO": 2,
    "DATO_INVALIDO": 1,
    "OMITIDO": 1,
}


def main() -> int:
    data = load_data_bundle()
    report = validate_data(data)

    print("=== Barrio Pizza · chequeo integral ===")
    print(f"Archivos: 4 | Registros: {data.total_rows}")
    print(f"Errores: {len(report.errors)} | Advertencias: {len(report.warnings)}")

    if report.errors:
        for issue in report.errors:
            print(f"[ERROR] {issue.code}: {issue.message}")
        return 1

    warning_codes = {issue.code for issue in report.warnings}
    if warning_codes != EXPECTED_WARNINGS:
        print(f"[FALLO] Advertencias inesperadas: {sorted(warning_codes)}")
        return 1

    forecast = build_baseline_forecast(report.cleaned_data)
    result = analyze_orders(report.cleaned_data, forecast)
    actual_counts = Counter(result.analysis["estado"].tolist())

    print("\nEstados detectados:")
    for status, expected in EXPECTED_STATUS_COUNTS.items():
        actual = actual_counts.get(status, 0)
        marker = "OK" if actual == expected else "FALLO"
        print(f"  [{marker}] {status}: {actual} (esperado {expected})")

    if dict(actual_counts) != EXPECTED_STATUS_COUNTS:
        print("\n[FALLO] La distribución de estados cambió frente a los datos oficiales.")
        return 1

    known_cases = [
        ("Brisas del Golf", "mozzarella", "OMITIDO"),
        ("Costa del Este", "aji_chombo", "DATO_INVALIDO"),
        ("Costa del Este", "harina", "FALTANTE"),
        ("Marbella", "pepperoni", "FALTANTE"),
        ("Brisas del Golf", "cebolla", "SOBREPEDIDO"),
        ("Via Argentina", "albahaca", "SOBREPEDIDO"),
    ]

    print("\nCasos intencionales:")
    for branch, ingredient, expected_status in known_cases:
        rows = result.analysis.loc[
            result.analysis["sucursal"].eq(branch)
            & result.analysis["ingrediente_id"].eq(ingredient)
        ]
        actual_status = rows.iloc[0]["estado"] if len(rows) == 1 else "NO_ENCONTRADO"
        marker = "OK" if actual_status == expected_status else "FALLO"
        print(
            f"  [{marker}] {branch} / {ingredient}: "
            f"{actual_status} (esperado {expected_status})"
        )
        if marker == "FALLO":
            return 1

    print("\nRESULTADO: OK · Los datos oficiales y el motor mantienen el comportamiento esperado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
