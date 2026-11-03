# RESUMEN EJECUTIVO · Sistema AT v1.0.0

**Sistema de Gestión de Formatos AT · DINADAF — Instituto Peruano del Deporte**
Aplicación de escritorio Windows (Python 3.12 + CustomTkinter + SQLite + openpyxl).

---

## 1. Archivos generados (24 + plantillas + icono)

| Grupo | Archivos |
|---|---|
| Raíz | `main.py`, `build.py`, `sistema_at.spec`, `installer.iss`, `requirements.txt`, `requirements-dev.txt`, `INSTALL.md`, `INSTALL_BUILD.md`, `RESUMEN_EJECUTIVO.md` |
| Núcleo `src/` | `__init__.py`, `config.py`, `theme.py`, `database.py`, `widgets.py`, `main_window.py` |
| Vistas `src/views/` | `__init__.py`, `dashboard.py`, `deportistas.py`, `firmas.py`, `at_f3.py`, `at_f1.py`, `at_f8.py`, `at_f9.py` |
| Servicios `src/services/` | `__init__.py`, `excel.py`, `pdf.py`, `sisdena.py` |
| Recursos | `assets/icon.ico`, `templates/` (las 4 plantillas oficiales), `data/`, `firmas/`, `generados/` (autogeneradas) |

## 2. Mapeos de celdas (verificados contra las plantillas entregadas)

Los diccionarios están al inicio de **`src/services/excel.py`**. Fueron derivados
inspeccionando celda por celda los 4 archivos oficiales (no son coordenadas de
ejemplo). **Solo deben ajustarse si el IPD cambia una plantilla.**

| Formato | Claves del mapa | Coordenadas verificadas |
|---|---|---|
| **AT-F3** | `MAPA_AT_F3` | Cabecera D8/D9/D10/D11 + J8 (región) y J9 (año); objetivos B14 (recuadro creado B14:J16); horario filas 19–21 × D–J; % asistencia B24 y % cumplimiento B28 (cuadros oficiales); test B32; detalle B36; competencias B40; cumplimiento B46; evaluación B51; observaciones B60 (recuadro creado B60:J63); firma D65. Se fuerza `fitToWidth=1` para impresión/PDF. |
| **AT-F1** | `MAPA_AT_F1` | CAR C7, mes C8, año E8; matrículas filas 13–17 + TOTAL 18 (C–J); tabla II.I filas 24–43 (20 cupos, se detecta el límite buscando “II-II” y se insertan filas seguras si hay más deportistas); valoraciones A45/A48/A51/A54/A58/A61/A64; IV.II A67 (recuadro creado); firmas B69 y H69. |
| **AT-F8** | `MAPA_AT_F8` | La cabecera oficial es **en línea**: A7 “FEDERACION: …”, A8 “NOMBRES Y APELLIDOS: …”, A9 “MES: … AÑO: …”; tareas filas 12–21 (10 cupos + inserción segura de filas extra); firma C26. |
| **AT-F9** | `MAPA_AT_F9` | Nombres D7, federación D9 (toma la del plan AT-F8 evaluado), mes H9, año J9; tareas D12/F12/H12; evaluación del cumplimiento B15 (recuadro creado B15:I15); % promedios G17/G18; dificultades secc. 2 B20; documentación B23; visitas D26/D27; resumen visitas B30; SÍ/NO F33–F35; análisis POA B38; otros B42; opinión B45; calificación C48/C49/C50; firmas D55 y H55. |

**Comportamiento especial de fila:**
- AT-F9: la “breve reseña de reuniones” no tiene recuadro en la plantilla oficial;
  si trae texto se **inserta una fila** dentro de la sección 2 (helper
  `_insertar_filas_seguras` reubica combinadas y alturas, que openpyxl no mueve).
- AT-F1/AT-F8: si los deportistas/tareas exceden los cupos de la plantilla, se
  insertan las filas necesarias copiando el estilo de la última fila.

## 3. Campos auxiliares agregados (documentados, pliego §13.1)

