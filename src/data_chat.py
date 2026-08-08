"""Asistente conversacional conectado a los datos del dashboard.

PizzIA usa dos capas:
1. Un contexto estructurado construido únicamente con los datos activos del dashboard.
2. Un modelo generativo opcional (Gemini) para convertir ese contexto en una respuesta natural.

Si no hay una API key configurada, el módulo mantiene un modo local de demostración
para preguntas operativas frecuentes. De esa forma el dashboard no deja de funcionar
por una credencial externa, pero el modo IA generativa se activa al configurar
``GEMINI_API_KEY`` en los secretos de Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


DEFAULT_MODEL = "gemini-3.1-flash-lite"


@dataclass(frozen=True)
class ChatResponse:
    """Respuesta producida por PizzIA."""

    text: str
    mode: str
    model: str | None = None


def _safe_records(frame: pd.DataFrame, columns: list[str], limit: int | None = None) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    usable = [column for column in columns if column in frame.columns]
    if not usable:
        return []
    selected = frame.loc[:, usable].copy()
    if limit is not None:
        selected = selected.head(limit)
    selected = selected.where(pd.notna(selected), None)
    return selected.to_dict(orient="records")


def build_chat_context(
    analysis: pd.DataFrame,
    forecast: pd.DataFrame,
    anomalies: pd.DataFrame,
    supplier_summary: pd.DataFrame,
    *,
    active_order_source: str,
    redistribution: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Construye un snapshot compacto y verificable de la situación actual."""

    status_counts: list[dict[str, Any]] = []
    branch_counts: list[dict[str, Any]] = []
    if analysis is not None and not analysis.empty:
        status_counts = (
            analysis.groupby("estado", dropna=False)
            .size()
            .reset_index(name="lineas")
            .sort_values("lineas", ascending=False)
            .to_dict(orient="records")
        )
        branch_counts = (
            analysis.loc[~analysis["estado"].eq("CORRECTO")]
            .groupby("sucursal", dropna=False)
            .size()
            .reset_index(name="alertas")
            .sort_values("alertas", ascending=False)
            .to_dict(orient="records")
        )

    actionable = analysis.loc[~analysis["estado"].eq("CORRECTO")].copy() if analysis is not None and not analysis.empty else pd.DataFrame()

    context = {
        "fuente_orden_activa": active_order_source,
        "resumen_estados": status_counts,
        "alertas_por_sucursal": branch_counts,
        "lineas_con_alerta": _safe_records(
            actionable,
            [
                "sucursal", "ingrediente_id", "nombre", "proveedor", "unidad_base",
                "consumo_proyectado", "inventario_actual", "necesidad_real",
                "formatos_solicitados", "formatos_recomendados", "estado", "prioridad",
                "accion_recomendada", "mensaje",
            ],
        ),
        "todas_las_lineas": _safe_records(
            analysis,
            [
                "sucursal", "ingrediente_id", "nombre", "proveedor", "unidad_base",
                "consumo_proyectado", "inventario_actual", "necesidad_real",
                "formatos_solicitados", "formatos_recomendados", "estado",
            ],
        ),
        "pronosticos": _safe_records(
            forecast,
            [
                "sucursal", "ingrediente_id", "nombre", "unidad_base", "consumo_proyectado",
                "consumo_proyectado_base", "metodo_proyeccion", "outliers_detectados",
                "tendencia_semanal", "confianza_proyeccion",
            ],
        ),
        "anomalias": _safe_records(
            anomalies,
            [
                "sucursal", "ingrediente_id", "nombre", "tipo_anomalia",
                "severidad_anomalia", "cobertura_post_compra", "cobertura_mediana_pares",
                "factor_vs_pares", "mensaje_anomalia",
            ],
        ),
        "proveedores": _safe_records(
            supplier_summary,
            [
                "proveedor", "sucursal", "formatos_actuales", "formatos_recomendados",
                "ajuste_formatos", "lineas_con_ajuste",
            ],
        ),
        "redistribucion_interna": _safe_records(
            redistribution if redistribution is not None else pd.DataFrame(),
            [
                "nombre", "unidad_base", "formato_compra", "sucursal_origen",
                "sucursal_destino", "tipo_origen", "viabilidad",
                "cantidad_transferir", "formatos_evitados_incrementales",
                "accion_recomendada",
            ],
        ),
    }
    return context


