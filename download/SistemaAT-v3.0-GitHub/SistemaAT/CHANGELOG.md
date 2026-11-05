# Changelog — Sistema AT

Todos los cambios notables del Sistema de Gestión de Formatos AT (IPD · DINADAF)
se documentan aquí. Formato basado en [Keep a Changelog](https://keepachangelog.com/)
y [Versionado Semántico](https://semver.org/).

## [3.0.0] — 2026-11

### Agregado
- **Asistente IA de redacción técnica** (vista propia + botones en módulos):
  motor local offline con bancos de frases por familia deportiva y semilla
  reproducible por deportista/periodo; soporte opcional de API compatible con
  OpenAI (`Data/config_ia.json`) con retorno automático al motor local.
- **Formato de alimentación**: evaluación nutricional mensual (peso, estatura,
  IMC automático, % grasa, kcal, objetivo, plan alimenticio asistido por IA)
  y exportación a Excel (`AT-NUT`) y PDF.
- **Formato de seguro**: pólizas por deportista con alerta automática de
  vencimiento (30 días) y listado exportable a Excel/PDF.
- **Expediente del atleta**: ficha completa (datos personales, categoría que
  compite, sexo, deporte, CAR) con **mejores resultados por mes, bimestre,
  trimestre y año**, registro rápido de resultados e historial completo;
  exportación del expediente a Excel (4 hojas) y PDF.
- **Módulo de análisis deportivo**: cuadros estadísticos (matrícula por
  categoría/sexo, distribución por deporte, asistencia/cumplimiento por
  periodo, top de resultados, IMC por categoría, estado de seguros) con
  exportación a Excel (5 hojas) y PDF.
- Nuevas tablas `resultados_deportivos`, `alimentacion` y `seguros` con
  migración idempotente desde bases v1/v2.
- Helper de escritura de narrativas (`actualizar_narrativa_f1/f3/f9`).

### Técnico
- `src/config.py`: versión 3.0, familias deportivas, constantes de nutrición
  y seguros, etiquetas de bloques bimestre/trimestre.
- `src/services/excel.py`: generadores `generar_alimentacion`,
  `generar_listado_seguros`, `generar_expediente`, `generar_analisis` con
  estilos institucionales (bandas de título, cabeceras índigo, bordes).

## [2.1.0] — 2026-11
- Paquete portable con instalador local (`Instalar-SistemaAT.bat`),
  respaldo de datos (`Respaldar-Datos.bat`) y desinstalador con salvaguarda
  de datos en el Escritorio.

## [2.0.0] — 2026-11
- Regeneración de la exportación Excel de AT-F3/F1/F8/F9 sobre las plantillas
  oficiales del IPD (se carga la plantilla y solo se escriben celdas de datos).
- Carga de participaciones SISDENA y horario semanal en AT-F3.

## [1.1.0] — 2026-11
- Portable real: lanzador C (`SistemaAT.exe`) + Python embebido, datos en
  `Data/` junto al ejecutable con fallback a `%LOCALAPPDATA%\SistemaAT`.

## [1.0.0] — 2026-11
- Primera versión: AT-F3, AT-F1, AT-F8, AT-F9, deportistas, firmas SHA-256
  con auditoría y dashboard.
