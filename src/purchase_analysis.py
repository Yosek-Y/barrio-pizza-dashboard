"""Necesidad real, formatos recomendados y alertas de órdenes de compra.

La Fase 3 transforma la proyección de consumo en una recomendación accionable.
Todas las comparaciones se realizan en dos niveles:

1. Unidad base (kg, L o unidades), para explicar faltantes y cobertura.
2. Formatos completos, para respetar que no se puede comprar medio saco o media caja.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import pandas as pd

from src.data_loader import DataBundle
from src.forecasting import ForecastResult

STATUS_ORDER = ("DATO_INVALIDO", "OMITIDO", "FALTANTE", "SOBREPEDIDO", "CORRECTO")

ANALYSIS_COLUMNS = (
    "sucursal",
    "ingrediente_id",
    "nombre",
    "proveedor",
    "unidad_base",
    "formato_compra",
    "unidad_base_por_formato",
    "es_perecedero",
    "consumo_proyectado",
    "inventario_actual",
    "necesidad_real",
    "orden_presente",
    "formatos_solicitados",
    "cantidad_solicitada_unidad_base",
    "formatos_recomendados",
    "cantidad_recomendada_unidad_base",
    "diferencia_formatos",
    "faltante_unidad_base",
    "excedente_sobre_necesidad",
    "excedente_sobre_recomendacion",
    "estado",
    "prioridad",
    "accion_recomendada",
    "mensaje",
)

CORRECTED_ORDER_COLUMNS = (
    "sucursal",
    "proveedor",
    "ingrediente_id",
    "nombre",
    "unidad_base",
    "formato_compra",
    "formatos_solicitados",
    "formatos_recomendados",
    "ajuste_formatos",
    "estado",
    "accion_recomendada",
)

SUPPLIER_SUMMARY_COLUMNS = (
    "proveedor",
    "sucursal",
    "lineas",
    "formatos_actuales",
    "formatos_recomendados",
    "ajuste_neto_formatos",
    "lineas_con_cambio",
)


@dataclass(frozen=True)
class PurchaseAnalysisResult:
    """Resultado tabular del motor de compras."""

    analysis: pd.DataFrame

    @property
    def total_rows(self) -> int:
        return len(self.analysis)

    def count(self, status: str) -> int:
        """Cuenta filas de un estado sin asumir que la tabla contiene datos."""
        if self.analysis.empty or "estado" not in self.analysis.columns:
            return 0
        return int(self.analysis["estado"].eq(status).sum())

    @property
    def alert_count(self) -> int:
        """Cantidad de filas que requieren una acción o revisión."""
        if self.analysis.empty:
            return 0
        return int((~self.analysis["estado"].eq("CORRECTO")).sum())

    @property
    def actionable_count(self) -> int:
        """Cantidad de pedidos que deben aumentar, reducirse o agregarse."""
        if self.analysis.empty:
            return 0
        return int(
            self.analysis["estado"].isin({"OMITIDO", "FALTANTE", "SOBREPEDIDO"}).sum()
        )

    def summary(self) -> dict[str, int]:
        """Resumen estable para métricas, pruebas y futuras exportaciones."""
        return {status: self.count(status) for status in STATUS_ORDER}

    def corrected_order(self) -> pd.DataFrame:
        """Versión recomendada del pedido para operación y descarga.

        Reglas:
        - excluye datos inválidos porque no pueden aprobarse automáticamente;
        - excluye líneas cuya recomendación final es cero formatos;
        - conserva cuántos formatos se pidieron, cuántos se recomiendan y el ajuste neto.
        """
        if self.analysis.empty:
            return pd.DataFrame(columns=CORRECTED_ORDER_COLUMNS)

        frame = self.analysis.copy()
        valid_mask = ~frame["estado"].eq("DATO_INVALIDO")
        positive_recommendation = frame["formatos_recomendados"].fillna(0).gt(0)
        corrected = frame.loc[valid_mask & positive_recommendation].copy()
        if corrected.empty:
            return pd.DataFrame(columns=CORRECTED_ORDER_COLUMNS)

        corrected["ajuste_formatos"] = (
            corrected["formatos_recomendados"].fillna(0)
            - corrected["formatos_solicitados"].fillna(0)
        ).astype("Float64")

        corrected = corrected.reindex(columns=CORRECTED_ORDER_COLUMNS)
        corrected = corrected.sort_values(
            ["proveedor", "sucursal", "nombre", "ingrediente_id"],
            na_position="last",
        ).reset_index(drop=True)
        return corrected

    def supplier_summary(self) -> pd.DataFrame:
        """Agrupa el pedido corregido por proveedor y sucursal."""
        corrected = self.corrected_order()
        if corrected.empty:
            return pd.DataFrame(columns=SUPPLIER_SUMMARY_COLUMNS)

        summary = (
            corrected.groupby(["proveedor", "sucursal"], dropna=False)
            .agg(
                lineas=("ingrediente_id", "count"),
                formatos_actuales=("formatos_solicitados", "sum"),
                formatos_recomendados=("formatos_recomendados", "sum"),
                ajuste_neto_formatos=("ajuste_formatos", "sum"),
                lineas_con_cambio=(
                    "ajuste_formatos",
                    lambda values: int((pd.Series(values).fillna(0) != 0).sum()),
                ),
            )
            .reset_index()
        )

        numeric_columns = (
            "formatos_actuales",
            "formatos_recomendados",
            "ajuste_neto_formatos",
        )
        for column in numeric_columns:
            summary[column] = pd.to_numeric(summary[column], errors="coerce").round(2)

        return summary.reindex(columns=SUPPLIER_SUMMARY_COLUMNS).sort_values(
            ["proveedor", "sucursal"],
            na_position="last",
        ).reset_index(drop=True)


def _empty_analysis() -> pd.DataFrame:
    return pd.DataFrame(columns=ANALYSIS_COLUMNS)


def _as_float(value: object) -> float | None:
    """Convierte un valor numérico de Pandas evitando propagar ``pd.NA``."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _recommended_formats(need: float, format_size: float) -> int:
    """Redondea la necesidad hacia arriba porque solo se compran formatos completos."""
    if need <= 0:
        return 0

    # El pequeño epsilon evita que 50.0000000001 termine recomendando tres sacos de 25.
    return max(0, int(ceil((need - 1e-9) / format_size)))