def context_to_prompt(context: dict[str, Any]) -> str:
    """Serializa el snapshot para entregarlo al modelo sin datos ajenos al dashboard."""
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"), default=str)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _find_named_rows(question: str, analysis: pd.DataFrame) -> pd.DataFrame:
    if analysis is None or analysis.empty:
        return pd.DataFrame()
    q = _normalise(question)
    mask = pd.Series(False, index=analysis.index)
    for column in ("sucursal", "nombre", "ingrediente_id", "proveedor"):
        if column not in analysis.columns:
            continue
        values = analysis[column].dropna().astype(str).unique().tolist()
        for value in values:
            if _normalise(value) in q:
                mask |= analysis[column].astype("string").eq(value)
    return analysis.loc[mask]


def answer_locally(
    question: str,
    analysis: pd.DataFrame,
    anomalies: pd.DataFrame,
    supplier_summary: pd.DataFrame,
    redistribution: pd.DataFrame | None = None,
) -> ChatResponse:
    """Fallback determinista para que PizzIA siga siendo demostrable sin API key."""
    q = _normalise(question)
    if analysis is None or analysis.empty:
        return ChatResponse("Todavía no hay un análisis disponible para responder esa pregunta.", "local")

    alerts = analysis.loc[~analysis["estado"].eq("CORRECTO")].copy()

    if any(term in q for term in ("mas alert", "más alert", "mayor riesgo", "mas riesgo", "más riesgo")):
        counts = alerts.groupby("sucursal").size().sort_values(ascending=False)
        if counts.empty:
            return ChatResponse("La orden activa no tiene alertas pendientes.", "local")
        branch = str(counts.index[0])
        count = int(counts.iloc[0])
        return ChatResponse(f"{branch} es la sucursal con más alertas en la orden activa: {count} línea(s) para revisar.", "local")

    if "anom" in q or "rara" in q or "atip" in q:
        if anomalies is None or anomalies.empty:
            return ChatResponse("No se detectan coberturas atípicas entre sucursales con la orden activa.", "local")
        top = anomalies.iloc[0]
        return ChatResponse(
            f"Se detectan {len(anomalies)} anomalía(s). La más destacada es {top['sucursal']} · {top['nombre']}: "
            f"{top['cobertura_post_compra']:.2f} semanas de cobertura frente a {top['cobertura_mediana_pares']:.2f} "
            "semanas como referencia de las otras sucursales.",
            "local",
        )

    if any(term in q for term in ("redistrib", "transfer", "traslad", "mover", "mueve")):
        if redistribution is None or redistribution.empty:
            return ChatResponse(
                "Con la orden activa no hay redistribuciones internas que permitan evitar formatos adicionales de compra.",
                "local",
            )
        avoided = int(pd.to_numeric(redistribution.get("formatos_evitados_incrementales"), errors="coerce").fillna(0).sum())
        first = redistribution.iloc[0]
        return ChatResponse(
            f"Hay {len(redistribution)} traslado(s) sugerido(s) en la red que, en conjunto, pueden evitar {avoided} formato(s) adicional(es). "
            f"Un ejemplo es mover {float(first['cantidad_transferir']):.2f} {first['unidad_base']} de {first['nombre']} "
            f"desde {first['sucursal_origen']} hacia {first['sucursal_destino']}.",
            "local",
        )

    if "proveedor" in q and any(term in q for term in ("ajuste", "cambio", "correg")):
        if supplier_summary is None or supplier_summary.empty:
            return ChatResponse("No hay resumen de proveedores disponible.", "local")
        work = supplier_summary.copy()
        if "ajuste_formatos" in work.columns:
            work["magnitud"] = pd.to_numeric(work["ajuste_formatos"], errors="coerce").abs()
            totals = work.groupby("proveedor")["magnitud"].sum().sort_values(ascending=False)
            if not totals.empty:
                return ChatResponse(
                    f"{totals.index[0]} concentra la mayor magnitud de ajustes en la orden activa: {totals.iloc[0]:.0f} formato(s).",
                    "local",
                )

    named = _find_named_rows(question, analysis)
    if not named.empty:
        # Priorizamos una línea con alerta si existe.
        alert_named = named.loc[~named["estado"].eq("CORRECTO")]
        row = alert_named.iloc[0] if not alert_named.empty else named.iloc[0]
        requested = row.get("formatos_solicitados")
        recommended = row.get("formatos_recomendados")
        requested_text = "sin línea de pedido" if pd.isna(requested) else f"{requested:.0f} formato(s)"
        recommended_text = "sin recomendación" if pd.isna(recommended) else f"{recommended:.0f} formato(s)"
        return ChatResponse(
            f"{row['sucursal']} · {row['nombre']}: estado {str(row['estado']).replace('_', ' ').lower()}. "
            f"Pedido actual: {requested_text}; recomendado: {recommended_text}. {row.get('accion_recomendada', '')}",
            "local",
        )

    if "omit" in q:
        omitted = analysis.loc[analysis["estado"].eq("OMITIDO")]
        if omitted.empty:
            return ChatResponse("No hay líneas omitidas en la orden activa.", "local")
        items = "; ".join(f"{r.sucursal} · {r.nombre}" for r in omitted.itertuples())
        return ChatResponse(f"Hay {len(omitted)} línea(s) omitida(s): {items}.", "local")

    return ChatResponse(
        "Puedo ayudarte con alertas, sucursales, ingredientes, proveedores, pronósticos, anomalías y redistribución interna. "
        "Para preguntas abiertas en lenguaje natural, configura la clave de IA de PizzIA.",
        "local",
    )


