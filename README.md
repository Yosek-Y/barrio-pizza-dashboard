# Barrio Pizza · AI Purchasing Dashboard

Dashboard administrativo construido para el reto técnico de Práctica de IA de **Barrio Pizza**. La herramienta revisa automáticamente la orden de compra semanal de cada sucursal, proyecta el consumo de la siguiente semana, considera el inventario disponible y convierte el resultado a formatos completos de compra para detectar faltantes, omisiones, sobrepedidos y datos inválidos.

Además del alcance mínimo, el proyecto incorpora pronóstico adaptativo, edición de órdenes en vivo, anomalías entre sucursales, un asistente conversacional conectado a los datos y una propuesta original de redistribución interna antes de comprar más.

> **Estado:** versión funcional lista para despliegue. El enlace público debe agregarse aquí después de publicar y verificar la app en una ventana de incógnito.

---

## 1. Demo y enlaces

- **App en vivo:** `PENDIENTE_DE_DEPLOY`
- **Repositorio GitHub:** `PENDIENTE_DE_LINK_PUBLICO`
- **Video demo (3–5 min):** `PENDIENTE_DE_VIDEO`
- **Reto original:** https://github.com/soydelbarrio/reto-practicante-ia

---

## 2. Qué resuelve

La gerente de compras no debería tener que revisar producto por producto para decidir si una orden está bien. Este dashboard transforma los cuatro CSV del reto en una revisión operativa completa:

1. valida catálogo, histórico, inventario y orden activa;
2. proyecta el consumo de la próxima semana por sucursal e ingrediente;
3. calcula la necesidad real descontando inventario;
4. convierte esa necesidad a formatos completos de compra;
5. compara la recomendación con la orden semanal;
6. clasifica cada línea y genera una acción concreta;
7. permite corregir la orden y recalcular todo sin reiniciar la aplicación;
8. detecta comportamientos atípicos entre sucursales;
9. busca oportunidades de redistribución interna antes de incrementar compras;
10. permite consultar el estado actual mediante **PizzIA**.

### Fórmulas principales

```text
necesidad_real = max(consumo_proyectado - inventario_actual, 0)
```

```text
formatos_recomendados = ceil(necesidad_real / unidad_base_por_formato)
```

La orden está expresada en **formatos completos**, mientras que consumo e inventario están en la **unidad base** del ingrediente. La conversión se realiza antes de comparar cantidades.

---

## 3. Estados de revisión

| Estado | Significado |
| --- | --- |
| `CORRECTO` | La orden cubre la necesidad dentro del redondeo normal del formato. |
| `FALTANTE` | Se solicitaron menos formatos de los necesarios. |
| `OMITIDO` | Existe necesidad proyectada, pero el ingrediente no aparece en la orden. |
| `SOBREPEDIDO` | Se pidió al menos un formato completo adicional frente a la recomendación. |
| `DATO_INVALIDO` | La línea no puede evaluarse de forma segura, por ejemplo por un ingrediente fuera del catálogo. |

### Regla de redondeo

Un sobrante menor a un formato completo **no se marca como sobrepedido**.

Ejemplo:

```text
Necesidad real: 244 kg
Formato: saco de 25 kg
Recomendación: ceil(244 / 25) = 10 sacos = 250 kg
Sobrante: 6 kg
Estado: CORRECTO
```

Ese sobrante puede ser normal para la sucursal y, al mismo tiempo, convertirse en una oportunidad de redistribución a nivel de red.

---

## 4. Funcionalidades del dashboard

### Resumen

Vista ejecutiva con indicadores globales, calidad de datos, distribución de estados y tarjetas de prioridades. Los accesos llevan directamente a las líneas que requieren revisión.

### Órdenes

Permite filtrar y revisar la orden activa, ver el detalle de cada línea y entender por qué fue clasificada como correcta o problemática.

También incluye un espacio de trabajo para:

- subir un CSV de orden semanal;
- editar cantidades directamente en la interfaz;
- agregar o eliminar líneas;
- recalcular todo el análisis;
- descargar la orden activa;
- restaurar los CSV oficiales.

Los cambios viven en la sesión de Streamlit y **no sobrescriben** los archivos oficiales de `/datos`.

