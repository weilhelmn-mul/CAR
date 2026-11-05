# Sistema AT · IPD - DINADAF — Guía de instalación y uso

Sistema de gestión de los formatos mensuales **AT-F3, AT-F1, AT-F8 y AT-F9**
de la Dirección Nacional de Deporte Afiliado y Afines (DINADAF) del Instituto
Peruano del Deporte.

---

## Opción A · Versión PORTABLE (recomendada — no requiere instalación)

### A.1 Si ya cuenta con `SistemaAT_Portable_v1.0.zip`

1. Descomprima el ZIP en cualquier carpeta **o en una memoria USB**.
2. Ejecute `SistemaAT.exe` (en el modo *onefile* es un único archivo; en el modo
   *onedir* está dentro de la carpeta `SistemaAT_Portable`).
3. Si Windows SmartScreen muestra un aviso la primera vez:
   **Más información → Ejecutar de todas formas**.

Requisitos del equipo: **Windows 10/11 de 64 bits**. No necesita Python, ni
permisos de administrador, ni instalar nada.

### A.2 Dónde viven sus datos (modo portable)

Junto al ejecutable hay un archivo marcador llamado **`PORTABLE`**:

| Elemento | Ubicación |
|---|---|
| Base de datos SQLite | `Data\sistema_at.db` (junto al exe) |
| Firmas capturadas | `Data\firmas\` |
| Excel generados | `Data\generados\` |
| Registro de eventos | `Data\sistema_at.log` |

- **Respaldo**: copie la carpeta `Data` completa.
- **Mudanza**: copie toda la carpeta del programa (incluido el marcador
  `PORTABLE`) a la nueva ubicación o USB.
- Si elimina el marcador `PORTABLE`, el sistema pasa a modo *instalado* y usa
  `%LOCALAPPDATA%\SistemaAT`.

### A.3 Exportar a PDF (opcional)

- Instale **LibreOffice** (<https://es.libreoffice.org>) — opción gratuita recomendada.
- O bien, si el equipo tiene **Microsoft Excel**, la conversión se hace
  automáticamente vía COM (incluido con `pywin32` en Windows).
- Sin ninguno de los dos, el sistema sigue generando los **Excel** sin problema.

---

## Opción B · Ejecutar desde el código fuente

1. Instale **Python 3.12 o 3.13** desde <https://www.python.org/downloads/>
   (marque *Add python.exe to PATH*). **No use Python 3.14.**
2. En la carpeta del proyecto:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

---

## Flujo de trabajo mensual (resumen)

| Paso | Formato | Carácter | Quién firma |
|---|---|---|---|
| 1 | **AT-F3** por deportista | Retrospectivo (mes cerrado) | Entrenador **o** JUT |
| 2 | **AT-F1** por CAR | Retrospectivo (agrega los AT-F3) | JUT/Rep. DINADAF **+** Entrenador |
| 3 | **AT-F8** plan del JUT | Prospectivo (mes siguiente) | JUT |
| 4 | **AT-F9** evaluación | Retrospectivo (evalúa el AT-F8 del mes anterior, con promedios automáticos del AT-F3) | JUT (+ Presidente FDN solo si opina) |

Los porcentajes se pueden escribir indistintamente como `95`, `95%` o `0.95`.

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| «Falta la plantilla oficial …» al generar | Plantilla renombrada o ausente | Restaure los 4 archivos exactos en `templates\` |
| No genera PDF | Sin LibreOffice ni Excel | Instale LibreOffice; el Excel ya quedó generado |
| La firma no aparece en el formato | Firma inexistente o desactivada, o PNG alterado | Regístrela de nuevo en la vista **Firmas** |
| «Error inesperado» al abrir | Carpeta de datos sin permisos | Ejecute desde una carpeta del usuario (no `C:\Program Files`) |
| Recuperar datos tras reinstalar | — | Los datos no se borran: están en `Data\` (portable) o `%LOCALAPPDATA%\SistemaAT` (instalado) |
