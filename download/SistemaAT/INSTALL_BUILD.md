# Sistema AT · Guía de compilación (PyInstaller + Inno Setup)

Guía para el personal técnico que deba **compilar el ejecutable portable** de
Sistema AT a partir del código fuente.

---

## 1. Requisitos

| Componente | Versión exacta | Nota |
|---|---|---|
| Windows | 10/11 64 bits | El exe resultante solo sirve para Windows |
| Python | **3.12.x o 3.13.x** | **Prohibido 3.14** (PyInstaller aún no soportado) |
| PyInstaller | ≥ 6.11 | De `requirements-dev.txt` |
| Inno Setup 6 | ≥ 6.3 | Solo si desea el instalador clásico |

> Descarga Python: <https://www.python.org/downloads/> (marque **Add python.exe to PATH**).

## 2. Preparar el entorno

```bat
cd ruta\a\SistemaAT
python -m venv .venv
.venv\Scripts\activate

:: Con internet:
pip install -r requirements.txt -r requirements-dev.txt

:: Sin internet (usar la carpeta wheels\ incluida, wheelhouse para win_amd64):
pip install --no-index --find-links wheels -r requirements.txt -r requirements-dev.txt
```

## 3. Compilar la versión PORTABLE

```bat
python build.py            :: onedir (arranque rápido, recomendado)
python build.py onefile    :: un único SistemaAT.exe
python build.py installer  :: onedir + recordatorio para Inno Setup
python build.py clean      :: limpiar build/dist
```

Salidas:

- `dist\SistemaAT\` — carpeta del programa (onedir, incluye `_internal\`).
- `dist\SistemaAT_Portable_v1.0.zip` — **ZIP portable definitivo** con el
  marcador `PORTABLE` y el `LEEME_PORTABLE.txt` ya incluidos.
  Con el marcador dentro, el exe guarda los datos en `Data\` junto al
  ejecutable (memoria USB incluida).

## 4. (Opcional) Instalador con Inno Setup 6

1. Instale Inno Setup 6: <https://jrsoftware.org/isdl.php>.
2. Abra `installer.iss` con el Inno Setup Compiler.
3. Menú **Build → Compile**.
4. Resultado: `dist_instalador\Instalador_SistemaAT_v1.0.exe`
   - Instala en `%LOCALAPPDATA%\Programs\SistemaAT` **sin permisos de
     administrador** (`PrivilegesRequired=lowest`), interfaz en español,
     acceso directo opcional al escritorio.
   - La desinstalación **no borra** los datos de `%LOCALAPPDATA%\SistemaAT`.

## 5. Verificación posterior a la compilación (checklist)

1. `dist\SistemaAT\SistemaAT.exe` abre la ventana 1400×850 con el panel.
2. Existen las 4 plantillas dentro de `_internal\templates\`.
3. Registrar un deportista → crear AT-F3 → genera Excel en `Data\generados`.
4. Capturar una firma en *Firmas* → volver a generar el AT-F3 → la rúbrica aparece.
5. AT-F8 → AT-F9: el plan se precarga y los promedios AT-F3 se calculan solos.
6. Ejecutar el exe desde una USB: `Data\` se crea junto al exe (portable OK).

## 6. Problemas frecuentes de compilación

| Error | Causa | Solución |
|---|---|---|
| `customtkinter` no encuentra sus temas dentro del exe | Falta `collect_data_files` | Use `sistema_at.spec` tal cual (ya lo incluye) |
| `ModuleNotFoundError: PIL._tkinter_finder` | Hidden import ausente | Ya declarado en el .spec; no lo quite |
| El antivirus borra el exe | Falso positivo por UPX | `upx=False` ya está fijado; excluya la carpeta |
| `precompilation failed` / errores raros | Python 3.14 | Reinstale 3.12/3.13 |
| Tkinter ausente | Instaló el «embeddable package» | Instale el instalador completo de python.org |
