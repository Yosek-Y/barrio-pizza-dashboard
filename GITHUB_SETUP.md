# Crear el repositorio remoto

Nombre recomendado: `barrio-pizza-ai-dashboard`

Configuración en GitHub:
- Propietario: `Yosek-Y`
- Visibilidad: Public
- No agregar README, `.gitignore` ni licencia desde GitHub, porque ya existen localmente.

Después de crear el repositorio vacío, abre una terminal dentro de esta carpeta y ejecuta:

```bash
git remote add origin https://github.com/Yosek-Y/barrio-pizza-ai-dashboard.git
git push -u origin main
```

Para verificar:

```bash
git remote -v
git status
git log --oneline -1
```
