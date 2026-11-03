# INSTALL.md · Instalación del Sistema AT (usuario final)

**Sistema AT** — Gestión de formatos mensuales AT-F1, AT-F3, AT-F8 y AT-F9
**DINADAF · Dirección Nacional de Deportes Afiliados — Instituto Peruano del Deporte**

---

## 1. Requisitos

| Componente | Detalle |
|---|---|
| Sistema operativo | Windows 10 u 11 (64 bits) |
| Instalador | `SistemaAT_Setup_1.0.0.exe` (no requiere permisos de administrador) |
| LibreOffice (opcional) | Solo si desea generar los **PDF** desde la aplicación. Descarga: <https://es.libreoffice.org>. Si prefiere Microsoft Excel, la app también puede convertir vía Excel COM. |
| Plantillas oficiales | Ya vienen incluidas en la carpeta `templates/` de la instalación. |

## 2. Instalación paso a paso

1. Ejecute **`SistemaAT_Setup_1.0.0.exe`**.
2. Siga el asistente (en español):
   - Carpeta de destino: `%LOCALAPPDATA%\Programs\SistemaAT` por defecto (instalación por usuario, **sin admin**).
   - Marque las tareas de accesos directos: **menú Inicio** (por defecto) y **escritorio** (opcional).
3. Al finalizar, marque **“Ejecutar Sistema AT ahora”** y pulse *Terminar*.

## 3. Dónde viven los datos (importante)

La aplicación guarda todo el trabajo del usuario en:

```
%LOCALAPPDATA%\SistemaAT\
├── data\        → sistema_at.db (SQLite) + sistema_at.log
├── firmas\      → imágenes PNG de las firmas registradas
└── generados\   → documentos Excel/PDF que usted genera
```

- **Desinstalar NO borra estos datos.** Reinstalar o actualizar el sistema conserva deportistas, registros, planes, evaluaciones y firmas.
- Para respaldar, copie la carpeta completa `%LOCALAPPDATA%\SistemaAT\`.

## 4. Primeros pasos recomendados

1. **Firmas** (vista ✒️ Firmas): registre las firmas PNG de entrenadores, JUT, representante DINADAF y presidente de la FDN. Cada firma queda con hash SHA-256 y auditoría; solo se *desactivan*, nunca se borran.
2. **Deportistas** (vista 🏃): registre los atletas del CAR (nombre, deporte, prueba/modalidad, categoría U-18/U-20/U-23/MAY/JUV, sexo, región, entrenador, fecha de ingreso).
3. **AT-F3** (vista 📋): registre el informe mensual de cada deportista. La sección 7 admite importar competencias desde un Excel/CSV exportado de **SISDENA** (<https://sisdena.ipd.gob.pe>).
4. **AT-F1** (vista 📊): elija CAR y mes; las matrículas (Sección I) y la tabla de deportistas (Sección II.I) se llenan automáticamente; complete las valoraciones cualitativas.
5. **AT-F8** (vista 🗓️): planifique las tareas del mes.
6. **AT-F9** (vista ✅): al elegir JUT y período, el sistema carga automáticamente el plan AT-F8 del **período anterior** y calcula tareas planificadas/cumplidas/%, además de los % promedio de asistencia y cumplimiento desde los AT-F3 del período.

## 5. Generación de documentos

- **Excel**: cada vista tiene el botón *Generar Excel*; el archivo se guarda en `generados\` con la plantilla oficial rellenada y la firma insertada (AT-F3: Entrenador o JUT; AT-F1: JUT/DINADAF + Entrenador; AT-F8: JUT; AT-F9: JUT y, si hay opinión, Presidente de la FDN).
- **PDF**: botón *Generar PDF*. Requiere **LibreOffice** (recomendado) o Microsoft Excel. Si no hay ninguno, la app avisa y el Excel queda disponible para exportarlo a mano.

## 6. Actualizar plantillas oficiales

Las plantillas viajan dentro del programa (`templates\`). Si el IPD publica una versión nueva y no desea recompilar, copie las plantillas actualizadas a una carpeta `templates\` **junto al ejecutable** (`...\Programs\SistemaAT\templates\`); esa carpeta tiene prioridad.

> Los mapeos de celdas están centralizados en `src/services/excel.py` (diccionarios `MAPA_AT_F3`, `MAPA_AT_F1`, `MAPA_AT_F8`, `MAPA_AT_F9`). Si la plantilla cambia de distribución, solo se ajustan esos diccionarios.

## 7. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| “No se encontró la plantilla oficial …” | Verifique el nombre exacto del archivo en `templates\` (ver mensaje de error). |
| “No se encontró LibreOffice ni Microsoft Excel…” | Instale LibreOffice o exporte el PDF desde Excel manualmente. |
| No aparecen deportistas en AT-F3 | Regístrelos primero en la vista Deportistas (solo se listan los **activos**). |
| AT-F9 no carga tareas | Verifique que exista un AT-F8 del **mes anterior** con el mismo nombre del JUT (escrito exactamente igual). |
| Las firmas no aparecen en el PDF | Suba el PNG desde la vista Firmas antes de generar; el PNG debe existir en `%LOCALAPPDATA%\SistemaAT\firmas\`. |

## 8. Soporte / trazabilidad

- Cada firma aplicada queda registrada en `asignaciones_firma` y `auditoria_firmas` (con usuario de Windows y fecha/hora).
- El log técnico está en `%LOCALAPPDATA%\SistemaAT\data\sistema_at.log`.