def ask_gemini(
    api_key: str,
    question: str,
    context: dict[str, Any],
    *,
    history: list[dict[str, str]] | None = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 75,
) -> ChatResponse:
    """Pregunta a Gemini usando únicamente el snapshot actual como fuente de verdad."""
    if not api_key.strip():
        raise ValueError("La API key está vacía.")

    history_text = ""
    if history:
        recent = history[-6:]
        history_text = "\n".join(
            f"{item.get('role', 'usuario')}: {item.get('content', '')}" for item in recent
        )

    system_instruction = (
        "Eres PizzIA, asistente de compras de Barrio Pizza. Responde en español claro, breve y profesional. "
        "Tu única fuente de verdad es el CONTEXTO DEL DASHBOARD que recibes. Nunca inventes cifras, sucursales, "
        "ingredientes ni causas que no estén en ese contexto. Si una respuesta no se puede determinar, dilo. "
        "Prioriza decisiones accionables: qué sucede, dónde, con qué producto, cifras relevantes y qué revisar. "
        "Distingue entre alertas de compra, anomalías comparativas y oportunidades de redistribución interna. "
        "No menciones fases internas de desarrollo."
    )
    prompt = (
        f"CONTEXTO DEL DASHBOARD:\n{context_to_prompt(context)}\n\n"
        f"CONVERSACIÓN RECIENTE:\n{history_text or '(sin historial)'}\n\n"
        f"PREGUNTA DEL USUARIO:\n{question}"
    )

    body = json.dumps(
        {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 450,
            },
        }
    ).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )

    payload = None

    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except TimeoutError as exc:
            if attempt == 0:
                time.sleep(1.5)
                continue
            raise RuntimeError(
                "Gemini tardó demasiado en responder después de 2 intentos."
            ) from exc
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"La API de PizzIA respondió con HTTP {exc.code}: {detail[:240]}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"No fue posible conectar con el servicio de IA: {exc.reason}"
            ) from exc

    if payload is None:
        raise RuntimeError("No fue posible obtener una respuesta de Gemini.")

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("El modelo no devolvió una respuesta utilizable.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(str(part.get("text", "")) for part in parts if part.get("text")).strip()
    if not text:
        raise RuntimeError("El modelo devolvió una respuesta vacía.")
    return ChatResponse(text=text, mode="gemini", model=model)