- `evaluaciones_jut.resumen_dificultades_seccion2` → “dificultades analizadas” de la sección 2 (la tabla original solo contempla el resumen de la sección 4).
- `evaluaciones_jut.pct_cumplimiento_promedio` / `pct_asistencia_promedio` → % promedio de los AT-F3 del período, **congelados al guardar** para que el informe no cambie si luego se editan registros.
- `deportistas.fecha_ingreso / fecha_retiro / activo` ya estaban en el esquema y se editan en el diálogo (necesarios para ingresos/retiros del AT-F1).
- Vista AT-F1: interruptor “Mostrar retirados” y botón “Recalcular matrículas”.

## 4. Cómo compilar el instalador (pasos exactos)

1. Instalar **Python 3.12/3.13** (no 3.14) y **Inno Setup 6** (ruta por defecto).
2. En la carpeta del proyecto:
   ```bat
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```
3. Verificar que `templates/` contiene las 4 plantillas con nombres exactos
   (AT-F1 CAR, AT-F3, ATF8, “AT -F9” con espacio antes de F9).
4. Ejecutar **`python build.py`** → limpia `build/`, `dist/`, `installer_output/`,
   compila con PyInstaller (`sistema_at.spec`), valida `dist\SistemaAT\SistemaAT.exe`,
   localiza `ISCC.exe` y compila `installer.iss`.
5. Resultado: **`installer_output\SistemaAT_Setup_1.0.0.exe`**.
   Flags útiles: `--exe-only` (solo ejecutable) y `--clean` (limpieza profunda).

## 5. Criterios de aceptación (pliego §10) — estado

| Criterio | Estado |
|---|---|
| `python main.py` abre la app con sidebar y dashboard | ✔ probado (GUI bajo display virtual) |
| Crear, editar y buscar deportistas | ✔ (búsqueda en vivo + diálogo de alta/edición) |
| Subir firma PNG con SHA-256 | ✔ (valida PNG real, copia a `firmas/`, audita) |
| Registrar AT-F3, guardar, recargar y ver persistido | ✔ (UPSERT por deportista+período) |
| Excel AT-F3 con firma insertada | ✔ (imagen ~160×60 px sobre el rótulo de firma) |
| PDF desde Excel (LibreOffice o Excel COM) | ✔ (convertidos con LibreOffice; COM como respaldo Windows) |
| AT-F1 consolidando múltiples AT-F3 | ✔ (tabla II.I autogenerada + matrículas agregadas) |
| AT-F8 planificado → AT-F9 evalúa jalando tareas y promedios | ✔ (carga automática del plan del período anterior; % y promedios automáticos) |
| `python build.py` produce el instalador | ✔ script completo (ejecutable en Windows con PyInstaller+Inno Setup) |
| Accesos de Menú Inicio/escritorio y desinstalador | ✔ definidos en `installer.iss` (español) |
| Datos persistentes en `%LOCALAPPDATA%\SistemaAT\` | ✔ (`config.py`; desinstalar no los borra) |
| Código comentado en español, modular, sin huérfanos | ✔ |

**Pruebas ejecutadas en el entorno de desarrollo:** esquema de BD completo, seed
de datos, generación de los 4 Excel (verificación celda por celda, inserción de
filas y de firmas), conversión de los 4 PDF, importación SISDENA (XLSX y CSV),
registro de auditoría de firmas y arranque de las 7 vistas de la interfaz.

## 6. Decisiones de interpretación documentadas

1. **AT-F9 evalúa el plan del período anterior** (§7.12 del pliego). La constante
   `DESFASE_PLAN = 1` en `src/views/at_f9.py` permite cambiarlo a `0` si su
   práctica es evaluar el plan del mismo mes.
2. Los nombres de JUT se normalizan en MAYÚSCULAS para que el emparejamiento
   AT-F8 → AT-F9 sea robusto; el CAR también (AT-F1).
3. La sección IV-I del AT-F1 (aspectos negativos + logros) se edita en dos
   cuadros y se escribe combinada en el único recuadro oficial (separados por
   línea en blanco).
4. La columna “Resultados competitivos y observaciones técnicas” del AT-F1 toma
   la sección 7 (competencias) del AT-F3 y, si está vacía, la sección 6.
5. Las firmas: AT-F3 usa Entrenador (respaldo JUT); AT-F1 usa JUT (respaldo
   DINADAF) + Entrenador; AT-F8 usa JUT (respaldo DINADAF); AT-F9 usa JUT y añade
   Presidente de la FDN solo si hay opinión registrada.
