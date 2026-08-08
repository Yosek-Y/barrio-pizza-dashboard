"""Optimización de redistribución entre sucursales antes de comprar más.

La idea es mirar la red completa, no cada sucursal de forma aislada. Después de
considerar inventario, pedido activo y consumo proyectado, una sucursal puede
quedar con un excedente seguro de un ingrediente mientras otra todavía queda
corta. Ese excedente puede convertirse en una sugerencia de traslado o
reasignación interna antes de incrementar la compra al proveedor.

Importante: un excedente menor a un formato completo sigue siendo *redondeo
normal* y NO se reclasifica como sobrepedido. Simplemente se aprovecha como una
posible fuente de redistribución a nivel de red.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import pandas as pd


TRANSFER_COLUMNS = [
    "ingrediente_id",
    "nombre",
    "proveedor",
    "unidad_base",
    "formato_compra",
    "unidad_base_por_formato",
    "es_perecedero",
    "sucursal_origen",
    "sucursal_destino",
    "tipo_origen",
    "viabilidad",
    "cantidad_transferir",
    "equivalente_formatos",
    "deficit_destino_antes",
    "deficit_destino_despues",
    "formatos_adicionales_antes",
    "formatos_adicionales_despues",
    "formatos_evitados_incrementales",
    "accion_recomendada",
]

RECEIVER_COLUMNS = [
    "ingrediente_id",
    "nombre",
    "proveedor",
    "unidad_base",
    "formato_compra",
    "es_perecedero",
    "sucursal_destino",
    "deficit_post_orden",
    "cantidad_redistribuida",
    "deficit_restante",
    "formatos_adicionales_antes",
    "formatos_adicionales_despues",
    "formatos_evitados",
    "porcentaje_deficit_cubierto",
]


@dataclass(frozen=True)
class RedistributionResult:
    """Sugerencias de traslado y resumen de ahorro potencial."""

    evaluated: pd.DataFrame
    transfers: pd.DataFrame
    receivers: pd.DataFrame

    @property
    def transfer_count(self) -> int:
        return len(self.transfers)

    @property
    def formats_avoided(self) -> int:
        if self.receivers.empty:
            return 0
        return int(pd.to_numeric(self.receivers["formatos_evitados"], errors="coerce").fillna(0).sum())

    @property
    def product_count(self) -> int:
        if self.transfers.empty:
            return 0
        return int(self.transfers["ingrediente_id"].nunique())

    @property
    def benefited_branch_count(self) -> int:
        if self.transfers.empty:
            return 0
        return int(self.transfers["sucursal_destino"].nunique())

    @property
    def donor_branch_count(self) -> int:
        if self.transfers.empty:
            return 0
        return int(self.transfers["sucursal_origen"].nunique())


def _empty_result(evaluated: pd.DataFrame | None = None) -> RedistributionResult:
    return RedistributionResult(
        evaluated=pd.DataFrame() if evaluated is None else evaluated,
        transfers=pd.DataFrame(columns=TRANSFER_COLUMNS),
        receivers=pd.DataFrame(columns=RECEIVER_COLUMNS),
    )


def _formats_needed(quantity: float, format_size: float) -> int:
    if quantity <= 1e-9:
        return 0
    return max(0, int(ceil((quantity - 1e-9) / format_size)))


def _source_type(row: pd.Series) -> tuple[str, str, int]:
    """Clasifica de dónde sale el excedente y su prioridad operativa."""
    projected = float(row["consumo_proyectado"])
    inventory = float(row["inventario_actual"])
    ordered = float(row["cantidad_solicitada_unidad_base"])
    recommended = float(row["cantidad_recomendada_unidad_base"])

    if inventory - projected > 1e-9:
        return "INVENTARIO_EXCEDENTE", "ALTA", 0
    if ordered - recommended > 1e-9:
        return "REASIGNAR_PEDIDO", "ALTA", 1
    return "REDONDEO_FORMATO", "MEDIA", 2


def optimize_redistribution(analysis: pd.DataFrame) -> RedistributionResult:
    """Busca excedentes post-orden que puedan cubrir déficits de otras sucursales.

    Para cada combinación sucursal/ingrediente se calcula el balance después de
    recibir la orden activa:

        balance_post_orden = inventario + pedido - consumo proyectado

    - balance positivo: excedente seguro potencial.
    - balance negativo: déficit que todavía quedaría después de la orden.

    Los excedentes se asignan solamente al mismo ingrediente. Se prioriza:
    inventario ya disponible, luego formatos claramente excedentes del pedido y,
    finalmente, sobrantes producidos por el redondeo normal del formato.

    Solo se conservan grupos donde la redistribución logra evitar al menos un
    formato adicional de compra al proveedor. De esta forma la salida se enfoca
    en recomendaciones con impacto real sobre la compra semanal.
    """
    required = {
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
        "cantidad_solicitada_unidad_base",
        "cantidad_recomendada_unidad_base",
        "formatos_solicitados",
        "formatos_recomendados",
        "estado",
    }
    if analysis is None or analysis.empty or not required.issubset(analysis.columns):
        return _empty_result()

    work = analysis.loc[~analysis["estado"].eq("DATO_INVALIDO")].copy()
    numeric = [
        "unidad_base_por_formato",
        "consumo_proyectado",
        "inventario_actual",
        "cantidad_solicitada_unidad_base",
        "cantidad_recomendada_unidad_base",
        "formatos_solicitados",
        "formatos_recomendados",
    ]
    for column in numeric:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    work = work.dropna(
        subset=[
            "unidad_base_por_formato",
            "consumo_proyectado",
            "inventario_actual",
            "cantidad_solicitada_unidad_base",
            "cantidad_recomendada_unidad_base",
        ]
    ).copy()
    work = work.loc[work["unidad_base_por_formato"].gt(0)].copy()
    if work.empty:
        return _empty_result()

    work["balance_post_orden"] = (
        work["inventario_actual"]
        + work["cantidad_solicitada_unidad_base"]
        - work["consumo_proyectado"]
    )
    work["excedente_post_orden"] = work["balance_post_orden"].clip(lower=0)
    work["deficit_post_orden"] = (-work["balance_post_orden"]).clip(lower=0)

    source_data = work.apply(_source_type, axis=1, result_type="expand")
    source_data.columns = ["tipo_origen", "viabilidad", "prioridad_origen"]
    work = pd.concat([work, source_data], axis=1)

    transfer_rows: list[dict[str, object]] = []
    receiver_rows: list[dict[str, object]] = []

    for ingredient_id, group in work.groupby("ingrediente_id", sort=False):
        donors = group.loc[group["excedente_post_orden"].gt(1e-9)].copy()
        receivers = group.loc[group["deficit_post_orden"].gt(1e-9)].copy()
        if donors.empty or receivers.empty:
            continue

        donors = donors.sort_values(
            ["prioridad_origen", "excedente_post_orden"],
            ascending=[True, False],
        )
        receivers = receivers.assign(
            _receiver_priority=receivers["estado"].map({"OMITIDO": 0, "FALTANTE": 1}).fillna(2)
        ).sort_values(["_receiver_priority", "deficit_post_orden"], ascending=[True, False])

        available = {idx: float(row["excedente_post_orden"]) for idx, row in donors.iterrows()}

        for receiver_idx, receiver in receivers.iterrows():
            format_size = float(receiver["unidad_base_por_formato"])
            initial_deficit = float(receiver["deficit_post_orden"])
            formats_before = _formats_needed(initial_deficit, format_size)
            remaining = initial_deficit
            candidate_rows: list[dict[str, object]] = []

            for donor_idx, donor in donors.iterrows():
                if donor["sucursal"] == receiver["sucursal"]:
                    continue
                donor_available = available.get(donor_idx, 0.0)
                if donor_available <= 1e-9 or remaining <= 1e-9:
                    continue

                before_transfer = remaining
                formats_before_step = _formats_needed(before_transfer, format_size)
                transfer = min(donor_available, remaining)
                remaining = max(0.0, remaining - transfer)
                available[donor_idx] = max(0.0, donor_available - transfer)
                formats_after_step = _formats_needed(remaining, format_size)

                source_type = str(donor["tipo_origen"])
                if source_type == "REASIGNAR_PEDIDO":
                    action = "Reasignar parte del pedido antes de recibirlo."
                elif source_type == "INVENTARIO_EXCEDENTE":
                    action = "Trasladar inventario disponible antes de comprar más."
                else:
                    action = "Consolidar el sobrante normal de redondeo; validar empaque y logística del traslado."

                candidate_rows.append(
                    {
                        "ingrediente_id": ingredient_id,
                        "nombre": receiver["nombre"],
                        "proveedor": receiver["proveedor"],
                        "unidad_base": receiver["unidad_base"],
                        "formato_compra": receiver["formato_compra"],
                        "unidad_base_por_formato": format_size,
                        "es_perecedero": receiver["es_perecedero"],
                        "sucursal_origen": donor["sucursal"],
                        "sucursal_destino": receiver["sucursal"],
                        "tipo_origen": source_type,
                        "viabilidad": donor["viabilidad"],
                        "cantidad_transferir": round(transfer, 4),
                        "equivalente_formatos": round(transfer / format_size, 4),
                        "deficit_destino_antes": round(before_transfer, 4),
                        "deficit_destino_despues": round(remaining, 4),
                        "formatos_adicionales_antes": formats_before_step,
                        "formatos_adicionales_despues": formats_after_step,
                        "formatos_evitados_incrementales": formats_before_step - formats_after_step,
                        "accion_recomendada": action,
                    }
                )

            formats_after = _formats_needed(remaining, format_size)
            formats_avoided = formats_before - formats_after

            # Si no se evita ningún formato, restauramos los excedentes consumidos
            # por este intento y no mostramos una transferencia sin impacto de compra.
            if formats_avoided <= 0:
                for row in candidate_rows:
                    donor_matches = donors.index[donors["sucursal"].eq(row["sucursal_origen"])].tolist()
                    if donor_matches:
                        available[donor_matches[0]] += float(row["cantidad_transferir"])
                continue

            transfer_rows.extend(candidate_rows)
            transferred = initial_deficit - remaining
            receiver_rows.append(
                {
                    "ingrediente_id": ingredient_id,
                    "nombre": receiver["nombre"],
                    "proveedor": receiver["proveedor"],
                    "unidad_base": receiver["unidad_base"],
                    "formato_compra": receiver["formato_compra"],
                    "es_perecedero": receiver["es_perecedero"],
                    "sucursal_destino": receiver["sucursal"],
                    "deficit_post_orden": round(initial_deficit, 4),
                    "cantidad_redistribuida": round(transferred, 4),
                    "deficit_restante": round(remaining, 4),
                    "formatos_adicionales_antes": formats_before,
                    "formatos_adicionales_despues": formats_after,
                    "formatos_evitados": formats_avoided,
                    "porcentaje_deficit_cubierto": round((transferred / initial_deficit) * 100, 2),
                }
            )

    if not transfer_rows:
        return _empty_result(work.reset_index(drop=True))

    transfers = pd.DataFrame(transfer_rows, columns=TRANSFER_COLUMNS)
    receivers = pd.DataFrame(receiver_rows, columns=RECEIVER_COLUMNS)

    transfers = transfers.sort_values(
        ["formatos_evitados_incrementales", "nombre", "sucursal_destino", "cantidad_transferir"],
        ascending=[False, True, True, False],
    ).reset_index(drop=True)
    receivers = receivers.sort_values(
        ["formatos_evitados", "nombre", "sucursal_destino"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    return RedistributionResult(
        evaluated=work.reset_index(drop=True),
        transfers=transfers,
        receivers=receivers,
    )