### Recomendado

Compara la orden actual con la orden calculada por el motor, resume ajustes y permite exportar tanto el pedido corregido como una agrupación por proveedor.

### Redistribución

Analiza la red completa antes de sugerir compras adicionales. Busca sucursales con excedente seguro del mismo ingrediente y propone movimientos que permitan evitar al menos un formato adicional de compra.

### Pronóstico

Muestra las seis semanas de histórico, la proyección siguiente, el promedio simple de referencia, el método seleccionado, el ajuste, los outliers detectados y el nivel de confianza.

### Anomalías

Compara la cobertura post-compra de cada sucursal contra la mediana de las otras sucursales para el mismo ingrediente. Así detecta coberturas demasiado altas o demasiado bajas incluso cuando una línea aislada parece razonable.

### Datos

Incluye los hallazgos de validación y acceso filtrable a los cuatro datasets para facilitar trazabilidad.

### PizzIA · Pregúntale al Barrio

Asistente flotante disponible desde cualquier sección. Usa el estado actual del dashboard —incluyendo la orden activa, alertas, pronósticos, proveedores, anomalías y redistribución— para responder preguntas operativas en lenguaje natural.

---

## 5. Extras implementados

### 5.1 Pronóstico inteligente

El promedio simple se conserva como línea base, pero el motor selecciona automáticamente una estrategia más adecuada para cada combinación sucursal–ingrediente:

```text
si existe una semana claramente atípica → promedio robusto sin el outlier
si existe una tendencia fuerte y consistente → tendencia lineal
si el histórico es estable → promedio histórico
```

La detección de outliers utiliza mediana y MAD mediante z-score modificado. La tendencia solo se utiliza cuando hay suficiente consistencia para evitar sobreajuste con un histórico tan corto.

#### Ejemplo: Marbella / Pepperoni

```text
Histórico: 28, 30, 150, 27, 29, 31 kg
Promedio simple: 49.17 kg
Pronóstico adaptativo: 29.00 kg
Método: promedio robusto · atípicos excluidos
Outliers: 1
```

La semana de 150 kg no arrastra artificialmente la compra siguiente.

#### Ejemplo: Costa del Este / Harina

```text
Histórico: 240, 255, 268, 284, 300, 316 kg
Promedio simple: 277.17 kg
Pronóstico adaptativo: ~330.27 kg
Método: tendencia lineal
```

Aquí sí existe crecimiento consistente, por lo que mantener solo el promedio habría subestimado la siguiente semana.

#### Cómo verlo

Abrir **Pronóstico**, elegir la sucursal y el ingrediente, y comparar `Base simple`, `Pronóstico`, `Ajuste`, `Método`, `Atípicos` y `Confianza`.

---

### 5.2 Carga y edición dinámica de órdenes

La orden ya no es estática. Puede reemplazarse mediante CSV o editarse desde la interfaz y todo el pipeline se recalcula inmediatamente.

#### Ejemplo

En los datos oficiales:

- cambiar **Brisas del Golf / cebolla** de 5 a 2 formatos elimina el sobrepedido;
- agregar **Brisas del Golf / mozzarella** con la cantidad recomendada elimina la omisión.

Después de aplicar los cambios se actualizan alertas, recomendación, anomalías, redistribución y contexto de PizzIA.

#### Cómo verlo

Abrir **Órdenes → Gestionar orden semanal** y usar la carga CSV o el editor integrado.

Formato esperado:

```csv
sucursal,ingrediente_id,cantidad_formatos
Brisas del Golf,mozzarella,18
```

---

### 5.3 Detección de anomalías entre sucursales

La métrica usada es la cobertura post-compra:

```text
cobertura = (inventario_actual + cantidad_pedida_en_unidad_base) / consumo_proyectado
```

Cada sucursal se compara contra la **mediana de las otras sucursales**, sin incluirse a sí misma en la referencia.

Con los datos oficiales se detectan, entre otros, estos casos:

- **Vía Argentina / Albahaca:** cobertura muy superior al comportamiento de sus pares;
- **Brisas del Golf / Cebolla:** cobertura alta;
- **Costa del Este / Harina:** cobertura baja;
- **Brisas del Golf / Mozzarella:** cobertura muy baja por la omisión en la orden.

