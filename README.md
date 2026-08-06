# Barrio Pizza AI Dashboard

Dashboard para analizar las órdenes de compra semanales de las sucursales de Barrio Pizza, proyectar el consumo y detectar faltantes, omisiones, sobrepedidos y datos inválidos.

## Estado del proyecto

**Fase 2 — Proyección base de consumo terminada.**

La aplicación carga y valida los cuatro CSV y calcula una proyección reproducible de la semana S7 mediante el promedio histórico por sucursal e ingrediente.

Validaciones actuales:

- Archivos y columnas obligatorias.
- Valores vacíos y números inválidos.
- Cantidades negativas.
- Registros duplicados.
- Ingredientes que no existen en el catálogo.
- Históricos con menos o más de seis semanas.
- Inventarios ausentes.
- Combinaciones que no aparecen en la orden semanal.

Funciones de proyección actuales:

- Promedio simple de las semanas disponibles.
- Resultado por sucursal e ingrediente.
- Consumo mínimo, máximo y promedio.
- Marca de histórico completo o incompleto.
- Gráfica de S1–S6 con el punto proyectado de S7.

La siguiente fase calculará la necesidad real, convertirá formatos de compra y generará las alertas del reto.

## Tecnologías

- Python
- Streamlit
- Pandas
- Plotly
- Pytest

## Primera instalación en Windows

La guía detallada para principiantes está en [`SETUP_WINDOWS.md`](SETUP_WINDOWS.md).

Resumen de comandos desde la carpeta del proyecto:

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

## Comandos de uso frecuente

Activar el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ejecutar la aplicación:

```powershell
python -m streamlit run app.py
```

Ejecutar pruebas:

```powershell
python -m pytest
```

Revisar estilo del código:

```powershell
python -m ruff check .
```

## Estructura

```text
barrio-pizza-ai-dashboard/
├── app.py
├── README.md
├── ROADMAP.md
├── FASE_2_EXPLICADA.md
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
    └── test_project_structure.py
```

## Qué debe aparecer con los datos oficiales

La aplicación debe reconocer, entre otros casos:

- Un ingrediente de la orden que no está registrado en el catálogo.
- Una combinación de sucursal e ingrediente que no aparece en la orden semanal.

Estos casos se muestran como advertencias y no hacen que la aplicación se cierre. La pestaña **Proyección S7** permite comprobar el promedio de cada combinación. La Fase 3 determinará si una línea ausente representa realmente un faltante de compra.

Para una explicación orientada a principiantes, consulta [`FASE_2_EXPLICADA.md`](FASE_2_EXPLICADA.md).

## Fuente de los datos

Los CSV pertenecen al reto técnico público de Barrio Pizza:
`soydelbarrio/reto-practicante-ia`.
