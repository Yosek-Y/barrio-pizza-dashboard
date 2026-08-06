# Preparación del proyecto en Windows

Esta guía está pensada para una persona que nunca ha trabajado con Python.

## 1. Programas necesarios

Instala:

1. **Python 3.11 o superior** desde Python.org.
2. **Visual Studio Code**.
3. La extensión **Python**, publicada por Microsoft, dentro de Visual Studio Code.
4. **Git**, que probablemente ya tienes porque subiste el repositorio.

Después de instalar Python, cierra y vuelve a abrir PowerShell o Visual Studio Code.

## 2. Comprobar Python

Abre la carpeta del proyecto en Visual Studio Code y luego abre:

`Terminal → New Terminal`

Ejecuta:

```powershell
py --version
```

También puedes probar:

```powershell
python --version
```

Debe aparecer Python 3.11 o una versión superior.

## 3. Crear el entorno virtual

El entorno virtual guarda las librerías de este proyecto sin mezclarlas con otros proyectos.

```powershell
py -m venv .venv
```

Actívalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, ejecuta primero:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

La terminal debe comenzar con `(.venv)`.

## 4. Instalar las librerías

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. Descargar los datos del reto

```powershell
python scripts/download_data.py
```

Esto debe crear cuatro CSV dentro de la carpeta `datos`.

## 6. Comprobar toda la instalación

```powershell
python scripts/check_setup.py
```

Cada línea debe mostrar `[OK]`.

## 7. Ejecutar las pruebas

```powershell
python -m pytest
```

El resultado esperado en la Fase 1 es:

```text
5 passed
```

## 8. Abrir el dashboard

```powershell
python -m streamlit run app.py
```

Se abrirá una pestaña del navegador. Para detener el servidor, regresa a la terminal y presiona `Ctrl + C`.

## Rutina para trabajar cada día

Cada vez que abras nuevamente el proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

No necesitas reinstalar las dependencias todos los días.
