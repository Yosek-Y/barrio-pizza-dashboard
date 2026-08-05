# Barrio Pizza AI Dashboard

Dashboard para analizar las órdenes de compra semanales de las sucursales de Barrio Pizza, proyectar el consumo y detectar faltantes, omisiones, sobrepedidos y datos inválidos.

## Estado del proyecto

**Fase 0 — Fundación del proyecto.**

La lógica de negocio y el dashboard se construirán por fases, con pruebas antes de agregar funciones opcionales.

## Tecnologías previstas

- Python
- Streamlit
- Pandas
- Plotly
- Pytest

## Preparación inicial

### 1. Crear y activar un entorno virtual

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
python -m venv .venv
.venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Descargar los datos oficiales del reto

```bash
python scripts/download_data.py
```

### 4. Ejecutar el dashboard

```bash
streamlit run app.py
```

### 5. Ejecutar las pruebas

```bash
pytest
```

## Estructura

```text
barrio-pizza-ai-dashboard/
├── app.py
├── README.md
├── ROADMAP.md
├── requirements.txt
├── pyproject.toml
├── datos/
├── scripts/
│   └── download_data.py
├── src/
│   ├── data_loader.py
│   ├── forecasting.py
│   ├── purchase_analysis.py
│   └── validations.py
└── tests/
```

## Fuente de los datos

Los CSV pertenecen al reto técnico público de Barrio Pizza:
`soydelbarrio/reto-practicante-ia`.
