# Fase 3 explicada: necesidad real y motor de alertas

## 1. ¿Qué problema resolvemos ahora?

En la Fase 2 estimamos cuánto consumirá cada sucursal en la próxima semana. Sin embargo, esa proyección no es igual a lo que debemos comprar, porque la sucursal ya tiene productos en inventario.

La Fase 3 responde tres preguntas:

1. ¿Cuánto hace falta realmente después de usar el inventario actual?
2. ¿Cuántos sacos, cajas, paquetes o unidades completas deben comprarse?
3. ¿La orden enviada por la sucursal es correcta, insuficiente, excesiva o está incompleta?

## 2. Primer cálculo: necesidad real

La fórmula es:

```text
Necesidad real = máximo(consumo proyectado - inventario actual, 0)
```

Usamos `máximo(..., 0)` porque una compra nunca puede ser negativa.

### Ejemplo

```text
Consumo proyectado: 100 kg
Inventario actual:   10 kg
Necesidad real:      90 kg
```

El cálculo es:

```text
100 - 10 = 90 kg
```

Si el inventario fuera de 120 kg:

```text
100 - 120 = -20 kg
```

La necesidad se convierte en cero:

```text
máximo(-20, 0) = 0 kg
```

Eso significa que no se necesita comprar esa semana.

## 3. Segundo cálculo: formatos completos

Los productos no siempre se compran por kg sueltos. Por ejemplo, la harina se compra en sacos de 25 kg.

La fórmula es:

```text
Formatos recomendados = redondear hacia arriba(
    necesidad real / cantidad por formato
)
```

Para 90 kg de necesidad y sacos de 25 kg:

```text
90 / 25 = 3.6
```

No se pueden comprar 3.6 sacos, así que redondeamos hacia arriba:

```text
Formatos recomendados = 4 sacos
Cantidad comprada = 4 × 25 = 100 kg
```

Sobran 10 kg, pero ese sobrante es normal porque se produce por comprar formatos completos.

## 4. Regla de redondeo del reto

Un pedido es correcto cuando solicita exactamente los formatos recomendados, aunque la cantidad comprada supere un poco la necesidad real.

Ejemplo:

```text
Necesidad real:       90 kg
Formato:               25 kg
Formatos recomendados: 4
Cantidad recomendada: 100 kg
```

Resultados posibles:

```text
3 sacos = 75 kg  → FALTANTE
4 sacos = 100 kg → CORRECTO
5 sacos = 125 kg → SOBREPEDIDO
```

El quinto saco representa un formato completo adicional y por eso sí es sobrepedido.

## 5. Estados generados

### `CORRECTO`

La sucursal pide exactamente los formatos recomendados. También se usa cuando no hace falta comprar y no existe una línea de pedido innecesaria.

### `FALTANTE`

La orden existe, pero solicita menos formatos que los recomendados. Puede provocar un quiebre de inventario durante el servicio.

### `OMITIDO`

La sucursal necesita comprar el ingrediente, pero no lo incluyó en su orden.

Una línea ausente no se marca automáticamente como omitida: primero se comprueba que la necesidad real sea mayor que cero.

### `SOBREPEDIDO`

La sucursal solicita más formatos completos que los recomendados. Puede provocar sobrestock, dinero inmovilizado o vencimiento de productos.

### `DATO_INVALIDO`

La línea no puede evaluarse con seguridad. Algunos ejemplos:

- ingrediente que no existe en el catálogo;
- línea sin histórico para proyectar;
- formato de compra inválido;
- número faltante;
- cantidad fraccionaria de formatos.

## 6. Archivo principal: `src/purchase_analysis.py`

La función principal es:

```python
analyze_orders(data, forecast)
```

Recibe:

- los cuatro conjuntos de datos ya validados;
- la proyección creada en la Fase 2.

Después une las tablas mediante:

```text
sucursal + ingrediente_id
```

Así obtiene en una sola fila:

- consumo proyectado;
- inventario actual;
- tamaño del formato;
- cantidad solicitada;
- proveedor y nombre del ingrediente.

Finalmente calcula la recomendación, asigna el estado y redacta un mensaje entendible.

## 7. ¿Qué significa `ceil`?

`ceil` significa redondear hacia arriba.

```text
ceil(3.1) = 4
ceil(3.6) = 4
ceil(4.0) = 4
```

En Python se importa desde `math`:

```python
from math import ceil
```

Es justo lo que necesitamos para formatos completos.

## 8. Pruebas automáticas

El archivo `tests/test_purchase_analysis.py` comprueba:

- redondeo normal sin falso sobrepedido;
- pedido insuficiente;
- formato completo adicional;
- línea omitida;
- inventario que ya cubre la proyección;
- necesidad que es múltiplo exacto del formato;
- ingrediente desconocido;
- resumen de estados.

Con esta fase, el proyecto tiene 19 pruebas automáticas.

## 9. Qué verás en el dashboard

La nueva pestaña **Análisis de órdenes** incluye:

- filtros por sucursal y estado;
- tabla con proyección, inventario y necesidad;
- formatos pedidos y recomendados;
- acción recomendada;
- selector para explicar un cálculo paso a paso;
- mensaje de alerta en lenguaje natural.

## 10. Qué viene después

La Fase 4 no cambiará las fórmulas principales. Se concentrará en convertir los resultados en un dashboard ejecutivo:

- mejor jerarquía visual;
- filtros por proveedor y prioridad;
- tarjetas más útiles;
- alertas destacadas;
- pedido corregido;
- descarga de resultados.
