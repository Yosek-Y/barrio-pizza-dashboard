"""Dashboard de control inteligente de órdenes de compra de Barrio Pizza."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.data_loader import DATASET_FILES, load_data_bundle
from src.forecasting import build_baseline_forecast, get_history_with_projection
from src.purchase_analysis import analyze_orders
from src.validations import validate_data

st.set_page_config(
    page_title="Barrio Pizza | Control de compras",
    page_icon="🍕",
    layout="wide",
)

st.title("🍕 Control inteligente de órdenes de compra")
st.caption("Reto técnico de IA — Barrio Pizza · Fase 3: necesidad real y alertas")

try:
    data = load_data_bundle()
except (FileNotFoundError, ValueError) as exc:
    st.error("No fue posible cargar los datos del reto.")
    st.code(str(exc), language="text")
    st.markdown("Ejecuta estos comandos desde la carpeta del proyecto:")
    st.code(
        "python scripts/download_data.py\n"
        "python -m streamlit run app.py",
        language="powershell",
    )
    st.stop()

report = validate_data(data)
forecast = None
purchase_analysis = None
if not report.has_errors:
    forecast = build_baseline_forecast(report.cleaned_data)
    purchase_analysis = analyze_orders(report.cleaned_data, forecast)

metric_columns = st.columns(5)
metric_columns[0].metric("Archivos cargados", len(DATASET_FILES))
metric_columns[1].metric("Registros", data.total_rows)
metric_columns[2].metric("Errores de datos", len(report.errors))
metric_columns[3].metric("Advertencias", len(report.warnings))
metric_columns[4].metric(
    "Alertas de compra",
    "—" if purchase_analysis is None else purchase_analysis.alert_count,
)

if report.has_errors:
    st.error(
        "Hay errores de datos que bloquean el análisis. Revísalos en la pestaña Hallazgos."
    )
elif report.warnings:
    st.warning(
        "El análisis pudo calcularse, pero existen situaciones que requieren revisión."
    )
else:
    st.success("Los datos son válidos y las órdenes fueron analizadas correctamente.")

summary_tab, forecast_tab, analysis_tab, issues_tab, data_tab = st.tabs(
    [
        "Resumen",
        "Proyección S7",
        "Análisis de órdenes",
        "Hallazgos",
        "Datos cargados",
    ]
)

with summary_tab:
    st.subheader("Qué hace la Fase 3")
    st.write(
        "La aplicación toma la proyección de S7, descuenta el inventario disponible y "
        "calcula cuántos formatos completos deben comprarse. Después compara esa "
        "recomendación con la orden enviada por cada sucursal."
    )

    formula_left, formula_right = st.columns(2)
    with formula_left:
        st.markdown("#### 1. Necesidad en unidad base")
        st.code(
            "necesidad real = máximo(consumo proyectado - inventario actual, 0)",
            language="text",
        )
        st.caption(
            "Si el inventario ya cubre el consumo esperado, la necesidad de compra es cero."
        )

    with formula_right:
        st.markdown("#### 2. Formatos completos")
        st.code(
            "formatos recomendados = redondear hacia arriba(\n"
            "    necesidad real / unidad base por formato\n"
            ")",
            language="text",
        )
        st.caption("Se redondea hacia arriba porque no existe medio saco o media caja.")

    st.markdown("#### Regla de redondeo del reto")
    st.info(
        "Pedir exactamente los formatos recomendados es correcto, aunque la cantidad "
        "comprada supere un poco la necesidad. Solo existe sobrepedido cuando se agrega "
        "al menos un formato completo adicional."
    )

    if purchase_analysis is not None:
        summary = purchase_analysis.summary()
        result_columns = st.columns(5)
        result_columns[0].metric("Correctos", summary["CORRECTO"])
        result_columns[1].metric("Faltantes", summary["FALTANTE"])
        result_columns[2].metric("Omitidos", summary["OMITIDO"])
        result_columns[3].metric("Sobrepedidos", summary["SOBREPEDIDO"])
        result_columns[4].metric("Datos inválidos", summary["DATO_INVALIDO"])

    st.markdown("#### Qué viene después")
    st.write(
        "La Fase 4 convertirá este motor en un dashboard ejecutivo más visual, con "
        "filtros avanzados, prioridades, una tabla optimizada y un pedido corregido "
        "descargable."
    )

with forecast_tab:
    st.subheader("Consumo proyectado para la próxima semana")

    if forecast is None:
        st.error("La tabla no puede calcularse hasta corregir los errores de datos.")
    elif forecast.projections.empty:
        st.warning("No hay observaciones numéricas suficientes para crear proyecciones.")
    else:
        projections = forecast.projections.copy()
        branch_options = sorted(projections["sucursal"].dropna().unique().tolist())
        selected_branches = st.multiselect(
            "Filtrar sucursales",
            options=branch_options,
            default=branch_options,
            key="forecast_branches",
        )

        filtered = projections.loc[projections["sucursal"].isin(selected_branches)].copy()
        display = filtered.rename(
            columns={
                "sucursal": "Sucursal",
                "nombre": "Ingrediente",
                "proveedor": "Proveedor",
                "unidad_base": "Unidad",
                "semanas_disponibles": "Semanas",
                "consumo_minimo": "Mínimo",
                "consumo_maximo": "Máximo",
                "consumo_promedio": "Promedio",
                "consumo_proyectado": "Proyección S7",
                "historico_completo": "Histórico completo",
            }
        )
        st.dataframe(
            display[
                [
                    "Sucursal",
                    "Ingrediente",
                    "Proveedor",
                    "Unidad",
                    "Semanas",
                    "Mínimo",
                    "Máximo",
                    "Promedio",
                    "Proyección S7",
                    "Histórico completo",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mínimo": st.column_config.NumberColumn(format="%.2f"),
                "Máximo": st.column_config.NumberColumn(format="%.2f"),
                "Promedio": st.column_config.NumberColumn(format="%.2f"),
                "Proyección S7": st.column_config.NumberColumn(format="%.2f"),
                "Histórico completo": st.column_config.CheckboxColumn(),
            },
        )

        st.divider()
        st.subheader("Explicación visual de una proyección")
        chart_left, chart_right = st.columns(2)
        with chart_left:
            selected_branch = st.selectbox(
                "Sucursal",
                options=branch_options,
                key="forecast_detail_branch",
            )
        available_ingredients = projections.loc[
            projections["sucursal"].eq(selected_branch),
            ["ingrediente_id", "nombre"],
        ].drop_duplicates()
        ingredient_labels = {
            row.ingrediente_id: row.nombre
            for row in available_ingredients.itertuples(index=False)
        }
        with chart_right:
            selected_ingredient = st.selectbox(
                "Ingrediente",
                options=list(ingredient_labels),
                format_func=lambda value: ingredient_labels.get(value, value),
                key="forecast_detail_ingredient",
            )

        chart_data = get_history_with_projection(
            report.cleaned_data,
            forecast,
            selected_branch,
            selected_ingredient,
        )
        selected_projection = projections.loc[
            projections["sucursal"].eq(selected_branch)
            & projections["ingrediente_id"].eq(selected_ingredient)
        ].iloc[0]

        figure = go.Figure()
        historical = chart_data.loc[chart_data["tipo"].eq("Histórico")]
        projection_point = chart_data.loc[chart_data["tipo"].eq("Proyección")]
        figure.add_trace(
            go.Scatter(
                x=historical["semana"],
                y=historical["consumo_unidad_base"],
                mode="lines+markers",
                name="Consumo histórico",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=projection_point["semana"],
                y=projection_point["consumo_unidad_base"],
                mode="markers",
                marker={"size": 13, "symbol": "diamond"},
                name="Proyección S7",
            )
        )
        figure.update_layout(
            xaxis_title="Semana",
            yaxis_title=f"Consumo ({selected_projection['unidad_base']})",
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            hovermode="x unified",
        )
        st.plotly_chart(figure, use_container_width=True)

        st.info(
            f"Para **{ingredient_labels[selected_ingredient]}** en **{selected_branch}**, "
            f"el promedio histórico es **{selected_projection['consumo_promedio']:.2f} "
            f"{selected_projection['unidad_base']}**. Por eso la proyección de S7 es "
            "esa misma cantidad."
        )

with analysis_tab:
    st.subheader("Comparación de la orden contra la necesidad real")

    if purchase_analysis is None:
        st.error("El análisis no puede calcularse hasta corregir los errores de datos.")
    elif purchase_analysis.analysis.empty:
        st.warning("No existen combinaciones suficientes para analizar las órdenes.")
    else:
        analysis = purchase_analysis.analysis.copy()
        branch_options = sorted(analysis["sucursal"].dropna().unique().tolist())
        status_options = [
            "DATO_INVALIDO",
            "OMITIDO",
            "FALTANTE",
            "SOBREPEDIDO",
            "CORRECTO",
        ]

        filter_left, filter_right = st.columns(2)
        with filter_left:
            selected_branches = st.multiselect(
                "Sucursales",
                options=branch_options,
                default=branch_options,
                key="analysis_branches",
            )
        with filter_right:
            selected_statuses = st.multiselect(
                "Estados",
                options=status_options,
                default=status_options,
                key="analysis_statuses",
            )

        filtered = analysis.loc[
            analysis["sucursal"].isin(selected_branches)
            & analysis["estado"].isin(selected_statuses)
        ].copy()
        display = filtered.rename(
            columns={
                "prioridad": "Prioridad",
                "estado": "Estado",
                "sucursal": "Sucursal",
                "nombre": "Ingrediente",
                "proveedor": "Proveedor",
                "consumo_proyectado": "Proyección",
                "inventario_actual": "Inventario",
                "necesidad_real": "Necesidad real",
                "formatos_solicitados": "Formatos pedidos",
                "formatos_recomendados": "Formatos recomendados",
                "formato_compra": "Formato",
                "accion_recomendada": "Acción recomendada",
            }
        )
        st.dataframe(
            display[
                [
                    "Prioridad",
                    "Estado",
                    "Sucursal",
                    "Ingrediente",
                    "Proveedor",
                    "Proyección",
                    "Inventario",
                    "Necesidad real",
                    "Formatos pedidos",
                    "Formatos recomendados",
                    "Formato",
                    "Acción recomendada",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Proyección": st.column_config.NumberColumn(format="%.2f"),
                "Inventario": st.column_config.NumberColumn(format="%.2f"),
                "Necesidad real": st.column_config.NumberColumn(format="%.2f"),
                "Formatos pedidos": st.column_config.NumberColumn(format="%.0f"),
                "Formatos recomendados": st.column_config.NumberColumn(format="%.0f"),
            },
        )

        st.divider()
        st.subheader("Entender un cálculo paso a paso")
        detail_options = analysis.index.tolist()
        selected_index = st.selectbox(
            "Selecciona una línea",
            options=detail_options,
            format_func=lambda index: (
                f"{analysis.loc[index, 'sucursal']} · "
                f"{analysis.loc[index, 'nombre']} · {analysis.loc[index, 'estado']}"
            ),
        )
        detail = analysis.loc[selected_index]

        if detail["estado"] == "DATO_INVALIDO":
            st.error(detail["mensaje"])
        else:
            calc_columns = st.columns(4)
            calc_columns[0].metric("Proyección S7", f"{detail['consumo_proyectado']:.2f}")
            calc_columns[1].metric("Inventario", f"{detail['inventario_actual']:.2f}")
            calc_columns[2].metric("Necesidad real", f"{detail['necesidad_real']:.2f}")
            calc_columns[3].metric(
                "Formatos recomendados",
                f"{int(detail['formatos_recomendados'])}",
            )
            st.code(
                f"necesidad real = max({detail['consumo_proyectado']:.2f} "
                f"- {detail['inventario_actual']:.2f}, 0)\n"
                f"necesidad real = {detail['necesidad_real']:.2f} "
                f"{detail['unidad_base']}\n\n"
                f"formatos recomendados = ceil({detail['necesidad_real']:.2f} "
                f"/ {detail['unidad_base_por_formato']:.2f})\n"
                f"formatos recomendados = {int(detail['formatos_recomendados'])}",
                language="text",
            )
            if detail["estado"] == "CORRECTO":
                st.success(detail["mensaje"])
            elif detail["estado"] == "SOBREPEDIDO":
                st.warning(detail["mensaje"])
            else:
                st.error(detail["mensaje"])

with issues_tab:
    st.subheader("Detalle de calidad de datos")
    issue_frame = report.to_dataframe()
    if issue_frame.empty:
        st.success("No se encontraron problemas.")
    else:
        selected_levels = st.multiselect(
            "Filtrar por nivel",
            options=["ERROR", "ADVERTENCIA"],
            default=["ERROR", "ADVERTENCIA"],
        )
        filtered = issue_frame[issue_frame["Nivel"].astype("string").isin(selected_levels)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)

with data_tab:
    st.subheader("Vista previa de los archivos")
    dataset_name = st.selectbox(
        "Selecciona un conjunto de datos",
        options=list(report.cleaned_data.as_dict()),
        format_func=lambda value: value.replace("_", " ").title(),
    )
    selected_frame = report.cleaned_data.as_dict()[dataset_name]
    st.caption(f"{len(selected_frame)} registros · {len(selected_frame.columns)} columnas")
    st.dataframe(selected_frame, use_container_width=True, hide_index=True)
