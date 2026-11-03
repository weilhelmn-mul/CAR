# INSTALL_BUILD.md · Guía de compilación (desarrolladores)

Esta guía describe cómo preparar el entorno de desarrollo y cómo producir el
**ejecutable** y el **instalador** del Sistema AT en Windows.

---

## 1. Prerrequisitos

| Herramienta | Versión | Notas |
|---|---|---|
| Python | **3.12 o 3.13** | NO usar 3.14 (PyInstaller aún no garantiza compatibilidad). <https://www.python.org/downloads/> |
| PyInstaller | ≥ 6.11 | Se instala con `requirements-dev.txt`. |
| Inno Setup 6 | 6.x | <https://jrsoftware.org/isdl.php> — instalar en la ruta por defecto (`C:\Program Files\Inno Setup 6`). |
| LibreOffice (opcional) | Cualquier 7.x+ | Solo para probar la conversión a PDF en la máquina de desarrollo. |

## 2. Preparar el entorno

```bat
:: 1) Clonar/copy la carpeta del proyecto y entrar
cd atletas_system

:: 2) Entorno virtual con Python 3.12/3.13
py -3.12 -m venv .venv
.venv\Scripts\activate

:: 3) Dependencias de la aplicación + de empaquetado
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 3. Estructura esperada

```
atletas_system\
├── main.py                ← punto de entrada
├── requirements.txt / requirements-dev.txt
├── sistema_at.spec        ← spec de PyInstaller
├── installer.iss          ← script de Inno Setup 6
├── build.py               ← script maestro de compilación
├── assets\icon.ico
├── templates\             ← LAS 4 PLANTILLAS OFICIALES (nombres exactos)
│   ├── PLANTILLA FORMATO AT-F1 CAR.xlsx
│   ├── PLANTILLA FORMATO AT-F3.xlsx
│   ├── PLANTILLA FORMATO ATF8.xlsx
│   └── PLANTILLA FORMATO AT -F9.xlsx
├── data\ firmas\ generados\   (autogeneradas en desarrollo)
└── src\  (config, theme, database, widgets, main_window, views\, services\)
```

Si falta alguna plantilla, `build.py` lo advierte: la app compila, pero no podrá generar ese formato.

## 4. Probar en desarrollo

```bat
python main.py
```

- En desarrollo, los datos se guardan en `data\`, `firmas\` y `generados\` del propio proyecto.
- Se puede compilar un solo formato sin la UI:

```python
# pruebas rápidas con la BD de desarrollo
from src.database import init_db
from src.services.excel import generar_at_f3
init_db()
generar_at_f3(1)   # requiere un registro AT-F3 con id=1 y su plantilla
```

## 5. Compilar ejecutable e instalador

```bat
:: Todo en uno: limpia, compila el exe y genera el instalador
python build.py

:: Solo el ejecutable (distribución portable de la carpeta dist\SistemaAT\)
python build.py --exe-only

:: Limpieza profunda (build/, dist/, installer_output/ y __pycache__)
python build.py --clean
```

Salidas:

| Artefacto | Ruta |
|---|---|
| Ejecutable | `dist\SistemaAT\SistemaAT.exe` |
| Instalador | `installer_output\SistemaAT_Setup_1.0.0.exe` |

`build.py` hace internamente lo equivalente a:

```bat
python -m PyInstaller --clean --noconfirm sistema_at.spec
"C:\Program Files\Inno Setup 6\ISCC.exe" installer.iss
```

## 6. Detalles técnicos del empaquetado

- **Modo onedir, console=False** (app de ventana; los errores quedan en el log).
- `datas` incluye `templates/`, `assets/` y `collect_data_files("customtkinter")` (temas).
- `hiddenimports`: `PIL._tkinter_finder`, `openpyxl`, `openpyxl.drawing.image`.
- En el .exe congelado: plantillas leídas desde el bundle (`sys._MEIPASS/templates`), salvo que exista `templates\` junto al exe (override para actualizar plantillas sin recompilar).
- Datos del usuario siempre en `%LOCALAPPDATA%\SistemaAT\` (persisten entre reinstalaciones).
- `pywin32` solo se instala en Windows (marcador de entorno en `requirements.txt`) y habilita la conversión PDF vía Excel COM como respaldo de LibreOffice.

## 7. Problemas frecuentes de compilación

| Problema | Causa / solución |
|---|---|
| `ModuleNotFoundError: customtkinter` al abrir el exe | Falta `collect_data_files("customtkinter")` en el spec (ya incluido) o se compiló con otro Python sin la librería. |
| El exe abre y se cierra al instante | Ejecute `dist\SistemaAT\SistemaAT.exe` desde `cmd` para ver el traceback, o revise `%LOCALAPPDATA%\SistemaAT\data\sistema_at.log`. |
| “PyInstaller no está instalado” | `pip install -r requirements-dev.txt` dentro del venv. |
| Inno Setup no encontrado | Instálelo en `C:\Program Files\Inno Setup 6` o compile a mano: `ISCC.exe installer.iss`. |
| Antivirus bloquea el exe | Firmar el instalador (certificado de código) o agregar exclusión corporativa. |
| PDF de prueba no se genera | Instale LibreOffice en el equipo de desarrollo, o pruebe solo la generación de Excel. |