def _format_quantity(value: float, unit: str) -> str:
    return f"{value:.2f} {unit}".replace(".00 ", " ")


def _classify_row(row: pd.Series) -> dict[str, object]:
    """Calcula y explica una combinación sucursal–ingrediente."""
    branch = str(row.get("sucursal", "Sucursal desconocida"))
    ingredient = str(row.get("nombre") or row.get("ingrediente_id") or "Ingrediente")
    unit = str(row.get("unidad_base") or "unidad base")
    purchase_format = str(row.get("formato_compra") or "formato")

    projected = _as_float(row.get("consumo_proyectado"))
    inventory = _as_float(row.get("stock_actual_unidad_base"))
    format_size = _as_float(row.get("unidad_base_por_formato"))
    order_present = bool(row.get("_order_present", False))
    ordered_formats = _as_float(row.get("cantidad_formatos")) if order_present else 0.0

    invalid_reasons: list[str] = []
    if projected is None:
        invalid_reasons.append("no existe una proyección numérica")
    if inventory is None:
        invalid_reasons.append("no existe inventario numérico")
    if format_size is None or format_size <= 0:
        invalid_reasons.append("el formato de compra no es válido")
    if order_present and ordered_formats is None:
        invalid_reasons.append("la cantidad solicitada no es numérica")
    if (
        order_present
        and ordered_formats is not None
        and abs(ordered_formats - round(ordered_formats)) > 1e-9
    ):
        invalid_reasons.append("la orden contiene una fracción de formato")

    if invalid_reasons:
        reason = "; ".join(invalid_reasons)
        return {
            "consumo_proyectado": projected,
            "inventario_actual": inventory,
            "necesidad_real": pd.NA,
            "orden_presente": order_present,
            "formatos_solicitados": ordered_formats if order_present else pd.NA,
            "cantidad_solicitada_unidad_base": pd.NA,
            "formatos_recomendados": pd.NA,
            "cantidad_recomendada_unidad_base": pd.NA,
            "diferencia_formatos": pd.NA,
            "faltante_unidad_base": pd.NA,
            "excedente_sobre_necesidad": pd.NA,
            "excedente_sobre_recomendacion": pd.NA,
            "estado": "DATO_INVALIDO",
            "prioridad": "CRÍTICA",
            "accion_recomendada": "Corregir los datos antes de aprobar la orden.",
            "mensaje": f"DATO INVÁLIDO: {branch} · {ingredient}: {reason}.",
        }

    assert projected is not None
    assert inventory is not None
    assert format_size is not None
    assert ordered_formats is not None

    need = max(projected - inventory, 0.0)
    recommended_formats = _recommended_formats(need, format_size)
    recommended_units = recommended_formats * format_size
    ordered_units = ordered_formats * format_size
    format_difference = ordered_formats - recommended_formats
    shortage = max(need - ordered_units, 0.0)
    excess_over_need = max(ordered_units - need, 0.0)
    excess_over_recommendation = max(ordered_units - recommended_units, 0.0)

    if not order_present and recommended_formats > 0:
        status = "OMITIDO"
        priority = "ALTA"
        action = (
            f"Agregar {recommended_formats} formato(s) de {purchase_format} "
            f"({_format_quantity(recommended_units, unit)})."
        )
        message = (
            f"ALERTA: {branch} omitió {ingredient} en su orden. La necesidad real es "
            f"{_format_quantity(need, unit)}, por lo que debe agregar {recommended_formats} "
            f"formato(s) de {purchase_format}."
        )
    elif ordered_formats < recommended_formats:
        missing_formats = int(round(recommended_formats - ordered_formats))
        status = "FALTANTE"
        priority = "ALTA"
        action = (
            f"Aumentar {missing_formats} formato(s) hasta llegar a "
            f"{recommended_formats} de {purchase_format}."
        )
        message = (
            f"ALERTA: {branch} está pidiendo {_format_quantity(shortage, unit)} de "
            f"{ingredient} menos que la necesidad proyectada → riesgo de quiebre. "
            f"Pedido recomendado: {recommended_formats} formato(s) de {purchase_format}."
        )
    elif ordered_formats > recommended_formats:
        extra_formats = int(round(ordered_formats - recommended_formats))
        status = "SOBREPEDIDO"
        priority = "MEDIA"
        action = (
            f"Reducir {extra_formats} formato(s) y dejar el pedido en "
            f"{recommended_formats} de {purchase_format}."
        )
        message = (
            f"ALERTA: {branch} está pidiendo {extra_formats} formato(s) adicional(es) de "
            f"{ingredient}, equivalentes a "
            f"{_format_quantity(excess_over_recommendation, unit)} por encima del pedido "
            "recomendado → riesgo de sobrestock."
        )
    else:
        status = "CORRECTO"
        priority = "OK"
        action = "Mantener la orden sin cambios."
        if recommended_formats == 0:
            message = (
                f"OK: el inventario de {ingredient} en {branch} cubre la proyección; "
                "no se necesita comprar esta semana."
            )
        else:
            message = (
                f"OK: el pedido de {ingredient} en {branch} cubre la necesidad real. "
                f"El excedente de redondeo es {_format_quantity(excess_over_need, unit)}, "
                f"menor que un formato completo de {_format_quantity(format_size, unit)}."
            )

    return {
        "consumo_proyectado": round(projected, 2),
        "inventario_actual": round(inventory, 2),
        "necesidad_real": round(need, 2),
        "orden_presente": order_present,
        "formatos_solicitados": round(ordered_formats, 2),
        "cantidad_solicitada_unidad_base": round(ordered_units, 2),
        "formatos_recomendados": recommended_formats,
        "cantidad_recomendada_unidad_base": round(recommended_units, 2),
        "diferencia_formatos": round(format_difference, 2),
        "faltante_unidad_base": round(shortage, 2),
        "excedente_sobre_necesidad": round(excess_over_need, 2),
        "excedente_sobre_recomendacion": round(excess_over_recommendation, 2),
        "estado": status,
        "prioridad": priority,
        "accion_recomendada": action,
        "mensaje": message,
    }


