# Barrio Pizza AI Dashboard

Dashboard para analizar las órdenes de compra semanales de las sucursales de Barrio Pizza, proyectar el consumo y detectar faltantes, omisiones, sobrepedidos y datos inválidos.

## Estado del proyecto

**Fase 3 — Necesidad real y motor de alertas terminada.**

La aplicación actualmente:

1. carga y valida los cuatro CSV;
2. proyecta S7 mediante el promedio histórico;
3. descuenta el inventario actual;
4. convierte la necesidad a formatos completos;
5. compara la recomendación con la orden semanal;
6. genera un estado, una acción y un mensaje explicativo.

Estados disponibles:

- `CORRECTO`;
- `FALTANTE`;
- `OMITIDO`;
- `SOBREPEDIDO`;
- `DATO_INVALIDO`.

La regla principal de redondeo está implementada: un excedente menor que un formato completo es normal. Solo se considera sobrepedido cuando la sucursal solicita al menos un formato completo adicional frente a la recomendación.

## Tecnologías

- Python
- Streamlit
- Pandas
- Plotly
- Pytest

## Primera instalación en Windows

La guía detallada para principiantes está en [`SETUP_WINDOWS.md`](SETUP_WINDOWS.md).

Resumen desde la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/check_setup.py
python -m pytest
python -m streamlit run app.py
```

## Uso diario en `C:\Proyecto_Barrio_Pizza`

Abrir la carpeta:

```powershell
cd C:\Proyecto_Barrio_Pizza
```

Activar el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ejecutar las pruebas:

```powershell
python -m pytest
```

Ejecutar la aplicación:

```powershell
python -m streamlit run app.py
```

Detener Streamlit:

```text
Ctrl + C
```

## Fórmulas actuales

### Proyección

```text
consumo proyectado S7 = promedio de S1 a S6
```

### Necesidad real

```text
necesidad real = máximo(consumo proyectado - inventario actual, 0)
```

### Formatos recomendados

```text
formatos recomendados = ceil(necesidad real / unidad base por formato)
```

## Estructura

```text
barrio-pizza-ai-dashboard/
├── app.py
├── README.md
├── ROADMAP.md
├── FASE_2_EXPLICADA.md
├── FASE_3_EXPLICADA.md
├── SETUP_WINDOWS.md
├── requirements.txt
├── pyproject.toml
├── datos/
├── scripts/
│   ├── check_setup.py
│   └── download_data.py
├── src/
│   ├── data_loader.py
│   ├── forecasting.py
│   ├── purchase_analysis.py
│   └── validations.py
└── tests/
    ├── test_data_validation.py
    ├── test_forecasting.py
    ├── test_purchase_analysis.py
    └── test_project_structure.py
```

## Pruebas

La Fase 3 incluye 19 pruebas automáticas. Entre otros casos, verifican:

- valores inválidos y negativos;
- ingredientes desconocidos;
- históricos incompletos;
- promedio de seis semanas;
- faltante de compra;
- orden omitida;
- sobrepedido de un formato completo;
- redondeo normal sin falsas alertas.

## Documentación para principiantes

- [`FASE_2_EXPLICADA.md`](FASE_2_EXPLICADA.md): cómo funciona la proyección.
- [`FASE_3_EXPLICADA.md`](FASE_3_EXPLICADA.md): necesidad, formatos y alertas.

## Siguiente fase

La Fase 4 transformará los resultados en un dashboard ejecutivo con mejor jerarquía visual, filtros, prioridades y pedido corregido descargable.

## Fuente de los datos

Los CSV pertenecen al reto técnico público de Barrio Pizza: `soydelbarrio/reto-practicante-ia`.