#### Cómo verlo

Abrir **Anomalías** y filtrar por sucursal, tipo o ingrediente. La vista muestra cobertura propia, mediana de pares, factor de diferencia, severidad y acción sugerida.

---

### 5.4 PizzIA · chat con los datos

PizzIA tiene dos modos:

**Gemini.** Si existe `GEMINI_API_KEY`, envía a Gemini un snapshot estructurado del estado actual del dashboard. El prompt del sistema le indica que su única fuente de verdad son esos datos y que debe reconocer cuando una respuesta no puede determinarse.

**Fallback local.** Si el servicio generativo no está disponible o tarda demasiado, el dashboard continúa funcionando y responde un conjunto de consultas operativas mediante lógica local. Se realizan hasta dos intentos para la llamada generativa antes de activar el fallback.

Ejemplos de preguntas:

```text
¿Qué sucursal tiene mayor riesgo de quedarse sin producto esta semana?
¿Qué pasa con la mozzarella de Brisas del Golf?
¿Qué anomalías detectaste?
¿Qué puedo redistribuir antes de comprar?
Si solo puedo revisar dos cosas, ¿qué debería priorizar?
```

Cuando la orden activa cambia, el contexto conversacional operativo se reconstruye para evitar responder con resultados obsoletos.

#### Configuración local

Crear `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "TU_CLAVE"
PIZZIA_MODEL = "gemini-3.1-flash-lite"
```

`secrets.toml` está excluido por `.gitignore` y no debe subirse al repositorio.

---

### 5.5 Redistribución inteligente entre sucursales

Esta funcionalidad fue agregada como optimización original: **antes de comprar más al proveedor, revisar si la red ya tendrá suficiente producto en otra sucursal**.

Para cada línea se calcula:

```text
balance_post_orden = inventario_actual + pedido_activo - consumo_proyectado
```

- balance positivo → excedente seguro potencial;
- balance negativo → déficit que aún quedaría después de recibir la orden.

El motor nunca toma producto que la sucursal donante necesita para cubrir su propio pronóstico. Solo relaciona el mismo ingrediente y solo conserva propuestas que eviten al menos un formato adicional de compra.

Además distingue el origen del excedente:

- `INVENTARIO_EXCEDENTE`: producto que ya está físicamente disponible;
- `REASIGNAR_PEDIDO`: formatos de la orden que podrían redirigirse antes de recibirlos;
- `REDONDEO_FORMATO`: sobrante normal creado por comprar formatos completos.

#### Resultado con los datos oficiales

El motor encuentra oportunidades sobre **harina** y **mozzarella** que permiten evitar **3 formatos adicionales** de compra en total.

Ejemplos:

```text
Costa del Este / Harina
Formatos adicionales antes del balance: 7
Después de redistribuir excedentes seguros: 5
Ahorro potencial: 2 sacos
```

```text
Brisas del Golf / Mozzarella
Formatos adicionales antes del balance: 18
Después de redistribuir excedentes seguros: 17
Ahorro potencial: 1 caja
```

La propuesta es operativa y **no ejecuta movimientos automáticamente**. En producción se deberían confirmar restricciones logísticas, inocuidad, lotes, vencimientos y costo de traslado antes de aprobar un movimiento físico.

#### Cómo verlo

Abrir **Redistribución**. La pantalla incluye KPIs, comparación antes/después, plan sugerido de movimientos, impacto por sucursal receptora y exportación CSV.

---

## 6. Casos intencionales de los datos oficiales

El chequeo integral protege explícitamente los casos incluidos en el reto:

| Caso | Resultado esperado |
| --- | --- |
| Brisas del Golf / mozzarella omitida | `OMITIDO` |
| Costa del Este / `aji_chombo` fuera del catálogo | `DATO_INVALIDO` |
| Costa del Este / harina en crecimiento | `FALTANTE` |
| Marbella / pepperoni con semana atípica | `CORRECTO` con pronóstico robusto |
| Brisas del Golf / cebolla | `SOBREPEDIDO` |
| Vía Argentina / albahaca | `SOBREPEDIDO` |

Con la orden oficial, el resultado global actual es:

```text
CORRECTO      84
FALTANTE       1
SOBREPEDIDO    2
DATO_INVALIDO  1
OMITIDO         1
```

---

## 7. Validación y calidad de datos

El sistema no asume que los CSV son perfectos. Antes de analizarlos verifica, entre otros puntos:

- columnas obligatorias;
- valores requeridos;
- tipos numéricos;
- negativos;
- duplicados;
- formatos de compra válidos;
- ingredientes fuera del catálogo;
- histórico incompleto;
- inventario faltante;
- líneas históricamente necesarias omitidas en la orden.

Un problema de datos se conserva como hallazgo visible; no se elimina silenciosamente para hacer que los resultados parezcan correctos.

---

## 8. Arquitectura

```text
CSV / orden editada
       │
       ▼
Data Loader
       │
       ▼
Validaciones
       │
       ▼
Pronóstico inteligente
       │
       ▼
Análisis de compra
       ├──────────────► Orden recomendada / proveedores
       │
       ├──────────────► Anomalías entre sucursales
       │
       ├──────────────► Redistribución interna
       │
       └──────────────► Contexto estructurado de PizzIA
                              │
                              ├── Gemini
                              └── fallback local
```

### Módulos principales

```text
src/data_loader.py           carga y normalización de CSV
src/validations.py           controles de calidad e integridad
src/forecasting.py           promedio base y pronóstico adaptativo
src/purchase_analysis.py     necesidad, formatos, estados y acciones
src/order_workspace.py       carga/edición de la orden activa
src/anomaly_detection.py     comparación robusta entre sucursales
src/redistribution.py        optimización de movimientos internos
src/data_chat.py              contexto y respuestas de PizzIA
app.py                        interfaz Streamlit y navegación
```

---

## 9. Supuestos y decisiones

1. Las seis semanas disponibles son el horizonte histórico entregado y se utilizan como señal para la semana siguiente.
2. Si falta histórico, el sistema reduce la confianza en lugar de inventar observaciones.
3. Consumo e inventario se interpretan en la unidad base definida por el catálogo.
4. `cantidad_formatos` representa formatos completos, nunca unidades base.
5. Una necesidad negativa se lleva a cero: no se recomienda una compra negativa.
6. Un ingrediente desconocido se mantiene como `DATO_INVALIDO` y no detiene el análisis del resto de la orden.
7. Una línea necesaria que no aparece en la orden se clasifica como `OMITIDO`.
8. Solo existe `SOBREPEDIDO` cuando la diferencia alcanza al menos un formato completo adicional; un sobrante menor es redondeo normal.
9. El pronóstico adaptativo prioriza primero la protección ante un outlier claro, luego una tendencia consistente y, en ausencia de ambas, el promedio estable.
10. La redistribución es una recomendación analítica, no una instrucción automática de movimiento físico.

---

## 10. Tecnologías

- Python 3.11+
- Streamlit
- Pandas
- NumPy
- Plotly
- Pytest
- Ruff
- Gemini API para el modo generativo de PizzIA

---

## 11. Instalación local

### Windows / PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_setup.py
python -m pytest
python scripts/run_quality_checks.py
python -m streamlit run app.py
```

Si PowerShell bloquea la activación del entorno virtual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Los CSV oficiales ya se incluyen en `/datos`. `scripts/download_data.py` queda disponible para recuperar los archivos desde la fuente del reto si fuese necesario.

---

## 12. Pruebas

Ejecutar:

```powershell
python -m pytest
```

Estado actual:

```text
49 passed
```

Chequeo integral:

```powershell
python scripts/run_quality_checks.py
```

Resultado esperado:

```text
Errores: 0
Estados oficiales: OK
Casos intencionales: OK
Redistribución interna: 3 formatos evitados / 2 productos
RESULTADO: OK
```

También puede verificarse sintaxis con:

```powershell
python -m compileall -q app.py src
```

---

## 13. Estructura del proyecto

```text
barrio-pizza-ai-dashboard/
├── app.py
├── README.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── .streamlit/
│   └── config.toml
├── assets/
├── datos/
│   ├── ingredientes.csv
│   ├── consumo_historico.csv
│   ├── inventario_actual.csv
│   └── orden_compra_semana.csv
├── scripts/
│   ├── check_setup.py
│   ├── download_data.py
│   └── run_quality_checks.py
├── src/
│   ├── anomaly_detection.py
│   ├── data_chat.py
│   ├── data_loader.py
│   ├── forecasting.py
│   ├── order_workspace.py
│   ├── purchase_analysis.py
│   ├── redistribution.py
│   └── validations.py
└── tests/
    └── test_*.py