def _build_projected_rows(data: DataBundle, forecast: ForecastResult) -> pd.DataFrame:
    """Une proyección, catálogo, inventario y orden para las combinaciones esperadas."""
    projections = forecast.projections.copy()
    if projections.empty:
        return _empty_analysis()

    keys = ["sucursal", "ingrediente_id"]
    catalog_columns = [
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "formato_compra",
        "unidad_base_por_formato",
        "es_perecedero",
    ]
    catalog = data.ingredientes[catalog_columns].drop_duplicates("ingrediente_id")

    # La proyección ya trae parte del catálogo. Se conservan solo las columnas calculadas
    # para evitar sufijos como nombre_x y nombre_y al volver a unir el catálogo completo.
    projection_columns = [
        "sucursal",
        "ingrediente_id",
        "consumo_proyectado",
        "historico_completo",
        "metodo_proyeccion",
    ]
    combined = projections[projection_columns].merge(
        catalog,
        on="ingrediente_id",
        how="left",
        validate="many_to_one",
    )

    inventory = data.inventario_actual[
        ["sucursal", "ingrediente_id", "stock_actual_unidad_base"]
    ].drop_duplicates(keys)
    combined = combined.merge(inventory, on=keys, how="left", validate="one_to_one")

    orders = data.orden_compra[
        ["sucursal", "ingrediente_id", "cantidad_formatos"]
    ].drop_duplicates(keys)
    combined = combined.merge(
        orders.assign(_order_present=True),
        on=keys,
        how="left",
        validate="one_to_one",
    )
    combined["_order_present"] = combined["_order_present"].eq(True)

    calculated = pd.DataFrame((_classify_row(row) for _, row in combined.iterrows()))
    base_columns = [
        "sucursal",
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "formato_compra",
        "unidad_base_por_formato",
        "es_perecedero",
    ]
    return pd.concat(
        [combined[base_columns].reset_index(drop=True), calculated.reset_index(drop=True)],
        axis=1,
    )


