# Fase 2 explicada: proyección base de consumo

## 1. ¿Qué problema resolvemos?

Barrio Pizza conoce cuánto consumió cada sucursal durante las semanas S1 a S6, pero necesita estimar cuánto consumirá en S7. Esa estimación se llama **proyección**.

En esta fase todavía no analizamos la orden de compra. Solamente respondemos:

> ¿Cuánto esperamos consumir la próxima semana de cada ingrediente en cada sucursal?

## 2. Modelo utilizado

Usamos el promedio simple:

```text
Proyección S7 = (S1 + S2 + S3 + S4 + S5 + S6) / 6
```

Ejemplo:

```text
Harina consumida: 100, 110, 105, 115, 108 y 112 kg
Suma: 650 kg
Promedio: 650 / 6 = 108.33 kg
Proyección S7: 108.33 kg
```

## 3. ¿Por qué no usamos IA avanzada todavía?

Porque primero necesitamos una referencia sencilla, comprobable y fácil de explicar. Más adelante podremos probar una tendencia lineal, promedio ponderado o detección de valores atípicos y comparar sus resultados contra esta base.

Un modelo más complejo solo será mejor si podemos demostrarlo.

## 4. Archivos involucrados

### `src/forecasting.py`

Contiene la lógica matemática. Su función principal es:

```python
build_baseline_forecast(data)
```

Esta función agrupa las filas por:

```text
sucursal + ingrediente
```

Después calcula:

- semanas disponibles;
- observaciones numéricas válidas;
- consumo mínimo;
- consumo máximo;
- consumo promedio;
- proyección de S7;
- indicador de histórico completo.

### `app.py`

Muestra los resultados sin obligar al usuario a leer código. Incluye:

- resumen de la metodología;
- tabla de proyecciones;
- filtros por sucursal;
- gráfica S1–S6;
- punto proyectado de S7;
- explicación en lenguaje natural.

### `tests/test_forecasting.py`

Comprueba automáticamente que:

- el promedio se calcula bien;
- un histórico incompleto se marca;
- los nombres y unidades se agregan desde el catálogo;
- un grupo sin números válidos no se proyecta;
- la gráfica incluye el punto S7.

## 5. Históricos incompletos

Cuando solo existen, por ejemplo, tres semanas válidas, el sistema calcula el promedio de esas tres semanas, pero marca:

```text
Histórico completo = No
```

Así no perdemos toda la proyección, pero avisamos que tiene menos evidencia.

## 6. Limitación conocida

El promedio simple es sensible a valores atípicos. Si cinco semanas rondan 30 kg y una semana indica 150 kg, el resultado subirá mucho.

En esta fase lo dejamos visible intencionalmente. En los extras podremos detectar o reducir el efecto de estas semanas anormales.

## 7. Qué viene después

En la Fase 3 calcularemos:

```text
Necesidad real = consumo proyectado - inventario actual
```

Luego convertiremos la orden desde formatos completos a unidad base y determinaremos si existe:

- faltante;
- sobrepedido;
- omisión;
- pedido correcto;
- dato inválido.
