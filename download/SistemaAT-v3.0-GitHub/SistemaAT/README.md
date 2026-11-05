# Sistema AT · Sistema de Gestión de Formatos AT — IPD · DINADAF

Aplicación de escritorio (Windows) para la gestión de los formatos técnicos de la
Dirección Deportiva (DINADAF) del **Instituto Peruano del Deporte**: informes mensuales
de deportistas (AT-F3), consolidados de CAR (AT-F1), planes del Jefe de Unidad Técnica
(AT-F8), evaluaciones mensuales (AT-F9) y, desde la **v3.0**, el **Asistente IA de
redacción técnica**, los módulos de **Alimentación** y **Seguro**, el **Expediente
del Atleta** con mejores resultados por mes/bimestre/trimestre/año y el módulo de
**Análisis Deportivo** exportable a Excel y PDF.

> 100 % local: sin internet, sin servidor y sin hosting. Los datos viven en una base
> SQLite dentro de la carpeta del sistema (modo portable) o de `%LOCALAPPDATA%`
> (modo instalado).

---

## ✨ Novedades de la v3.0

| Módulo | Descripción |
|---|---|
| **Asistente IA** (`✨`) | Redacta de forma original y con lenguaje técnico de las ciencias del deporte los campos narrativos de AT-F3, AT-F1, AT-F8, AT-F9 y del plan alimenticio. Motor local offline (semilla reproducible por deportista/periodo) + soporte opcional de API compatible con OpenAI. Aplica los textos directamente al registro con un clic. |
| **Formato de Alimentación** (`🥗`) | Evaluación nutricional mensual por deportista: peso, estatura, **IMC automático**, % de grasa, kcal/día, objetivo nutricional y plan alimenticio (asistido por IA). Exporta a Excel (`AT-NUT_...xlsx`) y PDF. |
| **Formato de Seguro** (`🛡️`) | Pólizas por deportista: aseguradora, tipo, póliza, cobertura, vigencias y estado con **alerta automática de vencimiento** (30 días). Exporta el listado completo a Excel/PDF. |
| **Expediente del Atleta** (`🥇`) | Visualización completa del atleta: datos personales, **categoría que compite, sexo**, deporte, CAR y **mejores resultados por mes, bimestre, trimestre y año**, más el historial completo y el registro rápido de resultados. Exporta el expediente completo (4 hojas) a Excel/PDF. |
| **Análisis Deportivo** (`📊`) | Cuadros estadísticos: matrícula por categoría y sexo, distribución por deporte, asistencia/cumplimiento promedio por periodo, top de resultados en podio, IMC promedio por categoría y estado de seguros. Todo **exportable a Excel (5 hojas) y PDF**. |
| **Base de datos extendida** | Nuevas tablas `resultados_deportivos`, `alimentacion` y `seguros`, con migración idempotente: las bases de datos v1/v2 se actualizan sin perder información. |

Los formatos AT-F3/F1/F8/F9 se generan **sobre las plantillas oficiales del IPD**
(archivos de `templates/`), escribiendo únicamente las celdas de datos para preservar
combinaciones, bordes y logos.

---

## 🗂️ Estructura del proyecto

```
SistemaAT/
├─ main.py                  # Punto de entrada (inicializa BD + GUI)
├─ build.py                 # Empaquetado PyInstaller (onefile + plantillas)
├─ sistema_at.spec          # Spec de PyInstaller
├─ installer.iss            # Script de instalador (Inno Setup, opcional)
├─ EJECUTAR_SISTEMA.bat     # Lanzador de doble clic (usa wheels\ sin internet)
├─ COMPILAR_EXE.bat         # Compila SistemaAT.exe (PyInstaller)
├─ requirements.txt         # Dependencias de ejecución
├─ requirements-dev.txt     # Dependencias de compilación
├─ src/
│  ├─ config.py             # Rutas (portable/instalado), mapas de celdas, constantes v3.0
│  ├─ database.py           # SQLite: esquema (12 tablas), CRUD, agregaciones y migraciones
│  ├─ main_window.py        # Ventana SPA (sidebar + 12 vistas)
│  ├─ theme.py / widgets.py # Tema institucional y componentes reutilizables
│  ├─ views/                # dashboard, deportistas, at_f3/f1/f8/f9, asistente,
│  │                        # expediente, alimentacion, seguro, analisis, firmas
│  └─ services/
│     ├─ asistente_ia.py    # ★ Motor de redacción técnica (local + API opcional)
│     ├─ excel.py           # Generadores de formatos (plantillas IPD + v3.0)
│     ├─ pdf.py             # Conversión Excel→PDF (LibreOffice / Excel COM)
│     └─ sisdena.py         # Carga de participaciones SISDENA
├─ templates/               # Plantillas oficiales IPD (nombres exactos, no renombrar)
├─ assets/                  # Iconos
├─ wheels/                  # Ruedas para instalación offline en Windows
└─ docs/                    # Guía de instalación y uso frecuente (PDF)
```

---

## 🚀 Requisitos y puesta en marcha

- **Windows 10/11 de 64 bits** (probado) — también corre en Linux/macOS instalando
  las dependencias con `pip` (el PDF vía Excel COM solo existe en Windows).
- Python **3.12 o 3.13** para modo desarrollo/compilación.

