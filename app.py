"""Dashboard de control inteligente de órdenes de compra de Barrio Pizza."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.data_loader import DATASET_FILES, load_data_bundle
from src.forecasting import build_baseline_forecast, get_history_with_projection
from src.validations import validate_data

st.set_page_config(
    page_title="Barrio Pizza | Control de compras",
    page_icon="🍕",
    layout="wide",
)

st.title("🍕 Control inteligente de órdenes de compra")
st.caption("Reto técnico de IA — Barrio Pizza · Fase 2: proyección base de consumo")

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
forecast = None if report.has_errors else build_baseline_forecast(report.cleaned_data)

metric_columns = st.columns(4)
metric_columns[0].metric("Archivos cargados", len(DATASET_FILES))
metric_columns[1].metric("Registros", data.total_rows)
metric_columns[2].metric("Errores", len(report.errors))
metric_columns[3].metric("Advertencias", len(report.warnings))

if report.has_errors:
    st.error(
        "Hay errores de datos que bloquean la proyección. Revísalos en la pestaña Hallazgos."
    )
elif report.warnings:
    st.warning(
        "La proyección pudo calcularse, pero existen situaciones que requieren revisión."
    )
else:
    st.success("Los datos son válidos y la proyección base se calculó correctamente.")

summary_tab, forecast_tab, issues_tab, data_tab = st.tabs(
    ["Resumen", "Proyección S7", "Hallazgos", "Datos cargados"]
)

with summary_tab:
    st.subheader("Qué hace la Fase 2")
    st.write(
        "Para cada sucursal e ingrediente, la aplicación suma el consumo válido de "
        "las semanas S1 a S6 y lo divide entre la cantidad de observaciones. Ese "
        "promedio es la proyección de S7."
    )

    st.code(
        "consumo proyectado S7 = (S1 + S2 + S3 + S4 + S5 + S6) / 6",
        language="text",
    )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Por qué empezamos con un promedio")
        st.markdown(
            "- Es transparente y fácil de comprobar.\n"
            "- Nos da una línea base para comparar modelos futuros.\n"
            "- Permite terminar primero la lógica central del negocio.\n"
            "- Evita usar un modelo complejo sin demostrar que mejora el resultado."
        )

    with right:
        st.markdown("#### Limitación importante")
        st.info(
            "Un valor atípico puede alterar mucho el promedio. Por ejemplo, si una "
            "semana tuvo un consumo anormalmente alto, el modelo base lo incluirá. "
            "Eso no es un error de programación: es una limitación conocida que "
            "mejoraremos en los extras."
        )

    if forecast is not None:
        st.markdown("#### Resultado general")
        result_columns = st.columns(4)
        result_columns[0].metric("Proyecciones", forecast.total_projections)
        result_columns[1].metric("Sucursales", forecast.branch_count)
        result_columns[2].metric("Ingredientes", forecast.ingredient_count)
        result_columns[3].metric("Históricos incompletos", forecast.incomplete_count)

    st.markdown("#### Qué todavía no hacemos")
    st.write(
        "Aún no descontamos inventario, no convertimos formatos de compra y no "
        "decidimos si una orden está correcta. Esa será la Fase 3."
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
            selected_branch = st.selectbox("Sucursal", options=branch_options)
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
            f"esa misma cantidad."
        )

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
