# Barrio Pizza AI Dashboard

Dashboard administrativo para revisar las órdenes de compra semanales de Barrio Pizza, proyectar el consumo, considerar el inventario disponible y detectar faltantes, omisiones, sobrepedidos y datos inválidos.

> Este README funciona como documentación central del proyecto y se completará para la entrega final.

## Estado actual

La aplicación actualmente:

1. carga y valida los cuatro CSV del reto;
2. proyecta el consumo de la próxima semana con el promedio histórico disponible;
3. descuenta el inventario actual para calcular la necesidad real;
4. convierte la necesidad a formatos completos de compra;
5. compara la recomendación con la orden semanal;
6. clasifica cada línea como `CORRECTO`, `FALTANTE`, `OMITIDO`, `SOBREPEDIDO` o `DATO_INVALIDO`;
7. muestra el análisis en un dashboard administrativo responsive;
8. permite revisar prioridades, pronósticos, datos fuente y calidad de datos;
9. permite descargar el pedido recomendado y un resumen por proveedor;
10. incluye pruebas automáticas sobre la lógica y los casos intencionales de los datos oficiales.

La regla principal de redondeo está implementada: un excedente menor que un formato completo se considera redondeo normal. Solo se marca sobrepedido cuando se solicita al menos un formato completo adicional frente a la recomendación.

## Tecnologías

- Python
- Streamlit
- Pandas
- Plotly
- Pytest

## Instalación en Windows

Desde la carpeta del proyecto:

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

Si PowerShell bloquea la activación del entorno virtual, puede habilitarse temporalmente para esa consola con:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Uso diario

```powershell
cd C:\Proyecto_Barrio_Pizza
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

Para detener Streamlit:

```text
Ctrl + C
```

## Verificación de calidad

Ejecutar las pruebas automáticas:

```powershell
python -m pytest
```

Ejecutar el chequeo integral de los CSV oficiales:

```powershell
python scripts/run_quality_checks.py
```

Actualmente el proyecto cuenta con **27 pruebas automáticas**.

## Fórmulas principales

### Proyección de consumo

```text
consumo proyectado = promedio del consumo histórico disponible
```

### Necesidad real

```text
necesidad real = max(consumo proyectado - inventario actual, 0)
```

### Formatos recomendados

```text
formatos recomendados = ceil(necesidad real / unidad base por formato)
```

## Estructura principal

```text
barrio-pizza-ai-dashboard/
├── app.py
├── README.md
├── requirements.txt
├── pyproject.toml
├── assets/
├── datos/
├── scripts/
│   ├── check_setup.py
│   ├── download_data.py
│   └── run_quality_checks.py
├── src/
│   ├── data_loader.py
│   ├── forecasting.py
│   ├── purchase_analysis.py
│   └── validations.py
└── tests/
    ├── test_data_validation.py
    ├── test_forecasting.py
    ├── test_integration_official_data.py
    ├── test_phase4_exports.py
    ├── test_project_structure.py
    └── test_purchase_analysis.py
```

## Fuente de los datos

Los CSV utilizados corresponden al reto técnico público de Barrio Pizza, repositorio `soydelbarrio/reto-practicante-ia`.

## Pendiente para la entrega final

Al cerrar el proyecto, este mismo README se ampliará con la arquitectura, decisiones técnicas, uso de IA, integración propuesta con Odoo, despliegue y enlace final del dashboard.
