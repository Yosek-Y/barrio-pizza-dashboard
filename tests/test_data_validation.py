"""Pruebas del cargador y de las validaciones de la Fase 1."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_loader import DataBundle, load_data_bundle
from src.validations import validate_data


def _valid_bundle() -> DataBundle:
    return DataBundle(
        ingredientes=pd.DataFrame(
            {
                "ingrediente_id": ["harina", "mozzarella"],
                "nombre": ["Harina 00", "Mozzarella"],
                "proveedor": ["Molinos", "Distribuidora"],
                "unidad_base": ["kg", "kg"],
                "formato_compra": ["Saco 25 kg", "Caja 10 kg"],
                "unidad_base_por_formato": ["25", "10"],
                "es_perecedero": ["No", "Si"],
            }
        ),
        consumo_historico=pd.DataFrame(
            [
                {
                    "sucursal": "Sucursal A",
                    "ingrediente_id": ingredient,
                    "semana": f"S{week}",
                    "consumo_unidad_base": str(value),
                }
                for ingredient, value in (("harina", 100), ("mozzarella", 50))
                for week in range(1, 7)
            ]
        ),
        inventario_actual=pd.DataFrame(
            {
                "sucursal": ["Sucursal A", "Sucursal A"],
                "ingrediente_id": ["harina", "mozzarella"],
                "stock_actual_unidad_base": ["20", "10"],
            }
        ),
        orden_compra=pd.DataFrame(
            {
                "sucursal": ["Sucursal A", "Sucursal A"],
                "ingrediente_id": ["harina", "mozzarella"],
                "cantidad_formatos": ["4", "4"],
            }
        ),
    )


def test_valid_bundle_has_no_issues() -> None:
    report = validate_data(_valid_bundle())
    assert not report.issues
    assert not report.has_errors
    assert str(report.cleaned_data.orden_compra["cantidad_formatos"].dtype) == "Float64"


def test_unknown_ingredient_and_omitted_order_are_detected() -> None:
    bundle = _valid_bundle()
    modified_orders = pd.DataFrame(
        {
            "sucursal": ["Sucursal A", "Sucursal A"],
            "ingrediente_id": ["harina", "aji_chombo"],
            "cantidad_formatos": ["4", "3"],
        }
    )
    report = validate_data(
        DataBundle(
            ingredientes=bundle.ingredientes,
            consumo_historico=bundle.consumo_historico,
            inventario_actual=bundle.inventario_actual,
            orden_compra=modified_orders,
        )
    )

    codes = {issue.code for issue in report.issues}
    assert "INGREDIENTE_DESCONOCIDO" in codes
    assert "LINEA_ORDEN_OMITIDA" in codes
    assert any("mozzarella" in example for issue in report.issues for example in issue.examples)


def test_invalid_numbers_and_negative_values_are_errors() -> None:
    bundle = _valid_bundle()
    invalid_inventory = bundle.inventario_actual.copy()
    invalid_inventory.loc[0, "stock_actual_unidad_base"] = "mucho"
    invalid_inventory.loc[1, "stock_actual_unidad_base"] = "-2"

    report = validate_data(
        DataBundle(
            ingredientes=bundle.ingredientes,
            consumo_historico=bundle.consumo_historico,
            inventario_actual=invalid_inventory,
            orden_compra=bundle.orden_compra,
        )
    )

    codes = {issue.code for issue in report.errors}
    assert "NUMERO_INVALIDO" in codes
    assert "VALOR_NEGATIVO" in codes


def test_loader_reads_the_four_expected_files(tmp_path: Path) -> None:
    bundle = _valid_bundle()
    filenames = {
        "ingredientes": "ingredientes.csv",
        "consumo_historico": "consumo_historico.csv",
        "inventario_actual": "inventario_actual.csv",
        "orden_compra": "orden_compra_semana.csv",
    }

    for dataset, filename in filenames.items():
        bundle.as_dict()[dataset].to_csv(tmp_path / filename, index=False, encoding="utf-8-sig")

    loaded = load_data_bundle(tmp_path)
    assert loaded.total_rows == bundle.total_rows
    assert set(loaded.as_dict()) == set(bundle.as_dict())
