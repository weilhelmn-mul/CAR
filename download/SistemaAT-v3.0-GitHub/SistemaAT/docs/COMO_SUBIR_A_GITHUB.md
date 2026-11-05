# Cómo subir este proyecto a GitHub (paso a paso)

Este archivo acompaña al código fuente del **Sistema AT v3.0**. Elija una de
las dos vías según su comodidad. Ambas producen el mismo resultado.

---

## Vía 1 · Desde la web de GitHub (sin instalar nada)

1. Entre a <https://github.com> e inicie sesión (cree cuenta gratis si no tiene).
2. Pulse el botón **“+”** (arriba a la derecha) → **“New repository”**.
3. Complete:
   - **Repository name:** `SistemaAT` (o el nombre que prefiera).
   - **Description:** `Sistema de Gestión de Formatos AT · IPD - DINADAF (v3.0 con Asistente IA)`.
   - Visibilidad: **Private** (recomendado: contiene plantillas institucionales)
     o **Public** si desea compartirlo.
   - **NO** marque “Add a README”, “Add .gitignore” ni “Choose a license”:
     este paquete ya los incluye.
4. Pulse **“Create repository”**.
5. En la pantalla que aparece, elija el enlace **“uploading an existing file”**.
6. Abra la carpeta `SistemaAT` (esta carpeta), seleccione **todo su contenido**
   (Ctrl+E para mostrar archivos ocultos como `.gitignore`) y **arrastre** los
   archivos y carpetas al navegador.
   - Importante: arrastre el **contenido** de la carpeta, no la carpeta contenedora.
7. Espere a que termine la carga (los `wheels/` pesan ~22 MB) y pulse
   **“Commit changes”**.
8. ¡Listo! Su código está en GitHub. La página principal mostrará el README.

---

## Vía 2 · Con Git en su PC (recomendada si va a mantener el código)

Requisito: instalar [Git for Windows](https://git-scm.com/download/win) (siguiente,
siguiente, finalizar). Luego abra **Git Bash** o **PowerShell** dentro de la carpeta
`SistemaAT` y ejecute, en orden:

```bash
# 1. Iniciar el repositorio local
git init
git branch -M main

# 2. Agregar todos los archivos (respeta .gitignore automáticamente)
git add .
git commit -m "Sistema AT v3.0 - Asistente IA, Alimentación, Seguro, Expediente y Análisis Deportivo"

# 3. Conectar con su repositorio (reemplace USUARIO por su cuenta de GitHub)
git remote add origin https://github.com/USUARIO/SistemaAT.git
git push -u origin main
```

> La primera vez GitHub le pedirá iniciar sesión: use **“Sign in with your browser”**.
> Si el repositorio lo creó con README en la web, use
> `git pull origin main --allow-unrelated-histories` antes del push.

---

## Actualizar el código más adelante

Cada vez que cambie archivos del sistema:

```bash
git add .
git commit -m "Descripción del cambio"
git push
```

## Qué NO se sube (protegido por .gitignore)

- `Data/` y `data/` — su base de datos, firmas y formatos generados.
- `config_ia.json` — la clave de API del Asistente IA (nunca debe publicarse).
- `__pycache__/`, `build/`, `dist/` — artefactos temporales.

## Clonar el proyecto en otra PC

```bash
git clone https://github.com/USUARIO/SistemaAT.git
cd SistemaAT
EJECUTAR_SISTEMA.bat
```

---
*DINADAF · Instituto Peruano del Deporte — 2026*