```

---

## 14. Cómo conectaría esto con Odoo

No se implementó Odoo porque no es requisito del reto. Para llevar la solución a producción evitaría depender de CSV cargados manualmente y agregaría una capa de integración entre Odoo y el motor analítico.

Flujo propuesto:

```text
Odoo
  │
  ├── catálogo / proveedores
  ├── existencias por sucursal
  ├── movimientos o consumo histórico
  └── borradores de órdenes de compra
          │
          ▼
Servicio de integración
          │
          ├── normaliza IDs y unidades
          ├── ejecuta validaciones
          └── entrega datos al motor actual
                   │
                   ▼
Pronóstico + análisis + anomalías + redistribución
                   │
                   ▼
Dashboard para aprobación humana
                   │
                   ▼
Orden corregida / aprobada
                   │
                   ▼
Servicio de integración → Odoo
```

En una implementación real:

- se usaría la API externa disponible en la instalación de Odoo;
- los IDs de sucursal, producto, proveedor y unidad tendrían un mapeo estable;
- las credenciales vivirían en secretos del entorno, nunca en el repositorio;
- el dashboard propondría cambios, pero la aprobación final seguiría siendo humana;
- solo después de aprobar se actualizarían o crearían borradores de compra en Odoo;
- se registraría auditoría de quién aprobó cada cambio y qué recomendación originó la decisión.

Así el motor desarrollado para el reto podría mantenerse casi sin cambios: el CSV sería reemplazado por un adaptador de entrada/salida hacia Odoo.

---

## 15. Cómo se utilizó IA

El uso de IA se divide en tres partes y se documenta de forma explícita:

### IA durante el desarrollo

Se utilizó **ChatGPT** como asistente de desarrollo para apoyar tareas como diseño de arquitectura, revisión de lógica, depuración, generación y ampliación de pruebas, análisis de casos borde, documentación y refinamiento de la experiencia de usuario. Las decisiones finales se verificaron ejecutando el código contra los datos oficiales y mediante pruebas automatizadas.

### IA dentro del producto

**PizzIA** usa Gemini como capa conversacional. El modelo no recibe acceso libre a archivos ni se utiliza para calcular los estados de compra. Recibe un contexto estructurado generado por el motor determinista y lo transforma en una explicación natural para la gerente de compras.

### Analítica determinista

El pronóstico adaptativo, las reglas de compra, la detección de anomalías y la redistribución se calculan con Python/Pandas/NumPy. No dependen de que un LLM “adivine” cifras. Esta separación permite probar los resultados y mantener trazabilidad.

---

## 16. Seguridad y despliegue

Nunca subir al repositorio:

```text
.streamlit/secrets.toml
.venv/
__pycache__/
.pytest_cache/
.tmp_pytest/
.ruff_cache/
```

Para Streamlit Community Cloud, la clave de Gemini debe configurarse desde la sección de **Secrets** del despliegue, por ejemplo:

```toml
GEMINI_API_KEY = "..."
PIZZIA_MODEL = "gemini-3.1-flash-lite"
```

Antes de entregar, comprobar el enlace público en una ventana de incógnito y verificar al menos:

- carga del Resumen;
- navegación completa;
- edición/carga de una orden;
- Pronóstico;
- Anomalías;
- Redistribución;
- PizzIA;
- descargas CSV.

---

## 17. Fuente de datos

Los cuatro CSV utilizados pertenecen al reto técnico público de Barrio Pizza:

https://github.com/soydelbarrio/reto-practicante-ia

El repositorio del reto indica que el objetivo es proyectar la siguiente semana, descontar inventario, comparar contra la orden y mostrar alertas accionables en un dashboard, además de permitir extras que hagan más útil la herramienta para la gerente de compras.