def _build_unmatched_order_rows(data: DataBundle, forecast: ForecastResult) -> pd.DataFrame:
    """Conserva órdenes sin catálogo o sin histórico como datos inválidos visibles."""
    keys = ["sucursal", "ingrediente_id"]
    orders = data.orden_compra.copy()
    if orders.empty or not set(keys).issubset(orders.columns):
        return _empty_analysis()

    projected_keys = forecast.projections[keys].drop_duplicates().assign(_projected=True)
    unmatched = orders.merge(projected_keys, on=keys, how="left")
    unmatched = unmatched.loc[unmatched["_projected"].isna()].copy()
    if unmatched.empty:
        return _empty_analysis()

    catalog = data.ingredientes[
        [
            "ingrediente_id",
            "nombre",
            "proveedor",
            "unidad_base",
            "formato_compra",
            "unidad_base_por_formato",
            "es_perecedero",
        ]
    ].drop_duplicates("ingrediente_id")
    unmatched = unmatched.merge(catalog, on="ingrediente_id", how="left")

    rows: list[dict[str, object]] = []
    for _, row in unmatched.iterrows():
        known = pd.notna(row.get("nombre"))
        ingredient = str(row.get("nombre") if known else row.get("ingrediente_id"))
        reason = (
            "el ingrediente no existe en el catálogo maestro"
            if not known
            else "no existe histórico suficiente para proyectar esta combinación"
        )
        rows.append(
            {
                "sucursal": row.get("sucursal"),
                "ingrediente_id": row.get("ingrediente_id"),
                "nombre": ingredient,
                "proveedor": row.get("proveedor"),
                "unidad_base": row.get("unidad_base"),
                "formato_compra": row.get("formato_compra"),
                "unidad_base_por_formato": row.get("unidad_base_por_formato"),
                "es_perecedero": row.get("es_perecedero"),
                "consumo_proyectado": pd.NA,
                "inventario_actual": pd.NA,
                "necesidad_real": pd.NA,
                "orden_presente": True,
                "formatos_solicitados": row.get("cantidad_formatos"),
                "cantidad_solicitada_unidad_base": pd.NA,
                "formatos_recomendados": pd.NA,
                "cantidad_recomendada_unidad_base": pd.NA,
                "diferencia_formatos": pd.NA,
                "faltante_unidad_base": pd.NA,
                "excedente_sobre_necesidad": pd.NA,
                "excedente_sobre_recomendacion": pd.NA,
                "estado": "DATO_INVALIDO",
                "prioridad": "CRÍTICA",
                "accion_recomendada": "Revisar la línea antes de aprobar la orden.",
                "mensaje": (
                    f"DATO INVÁLIDO: {row.get('sucursal')} pidió {ingredient}, pero {reason}."
                ),
            }
        )

    return pd.DataFrame(rows).reindex(columns=ANALYSIS_COLUMNS)