### Opción A · Ejecutar desde el código fuente (sin internet)

1. Instala Python 3.12/3.13 marcando **“Add python.exe to PATH”**.
2. Doble clic en `EJECUTAR_SISTEMA.bat` (usa las ruedas de `wheels/`; no descarga nada).

### Opción B · Entorno virtual (estándar)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

En Linux/macOS: `pip install -r requirements.txt && python main.py`.

### Opción C · Compilar el ejecutable portable

```bat
COMPILAR_EXE.bat        :: genera dist\SistemaAT.exe con PyInstaller
```

`build.py` empaqueta también `templates/` y `assets/`. Con [Inno Setup](https://jrsoftware.org/isinfo.php)
puede generarse además un instalador clásico desde `installer.iss`.

---

## 🤖 Configurar el Asistente IA

El asistente funciona **sin configuración**: usa el motor local (bancos de frases
técnicas por familia deportiva — resistencia, velocidad, fuerza, combate, equipo,
precisión, arte — y semilla reproducible por deportista/periodo, por lo que las
redacciones son originales pero verificables en auditoría).

Opcionalmente puede delegar la redacción en un modelo vía **API compatible con
OpenAI** creando el archivo `Data/config_ia.json` (o `data/config_ia.json` en desarrollo):

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "TU_CLAVE",
  "modelo": "gpt-4o-mini",
  "temperatura": 0.7
}
```

- Si la API falla o no está configurada, el sistema **vuelve al motor local automáticamente**.
- La clave nunca sale del equipo (no se envía a ningún otro destino que el `base_url` definido).
- `config_ia.json` está excluido del repositorio por seguridad (ver `.gitignore`).

---

## 📄 Formatos generados

| Formato | Salida | Plantilla |
|---|---|---|
| AT-F3 — Informe mensual del deportista | `AT-F3_NOMBRE_YYYY-MM.xlsx` | ✔ oficial IPD |
| AT-F1 — Consolidado mensual del CAR | `AT-F1_CAR_YYYY-MM.xlsx` | ✔ oficial IPD |
| AT-F8 — Plan mensual JUT | `AT-F8_JUT_YYYY-MM.xlsx` | ✔ oficial IPD |
| AT-F9 — Evaluación del mes anterior | `AT-F9_JUT_YYYY-MM.xlsx` | ✔ oficial IPD |
| AT-NUT — Ficha de alimentación | `AT-NUT_NOMBRE_YYYY-MM.xlsx` | libro estilizado v3.0 |
| Seguros — Listado de pólizas | `SEGUROS_listado.xlsx` | libro estilizado v3.0 |
| Expediente del atleta (4 hojas) | `EXPEDIENTE_NOMBRE.xlsx` | libro estilizado v3.0 |
| Análisis deportivo (5 hojas) | `ANALISIS_DEPORTIVO_YYYY-MM.xlsx` | libro estilizado v3.0 |

Todos los Excel se convierten a **PDF** con un clic (LibreOffice o Microsoft Excel
vía COM, en ese orden; sin ambos, el Excel queda igualmente disponible).

Los archivos se guardan en `Data/generados/` (portable) o
`%LOCALAPPDATA%\SistemaAT\generados\` (instalado).

---

## 🔐 Firmas y auditoría

Las firmas (entrenador, JUT, DINADAF, Presidente FDN) se registran con **hash SHA-256**;
al estamparlas en un formato se verifica su integridad y se deja constancia en la tabla
de auditoría. Las firmas nunca se eliminan: solo se desactivan.

---

## 🧪 Verificación

El proyecto incluye una batería de verificaciones usadas antes de cada entrega:
sintaxis de todos los módulos (`python -m py_compile src/**/*.py`), pruebas
funcionales de base de datos (resultados, alimentación, seguros, agregaciones por
periodo), redacción del asistente (originalidad por deportista, cita de marcas reales)
y generación de los cuatro libros Excel v3.0 con validación de contenido.

---

## 📦 Datos y respaldos

- `Data/sistema_at.db` — base de datos SQLite (todo el sistema).
- `Data/generados/` — formatos Excel/PDF generados.
- `Data/firmas/` — imágenes de firmas con su hash.
- `Data/sistema_at.log` — registro técnico.
- `Data/config_ia.json` — *(opcional)* configuración de API de IA.

Respaldar = copiar la carpeta `Data`. Ver `LEEME_PORTABLE.txt` y `docs/`.

---

## ⚠️ Nota sobre las plantillas

Las plantillas de `templates/` corresponden a los formatos oficiales del IPD.
Si la institución publica versiones nuevas, reemplácelas **manteniendo los nombres
exactos** y, si cambia la disposición de celdas, ajuste solo los mapas de
`src/config.py` (`MAPA_AT_F3`, `MAPA_AT_F1`, `MAPA_AT_F8`, `MAPA_AT_F9`).

---

## 📜 Licencia

Distribuido bajo la [Licencia MIT](LICENSE). Las plantillas oficiales IPD incluidas
en `templates/` son documentos institucionales: úselas únicamente en el marco de sus
funciones en el Instituto Peruano del Deporte.

---

*Sistema de Gestión de Formatos AT · v3.0 · DINADAF — Instituto Peruano del Deporte, 2026.*
