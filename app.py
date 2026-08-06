"""Dashboard de control inteligente de órdenes de compra de Barrio Pizza."""

from __future__ import annotations

import streamlit as st

from src.data_loader import DATASET_FILES, load_data_bundle
from src.validations import validate_data

st.set_page_config(
    page_title="Barrio Pizza | Control de compras",
    page_icon="🍕",
    layout="wide",
)

st.title("🍕 Control inteligente de órdenes de compra")
st.caption("Reto técnico de IA — Barrio Pizza · Fase 1: carga y calidad de datos")

try:
    data = load_data_bundle()
except (FileNotFoundError, ValueError) as exc:
    st.error("No fue posible cargar los datos del reto.")
    st.code(str(exc), language="text")
    st.markdown("Ejecuta estos comandos desde la carpeta del proyecto:")
    st.code(
        "python scripts/download_data.py\n"
        "streamlit run app.py",
        language="powershell",
    )
    st.stop()

report = validate_data(data)

metric_columns = st.columns(4)
metric_columns[0].metric("Archivos cargados", len(DATASET_FILES))
metric_columns[1].metric("Registros", data.total_rows)
metric_columns[2].metric("Errores", len(report.errors))
metric_columns[3].metric("Advertencias", len(report.warnings))

if report.has_errors:
    st.error(
        "Hay errores que deben corregirse antes de calcular proyecciones y órdenes recomendadas."
    )
elif report.warnings:
    st.warning(
        "Los archivos se pueden procesar, pero hay situaciones que requieren revisión."
    )
else:
    st.success("Los cuatro archivos superaron todas las validaciones de la Fase 1.")

summary_tab, issues_tab, data_tab = st.tabs(
    ["Resumen", "Hallazgos", "Datos cargados"]
)

with summary_tab:
    st.subheader("Estado de la Fase 1")
    st.write(
        "La aplicación ya verifica estructura, campos vacíos, números inválidos, "
        "cantidades negativas, duplicados y consistencia entre archivos."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Validaciones implementadas")
        st.markdown(
            "- Columnas y archivos obligatorios\n"
            "- Valores vacíos y formatos numéricos\n"
            "- Cantidades negativas y registros duplicados\n"
            "- Ingredientes que no existen en el catálogo\n"
            "- Históricos incompletos e inventarios ausentes\n"
            "- Líneas omitidas en la orden semanal"
        )

    with right:
        st.markdown("#### Próximo paso")
        st.info(
            "Cuando confirmemos estas validaciones, la Fase 2 calculará el consumo "
            "proyectado de cada ingrediente por sucursal."
        )

    if report.issues:
        st.markdown("#### Hallazgos principales")
        for issue in report.issues[:5]:
            icon = "🛑" if issue.severity == "ERROR" else "⚠️"
            st.write(f"{icon} **{issue.code}** — {issue.message}")

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