def analyze_orders(data: DataBundle, forecast: ForecastResult) -> PurchaseAnalysisResult:
    """Calcula necesidad, recomendación y estado de cada línea de compra.

    Reglas centrales:
    - ``necesidad_real = max(proyección - inventario, 0)``;
    - ``formatos_recomendados = ceil(necesidad_real / tamaño_del_formato)``;
    - pedir exactamente los formatos recomendados es correcto;
    - pedir menos es faltante;
    - pedir más implica al menos un formato completo adicional y es sobrepedido;
    - una línea ausente con necesidad positiva es una omisión;
    - órdenes sin catálogo o sin proyección permanecen visibles como dato inválido.
    """
    projected_rows = _build_projected_rows(data, forecast)
    unmatched_rows = _build_unmatched_order_rows(data, forecast)

    frames = [frame for frame in (projected_rows, unmatched_rows) if not frame.empty]
    if not frames:
        return PurchaseAnalysisResult(_empty_analysis())

    records = [record for frame in frames for record in frame.to_dict("records")]
    result = pd.DataFrame.from_records(records)

    result = result.reindex(columns=ANALYSIS_COLUMNS)
    numeric_columns = (
        "unidad_base_por_formato",
        "consumo_proyectado",
        "inventario_actual",
        "necesidad_real",
        "formatos_solicitados",
        "cantidad_solicitada_unidad_base",
        "formatos_recomendados",
        "cantidad_recomendada_unidad_base",
        "diferencia_formatos",
        "faltante_unidad_base",
        "excedente_sobre_necesidad",
        "excedente_sobre_recomendacion",
    )
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("Float64")
    result["orden_presente"] = result["orden_presente"].eq(True)

    severity_rank = {
        "DATO_INVALIDO": 0,
        "OMITIDO": 1,
        "FALTANTE": 2,
        "SOBREPEDIDO": 3,
        "CORRECTO": 4,
    }
    result["_rank"] = result["estado"].map(severity_rank).fillna(99)
    result = result.sort_values(
        ["_rank", "sucursal", "nombre", "ingrediente_id"],
        na_position="last",
    ).drop(columns="_rank")
    result = result.reset_index(drop=True)

    return PurchaseAnalysisResult(result)
