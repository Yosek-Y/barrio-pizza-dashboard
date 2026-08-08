"""Detección de pedidos atípicos entre sucursales.

La comparación se hace sobre la *cobertura post-compra* de cada ingrediente:

    (inventario actual + cantidad pedida en unidad base) / consumo proyectado

Una cobertura de 1.0 equivale, aproximadamente, a una semana de consumo cubierta
tras recibir la orden. Para cada sucursal se compara ese indicador con la mediana
de las demás sucursales que manejan el mismo ingrediente.

Este enfoque evita comparar directamente cajas/sacos entre productos y también
incorpora el inventario disponible y el pronóstico particular de cada sucursal.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


ANOMALY_COLUMNS = [
    "sucursal",
    "ingrediente_id",
    "nombre",
    "proveedor",
    "unidad_base",
    "es_perecedero",
    "tipo_anomalia",
    "severidad_anomalia",
    "cobertura_post_compra",
    "cobertura_mediana_pares",
    "factor_vs_pares",
    "diferencia_cobertura",
    "formatos_solicitados",
    "formatos_recomendados",
    "estado_orden",
    "prioridad_orden",
    "accion_recomendada",
    "mensaje_anomalia",
]


@dataclass(frozen=True)
class CrossBranchAnomalyResult:
    """Resultado de la comparación entre sucursales."""

    evaluated: pd.DataFrame
    anomalies: pd.DataFrame

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    @property
    def high_count(self) -> int:
        if self.anomalies.empty:
            return 0
        return int(self.anomalies["tipo_anomalia"].eq("COBERTURA_ALTA").sum())

    @property
    def low_count(self) -> int:
        if self.anomalies.empty:
            return 0
        return int(self.anomalies["tipo_anomalia"].eq("COBERTURA_BAJA").sum())


def _empty_result() -> CrossBranchAnomalyResult:
    empty = pd.DataFrame(columns=ANOMALY_COLUMNS)
    return CrossBranchAnomalyResult(evaluated=pd.DataFrame(), anomalies=empty)


def detect_cross_branch_anomalies(
    analysis: pd.DataFrame,
    *,
    high_factor: float = 1.75,
    low_factor: float = 0.55,
    min_high_gap: float = 0.50,
    min_low_gap: float = 0.35,
    min_peers: int = 2,
) -> CrossBranchAnomalyResult:
    """Detecta coberturas de compra muy distintas a las sucursales pares.

    Los factores se calculan contra la mediana *leave-one-out*: para evaluar una
    sucursal, su propio valor no participa en la referencia. Con solo cuatro
    sucursales esto es más estable y explicable que un z-score clásico.
    """
    required = {
        "sucursal",
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "es_perecedero",
        "consumo_proyectado",
        "inventario_actual",
        "cantidad_solicitada_unidad_base",
        "formatos_solicitados",
        "formatos_recomendados",
        "estado",
        "prioridad",
    }
    if analysis.empty or not required.issubset(analysis.columns):
        return _empty_result()

    work = analysis.copy()
    work = work.loc[~work["estado"].eq("DATO_INVALIDO")].copy()

    numeric_columns = [
        "consumo_proyectado",
        "inventario_actual",
        "cantidad_solicitada_unidad_base",
        "formatos_solicitados",
        "formatos_recomendados",
    ]
    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    work = work.loc[
        work["consumo_proyectado"].gt(0)
        & work["inventario_actual"].notna()
        & work["cantidad_solicitada_unidad_base"].notna()
    ].copy()
    if work.empty:
        return _empty_result()

    work["cobertura_post_compra"] = (
        work["inventario_actual"] + work["cantidad_solicitada_unidad_base"]
    ) / work["consumo_proyectado"]

    peer_medians: list[float | None] = []
    peer_counts: list[int] = []
    for index, row in work.iterrows():
        peers = work.loc[
            work["ingrediente_id"].eq(row["ingrediente_id"])
            & ~work["sucursal"].eq(row["sucursal"]),
            "cobertura_post_compra",
        ].dropna()
        peer_counts.append(len(peers))
        peer_medians.append(float(peers.median()) if len(peers) >= min_peers else None)

    work["cantidad_pares"] = peer_counts
    work["cobertura_mediana_pares"] = peer_medians
    work["factor_vs_pares"] = work["cobertura_post_compra"] / work["cobertura_mediana_pares"]
    work["diferencia_cobertura"] = (
        work["cobertura_post_compra"] - work["cobertura_mediana_pares"]
    )

    valid_reference = work["cobertura_mediana_pares"].gt(0) & work["cantidad_pares"].ge(min_peers)
    high_mask = (
        valid_reference
        & work["factor_vs_pares"].ge(high_factor)
        & work["diferencia_cobertura"].ge(min_high_gap)
    )
    low_mask = (
        valid_reference
        & work["factor_vs_pares"].le(low_factor)
        & work["diferencia_cobertura"].le(-min_low_gap)
    )

    anomalies = work.loc[high_mask | low_mask].copy()
    if anomalies.empty:
        return CrossBranchAnomalyResult(evaluated=work, anomalies=pd.DataFrame(columns=ANOMALY_COLUMNS))

    anomalies["tipo_anomalia"] = ""
    anomalies.loc[high_mask.loc[anomalies.index], "tipo_anomalia"] = "COBERTURA_ALTA"
    anomalies.loc[low_mask.loc[anomalies.index], "tipo_anomalia"] = "COBERTURA_BAJA"

    anomalies["severidad_anomalia"] = "MEDIA"
    extreme_mask = anomalies["factor_vs_pares"].ge(2.5) | anomalies["factor_vs_pares"].le(0.25)
    anomalies.loc[extreme_mask, "severidad_anomalia"] = "ALTA"

    anomaly_score = anomalies["factor_vs_pares"].where(
        anomalies["factor_vs_pares"].ge(1),
        1 / anomalies["factor_vs_pares"].clip(lower=0.01),
    )
    anomalies["indice_atipicidad"] = anomaly_score

    def _message(row: pd.Series) -> str:
        branch = row["sucursal"]
        product = row["nombre"]
        coverage = row["cobertura_post_compra"]
        peers = row["cobertura_mediana_pares"]
        factor = row["factor_vs_pares"]
        if row["tipo_anomalia"] == "COBERTURA_ALTA":
            return (
                f"{branch} quedaría con {coverage:.2f} semanas de cobertura de {product} "
                f"después de recibir la orden, frente a {peers:.2f} semanas como mediana "
                f"de las otras sucursales ({factor:.1f}×). Conviene validar si existe una "
                "razón operativa antes de aprobar el pedido."
            )
        percent = max(factor, 0) * 100
        return (
            f"{branch} quedaría con solo {coverage:.2f} semanas de cobertura de {product}, "
            f"equivalente al {percent:.0f}% de la mediana de las otras sucursales "
            f"({peers:.2f} semanas). Conviene revisar si el pedido o el inventario están incompletos."
        )

    def _action(row: pd.Series) -> str:
        if row["tipo_anomalia"] == "COBERTURA_ALTA":
            return "Validar la causa del exceso de cobertura antes de aprobar."
        return "Revisar la cantidad pedida y el inventario antes de aprobar."

    anomalies["accion_recomendada"] = anomalies.apply(_action, axis=1)
    anomalies["mensaje_anomalia"] = anomalies.apply(_message, axis=1)
    anomalies["estado_orden"] = anomalies["estado"]
    anomalies["prioridad_orden"] = anomalies["prioridad"]

    anomalies = anomalies.sort_values(
        ["severidad_anomalia", "indice_atipicidad"],
        ascending=[True, False],
        key=lambda series: (
            series.map({"ALTA": 0, "MEDIA": 1}).fillna(9)
            if series.name == "severidad_anomalia"
            else series
        ),
    )

    return CrossBranchAnomalyResult(
        evaluated=work.reset_index(drop=False).rename(columns={"index": "analysis_index"}),
        anomalies=anomalies.reset_index(drop=False).rename(columns={"index": "analysis_index"}),
    )
