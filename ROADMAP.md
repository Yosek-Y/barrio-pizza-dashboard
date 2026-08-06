# Plan de trabajo por fases

## Fase 0 — Repositorio y entorno ✅

**Objetivo:** dejar una base reproducible y ordenada.

Entregables:
- Repositorio Git con rama `main`.
- Estructura modular.
- Entorno virtual y dependencias.
- Script para obtener los CSV originales.
- Configuración inicial de Streamlit y Pytest.

**Terminado cuando:** otra persona puede clonar el proyecto, instalarlo y abrir la pantalla inicial siguiendo el README.

## Fase 1 — Carga y validación de datos ✅

**Objetivo:** leer los cuatro CSV sin depender de tablas crudas ni asumir que los datos son perfectos.

Entregables:
- Carga centralizada de archivos.
- Verificación de columnas obligatorias.
- Conversión de columnas numéricas.
- Detección de duplicados, nulos, valores negativos e ingredientes desconocidos.
- Pruebas unitarias de validación.

**Estado:** implementada y cubierta por pruebas unitarias.

**Terminado cuando:** el sistema carga los datos oficiales y reporta claramente cualquier problema sin cerrarse.

## Fase 2 — Proyección base de consumo ✅

**Objetivo:** proyectar la semana siguiente de manera transparente.

Entregables:
- Promedio histórico de seis semanas como modelo base.
- Resultado por sucursal e ingrediente.
- Manejo de históricos incompletos.
- Pruebas con casos conocidos.

**Estado:** implementada y cubierta por pruebas unitarias.

**Terminado cuando:** cada combinación válida tiene una proyección reproducible y explicable.

## Fase 3 — Necesidad real y motor de alertas

**Objetivo:** resolver correctamente la lógica principal del reto.

Entregables:
- Necesidad real = proyección − inventario.
- Conversión de formatos de compra a unidad base.
- Cantidad recomendada en formatos completos.
- Estados: correcto, faltante, sobrepedido, omitido y dato inválido.
- Mensajes accionables.
- Pruebas de límites y redondeo.

**Terminado cuando:** las alertas cumplen la regla de que un excedente menor a un formato completo es redondeo normal.

## Fase 4 — Dashboard MVP

**Objetivo:** presentar el análisis para una gerente de compras.

Entregables:
- Resumen ejecutivo.
- Filtros por sucursal, proveedor y estado.
- Tarjetas de indicadores.
- Tabla priorizada de alertas.
- Detalle por ingrediente y gráfico histórico.
- Pedido corregido descargable.

**Terminado cuando:** una persona no técnica puede identificar qué debe corregir sin leer código.

## Fase 5 — Calidad y pruebas integrales

**Objetivo:** evitar regresiones antes de añadir extras.

Entregables:
- Suite de pruebas.
- Validación manual de anomalías intencionales.
- Revisión de cálculos y unidades.
- Prueba en Windows y navegador.

**Terminado cuando:** la aplicación funciona con los datos originales y los casos problemáticos están documentados.

## Fase 6 — Publicación y entrega

**Objetivo:** dejar una entrega evaluable y fácil de ejecutar.

Entregables:
- README definitivo.
- Despliegue en Streamlit Community Cloud.
- Prueba en incógnito.
- Guion y video de 3–5 minutos.
- Explicación del uso de IA y propuesta de integración con Odoo.

**Terminado cuando:** repositorio, app y video son públicos mediante enlace y funcionan sin permisos especiales.

## Fase 7 — Extras por iteraciones

Cada extra se desarrolla en una rama independiente y se integra solo si no rompe el MVP.

Prioridad sugerida:
1. Proyección robusta que detecte tendencia y valores atípicos.
2. Editor o carga de órdenes desde la interfaz.
3. Pedido corregido agrupado por proveedor.
4. Detección comparativa entre sucursales.
5. Chat con los datos.
6. Ideas adicionales de optimización y experiencia de usuario.
