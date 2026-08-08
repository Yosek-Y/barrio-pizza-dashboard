import pandas as pd
import pytest

from src.data_loader import DataBundle
from src.order_workspace import (
    editor_frame,
    missing_order_columns,
    normalize_order_frame,
    with_order,
)


def _bundle() -> DataBundle:
    return DataBundle(
        ingredientes=pd.DataFrame(
            {
                "ingrediente_id": ["harina"],
                "nombre": ["Harina 00"],
                "proveedor": ["Proveedor"],
                "unidad_base": ["kg"],
                "formato_compra": ["Saco"],
                "unidad_base_por_formato": [25],
                "es_perecedero": ["No"],
            }
        ),
        consumo_historico=pd.DataFrame(),
        inventario_actual=pd.DataFrame(),
        orden_compra=pd.DataFrame(
            {"sucursal": ["A"], "ingrediente_id": ["harina"], "cantidad_formatos": [2]}
        ),
    )


def test_normalize_order_frame_trims_text_and_ignores_extra_columns() -> None:
    raw = pd.DataFrame(
        {
            " sucursal ": [" Brisas del Golf "],
            "ingrediente_id": [" harina "],
            "cantidad_formatos": ["10"],
            "comentario": ["extra"],
        }
    )
    result = normalize_order_frame(raw)
    assert result.columns.tolist() == ["sucursal", "ingrediente_id", "cantidad_formatos"]
    assert result.loc[0, "sucursal"] == "Brisas del Golf"
    assert result.loc[0, "ingrediente_id"] == "harina"


def test_missing_order_columns_reports_required_schema() -> None:
    frame = pd.DataFrame({"sucursal": ["A"]})
    assert missing_order_columns(frame) == ("ingrediente_id", "cantidad_formatos")
    with pytest.raises(ValueError):
        normalize_order_frame(frame)


def test_with_order_replaces_only_the_order_dataset() -> None:
    base = _bundle()
    replacement = pd.DataFrame(
        {"sucursal": ["B"], "ingrediente_id": ["harina"], "cantidad_formatos": [4]}
    )
    result = with_order(base, replacement)
    assert result.orden_compra.loc[0, "sucursal"] == "B"
    assert result.ingredientes.equals(base.ingredientes)


def test_editor_frame_adds_friendly_ingredient_name() -> None:
    base = _bundle()
    result = editor_frame(base.orden_compra, base.ingredientes)
    assert result.loc[0, "nombre"] == "Harina 00"
