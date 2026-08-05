"""Punto de entrada del dashboard de Barrio Pizza."""

import streamlit as st

st.set_page_config(
    page_title="Barrio Pizza | Control de compras",
    page_icon="🍕",
    layout="wide",
)

st.title("🍕 Control inteligente de órdenes de compra")
st.caption("Reto técnico de IA — Barrio Pizza")

st.info(
    "Proyecto inicializado correctamente. La siguiente fase implementará la carga y "
    "validación de los cuatro archivos CSV."
)

left, middle, right = st.columns(3)
left.metric("Fase actual", "0", "Fundación")
middle.metric("Sucursales esperadas", "4")
right.metric("Archivos de entrada", "4")

st.subheader("Ruta de construcción")
st.write(
    "Datos → Proyección → Necesidad real → Alertas → Dashboard → Pruebas → Extras"
)
