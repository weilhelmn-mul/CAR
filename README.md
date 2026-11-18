# Sistema de Gestión de Formatos AT · IPD DINADAF — CAR Cusco

Sistema web para la gestión de los formatos administrativos del **Centro Alto Rendimiento (CAR) Cusco** del Instituto Peruano del Deporte (IPD) · Dirección Nacional de Deporte Afiliado y Formativo (DINADAF).

## Módulos

| Pestaña | Función |
|---|---|
| **Inicio** | Panel general: KPIs, composición de la población, alertas de aval/continuidad, cumpleaños y resultados del mes, accesos rápidos |
| **Deportistas** | Registro completo (18+ campos), filtros avanzados, ordenamiento, columnas configurables, estado ACTIVO / INACTIVO / RETIRADO y Ficha 360° |
| **Formatos** | AT-F1 (consolidado), AT-F3 (informe por deportista), AT-F8 (plan JUT), AT-F9 (evaluación), Programación de Alimentación y Lista para Seguro (PAD) — con redacción asistida por IA, guardado automático y exportación a Excel y PDF |
| **Análisis deportivo** | Estadísticas por periodo (mes/bimestre/trimestre/año), mejores marcas y rendimiento individual por prueba y año |
| **Firmas** | Carga de firmas escaneadas con nombre, cargo y formatos donde se incrustan |
| **Asistente IA** | Consultas técnicas y apoyo en la redacción de los informes AT |

## Stack tecnológico

- **Next.js 16** (App Router) + **TypeScript** + **Tailwind CSS 4** + shadcn/ui
- **Prisma ORM** + SQLite (`db/custom.db`, no incluido en el repositorio)
- **Recharts** para gráficas estadísticas (diseño responsive PC/celular)
- Módulo de IA basado en z-ai-web-dev-sdk (solo servidor)

## Estructura

```
src/
  app/                  # Rutas y API REST (deportistas, formatos, export, ia, estadisticas)
  components/at/        # Módulos del sistema (inicio, deportistas, formatos, análisis, firmas, asistente)
  lib/                  # Lógica compartida (periodos, excel, ia)
prisma/schema.prisma    # Modelo de datos (Deportista, Resultado, FormatoF1/F3/F8/F9, Alimentacion, Firma)
templates/              # Plantillas oficiales en blanco (Excel)
```

## Puesta en marcha

```bash
npm install
npx prisma db push     # crea la base de datos local (db/custom.db)
npm run dev            # desarrollo en http://localhost:3000
```

## Notas

- La **base de datos no se incluye** en el repositorio por contener datos personales: se crea localmente con `prisma db push`.
- `.env` (variables de entorno y claves) tampoco se incluye.
- Diseño adaptado a PC y celular en todas las pestañas.
- Plantillas oficiales: AT-F1, AT-F3, AT-F8, AT-F9, Alimentación y Seguro (carpeta `templates/`).
