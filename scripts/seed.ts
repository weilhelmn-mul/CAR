/**
 * SEED — Sistema de Gestión de Formatos AT · IPD (CAR Cusco)
 * Carga los 18 deportistas del archivo oficial SEGURO- NOVIEMBRE - 2026,
 * entrenadores según entrenador.xlsx y resultados de ejemplo (CONTROL INTERNO)
 * para demostrar la sección de análisis. Los resultados son EDITABLES/ELIMINABLES.
 */
import { PrismaClient } from '@prisma/client'

const db = new PrismaClient()

type SeedDep = {
  orden: number; ap: string; am: string; nom: string; dni: string; sexo: string;
  ingreso: string | null; deporte: string; nac: string; nivel: string; mod: string;
  tel: string | null; proc: string; cat: string; pad: boolean; entrenador: string; prueba: string;
  base: number; unidad: 'seg' | 'm'; formato: (v: number) => string
}

const seg = (v: number) => {
  if (v >= 60) { const m = Math.floor(v / 60); const s = v - m * 60; return `${m}:${s.toFixed(1).padStart(4, '0')}` }
  return v.toFixed(2)
}
const met = (v: number) => v.toFixed(2)

const DEP: SeedDep[] = [
  { orden: 1, ap: 'COMPANOCCA', am: 'CHECCO', nom: 'ELVIS EMERSON', dni: '72021665', sexo: 'MASCULINO', ingreso: '2019-03-18', deporte: 'ATLETISMO', nac: '2004-06-24', nivel: 'DC', mod: 'INTERNO', tel: '931844232', proc: 'URINSAYA/CCOPORAQUE/ESPINAR', cat: 'MAY', pad: false, entrenador: 'OMAR MOLINA CRESPO', prueba: '100 m planos', base: 11.35, unidad: 'seg', formato: seg },
  { orden: 2, ap: 'CUITO', am: 'TACUSI', nom: 'NANCY', dni: '70816467', sexo: 'FEMENINO', ingreso: '2024-07-02', deporte: 'ATLETISMO', nac: '2000-10-30', nivel: 'DC', mod: 'INTERNO', tel: '986493744', proc: 'YANAOCA/CANAS', cat: 'MAY', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: '800 m', base: 148.0, unidad: 'seg', formato: seg },
  { orden: 3, ap: 'FLORES', am: 'LOPINTA', nom: 'KIMBERLY LISSETTE', dni: '61401617', sexo: 'FEMENINO', ingreso: '2024-02-12', deporte: 'ATLETISMO', nac: '2008-07-24', nivel: 'DECAN', mod: 'EXTERNO', tel: '948742932', proc: 'SANTIAGO/CUSCO', cat: 'U-18', pad: false, entrenador: 'OMAR MOLINA CRESPO', prueba: '100 m planos', base: 13.40, unidad: 'seg', formato: seg },
  { orden: 4, ap: 'HUAMAN', am: 'MATAMOROS', nom: 'LUIS GUSTAVO', dni: '71386805', sexo: 'MASCULINO', ingreso: '2023-02-08', deporte: 'ATLETISMO', nac: '2005-12-16', nivel: 'DECAN', mod: 'INTERNO', tel: '927726518', proc: 'YAULI-HUANCAVELICA', cat: 'U-23', pad: true, entrenador: 'OMAR MOLINA CRESPO', prueba: '3000 m', base: 595.0, unidad: 'seg', formato: seg },
  { orden: 5, ap: 'HUAMANI', am: 'CHEQQUERA', nom: 'LIZARDO', dni: '72264189', sexo: 'MASCULINO', ingreso: '2023-01-02', deporte: 'ATLETISMO', nac: '2006-01-26', nivel: 'DECAN', mod: 'INTERNO', tel: '966466443', proc: 'SANTO TOMAS/CHUMBIVILCAS', cat: 'U-20', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: '3000 m', base: 580.0, unidad: 'seg', formato: seg },
  { orden: 6, ap: 'LOAYZA', am: 'HUAMAN', nom: 'AYDEE', dni: '73489471', sexo: 'FEMENINO', ingreso: '2023-01-02', deporte: 'ATLETISMO', nac: '1994-12-05', nivel: 'DECAN', mod: 'EXTERNO', tel: '966466443', proc: 'ANTA', cat: 'MAY', pad: true, entrenador: 'JORGE BERRIOS BARCENA', prueba: '10000 m', base: 2430.0, unidad: 'seg', formato: seg },
  { orden: 7, ap: 'MAMANI', am: 'QUISPE', nom: 'NERI ROXANA', dni: '71051988', sexo: 'FEMENINO', ingreso: '2024-04-11', deporte: 'PARA ATLETISMO', nac: '1998-06-14', nivel: 'DECAN', mod: 'INTERNO', tel: '948202064', proc: 'PAUCARTAMBO', cat: 'MAY', pad: true, entrenador: 'JHON CUSI HUAMÁN', prueba: '400 m', base: 68.5, unidad: 'seg', formato: seg },
  { orden: 8, ap: 'MARQUEZ', am: 'HUISA', nom: 'EDWAR RELY', dni: '61193123', sexo: 'MASCULINO', ingreso: '2025-02-07', deporte: 'ATLETISMO', nac: '2007-08-16', nivel: 'DECAN', mod: 'INTERNO', tel: '941459668', proc: 'SANTO TOMAS/CHUMBIVILCAS', cat: 'U-20', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: '5000 m', base: 1005.0, unidad: 'seg', formato: seg },
  { orden: 9, ap: 'MEDINA', am: 'HUAILLANI', nom: 'JHOEL', dni: '60599221', sexo: 'MASCULINO', ingreso: '2025-02-07', deporte: 'ATLETISMO', nac: '2008-05-10', nivel: 'DECAN', mod: 'INTERNO', tel: '910767285', proc: 'CUSIPATA/QUISPICANCHIS', cat: 'U-18', pad: false, entrenador: 'PABLO MORALES ORTELANO', prueba: '800 m', base: 132.0, unidad: 'seg', formato: seg },
  { orden: 10, ap: 'MOLINA', am: 'CENTENO', nom: 'JHONATAN', dni: '76462013', sexo: 'MASCULINO', ingreso: '2024-10-11', deporte: 'ATLETISMO', nac: '2002-01-22', nivel: 'DECAN', mod: 'INTERNO', tel: '963468745', proc: 'CHAMACA/CHUMBIVILCAS', cat: 'U-23', pad: true, entrenador: 'JHON CUSI HUAMÁN', prueba: '800 m', base: 118.0, unidad: 'seg', formato: seg },
  { orden: 11, ap: 'PEREZ', am: 'CCASA', nom: 'DANIEL', dni: '48593924', sexo: 'MASCULINO', ingreso: '2025-03-10', deporte: 'PARA ATLETISMO', nac: '1994-11-20', nivel: 'DECAN', mod: 'INTERNO', tel: '921118305', proc: 'CHALLABAMBA/PAUCARTAMBO', cat: 'MAY', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: 'Lanzamiento de bala', base: 10.85, unidad: 'm', formato: met },
  { orden: 12, ap: 'VEGA', am: 'HUALLPA', nom: 'LOURDES', dni: '61390648', sexo: 'FEMENINO', ingreso: '2025-02-07', deporte: 'ATLETISMO', nac: '2009-02-15', nivel: 'DC', mod: 'INTERNO', tel: '932285560', proc: 'SANTO TOMAS/CHUMBIVILCAS', cat: 'U-18', pad: false, entrenador: 'PABLO MORALES ORTELANO', prueba: '10 km marcha', base: 3660.0, unidad: 'seg', formato: seg },
  { orden: 13, ap: 'VELASQUEZ', am: 'ROJAS', nom: 'DINA', dni: '47458760', sexo: 'FEMENINO', ingreso: '2025-02-07', deporte: 'ATLETISMO', nac: '1992-11-30', nivel: 'DECAN', mod: 'EXTERNO', tel: '937394295', proc: 'LAMAY/CALCA/CUSCO', cat: 'MAY', pad: true, entrenador: 'JHON CUSI HUAMÁN', prueba: 'Media maratón', base: 4920.0, unidad: 'seg', formato: seg },
  { orden: 14, ap: 'ROJAS', am: 'HUILLCA', nom: 'JHONS FILDER', dni: '61903114', sexo: 'MASCULINO', ingreso: '2025-11-17', deporte: 'ATLETISMO', nac: '2009-11-26', nivel: 'DC', mod: 'INTERNO', tel: '998356317', proc: 'PLAZA DE ARMAS S/N PERU/CUSCO/ANTA/ZURITE', cat: 'U-18', pad: false, entrenador: 'PABLO MORALES ORTELANO', prueba: '5 km marcha', base: 1650.0, unidad: 'seg', formato: seg },
  { orden: 15, ap: 'HUAMÁN', am: 'LLOQQUE', nom: 'HILDA', dni: '60017334', sexo: 'FEMENINO', ingreso: '2026-01-05', deporte: 'ATLETISMO', nac: '2006-11-13', nivel: 'DECAN', mod: 'INTERNO', tel: null, proc: 'PERU / CUSCO / CALCA / COYA', cat: 'U-20', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: 'Salto largo', base: 5.42, unidad: 'm', formato: met },
  { orden: 16, ap: 'DAZA', am: 'QUISPE', nom: 'DEMETRIO', dni: '60019084', sexo: 'MASCULINO', ingreso: '2006-11-20', deporte: 'PARA ATLETISMO', nac: '2006-11-20', nivel: 'DC', mod: 'INTERNO', tel: '900650254', proc: 'PERU/CUSCO/CUSCO/POROY', cat: 'JUV', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: '100 m planos', base: 12.60, unidad: 'seg', formato: seg },
  { orden: 17, ap: 'ARIAS', am: 'MAYHUA', nom: 'LUZ LIZANDRA', dni: '74913707', sexo: 'FEMENINO', ingreso: '2026-07-01', deporte: 'ATLETISMO', nac: '2006-02-08', nivel: 'DECAN', mod: 'EXTERNO', tel: '974754237', proc: 'PERU / CUSCO / CHUMBIVILCAS / CHAMACA', cat: 'U-23', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: '400 m', base: 63.2, unidad: 'seg', formato: seg },
  { orden: 18, ap: 'LABRA', am: 'PHUTURI', nom: 'YURI HEDLEY', dni: '60549836', sexo: 'MASCULINO', ingreso: '2026-07-01', deporte: 'ATLETISMO', nac: '1998-08-06', nivel: 'DC', mod: 'EXTERNO', tel: '935628928', proc: 'PERU / CUSCO / CANCHIS / SICUANI', cat: 'MAY', pad: false, entrenador: 'JHON CUSI HUAMÁN', prueba: '5000 m', base: 1030.0, unidad: 'seg', formato: met },
]

const HORARIO_DEFAULT = {
  manana: ['7:00–10:00', '7:00–10:00', '7:00–10:00', '7:00–10:00', '7:00–10:00', '6:00–11:00', 'DESCANSO'],
  tarde: ['16:00–18:00', '16:00–18:00', '16:00–18:00', '16:00–18:00', '16:00–18:00', 'DESCANSO', 'DESCANSO'],
  noche: ['DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO'],
}

async function main() {
  await db.resultado.deleteMany()
  await db.alimentacion.deleteMany()
  await db.formatoF3.deleteMany()
  await db.formatoF1.deleteMany()
  await db.formatoF8.deleteMany()
  await db.formatoF9.deleteMany()
  await db.deportista.deleteMany()

  // --- Deportistas ---
  for (const d of DEP) {
    await db.deportista.create({
      data: {
        orden: d.orden, apellidoPaterno: d.ap, apellidoMaterno: d.am, nombres: d.nom,
        dni: d.dni, sexo: d.sexo, fechaIngreso: d.ingreso ? new Date(d.ingreso + 'T00:00:00Z') : null,
        deporte: d.deporte, fechaNacimiento: new Date(d.nac + 'T00:00:00Z'), nivelTecnico: d.nivel,
        modalidad: d.mod, telefono: d.tel, procedencia: d.proc, categoria: d.cat, pad: d.pad,
        entrenador: d.entrenador, prueba: d.prueba, activo: true, retirado: false,
      },
    })
  }

  // --- Resultados de ejemplo (CONTROL INTERNO, sep/oct/nov 2026) ---
  // Para 'seg' mejora (disminuye) ~0.5%/mes; para 'm' mejora (aumenta) ~1.2%/mes
  const meses = [
    { mes: 9, dia: 24, comp: 'CONTROL TÉCNICO INTERNO' },
    { mes: 10, dia: 22, comp: 'CONTROL DE TOPES' },
    { mes: 11, dia: 12, comp: 'CONTROL TÉCNICO INTERNO' },
  ]
  for (const d of DEP) {
    const dep = await db.deportista.findUnique({ where: { dni: d.dni } })
    if (!dep) continue
    for (let i = 0; i < meses.length; i++) {
      const f = 0.006 * i            // mejora acumulada
      const ruido = i === 1 ? 0.0005 : 0
      let valor: number
      if (d.unidad === 'seg') valor = d.base * (1 - f + ruido) * (1 + (i === 0 ? 0.002 : 0))
      else valor = d.base * (1 + f * 2 + ruido)
      await db.resultado.create({
        data: {
          deportistaId: dep.id, fecha: new Date(`2026-${String(meses[i].mes).padStart(2, '0')}-${String(meses[i].dia).padStart(2, '0')}T00:00:00Z`),
          competencia: meses[i].comp, prueba: d.prueba, marca: d.formato(valor),
          marcaValor: Math.round(valor * 100) / 100, unidad: d.unidad,
          puesto: 1, sede: 'PISTA ATLÉTICA CAR CUSCO', nivel: 'CONTROL INTERNO',
        },
      })
    }
  }

  // --- Alimentación 1-15 nov 2026: todos incluidos (como archivo oficial) ---
  const todos = await db.deportista.findMany({ orderBy: { orden: 'asc' } })
  for (const t of todos) {
    await db.alimentacion.create({ data: { deportistaId: t.id, periodo: '2026-11-Q1', incluido: true, observaciones: null } })
  }

  // --- AT-F8 noviembre 2026 (plan de ejemplo) ---
  await db.formatoF8.create({
    data: {
      periodo: '2026-11', jefe: 'JEFE DE UNIDAD TÉCNICA CAR CUSCO',
      actividades: [
        { actividad: 'Evaluación física inicial del mes (test de campo) a todos los deportistas del CAR', fecha: '03/11/2026', hora: '7:00', lugar: 'PISTA ATLÉTICA CAR CUSCO', observaciones: 'Registrar marcas y cargas' },
        { actividad: 'Revisión y aprobación de los planes de entrenamiento mensual presentados por los entrenadores', fecha: '05/11/2026', hora: '9:00', lugar: 'OFICINA JUT – CAR CUSCO', observaciones: '' },
        { actividad: 'Control de asistencia y actualización de la base de datos de deportistas', fecha: '07/11/2026', hora: '8:00', lugar: 'CAR CUSCO', observaciones: '' },
        { actividad: 'Reunión técnica con entrenadores sobre periodización y cargas de la etapa específica', fecha: '11/11/2026', hora: '16:00', lugar: 'SALA DE VIDEO – CAR CUSCO', observaciones: '' },
        { actividad: 'Control técnico interno (topes) por prueba', fecha: '12/11/2026', hora: '7:00', lugar: 'PISTA ATLÉTICA CAR CUSCO', observaciones: 'Comparar con registro de septiembre/octubre' },
        { actividad: 'Capacitación en ciencias del deporte: nutrición aplicada al entrenamiento en altura', fecha: '18/11/2026', hora: '15:00', lugar: 'AUDITORIO CAR CUSCO', observaciones: 'Con participación de nutricionista' },
        { actividad: 'Visita técnica a los entrenadores externos', fecha: '20/11/2026', hora: '9:00', lugar: 'SEDES EXTERNAS', observaciones: '' },
        { actividad: 'Evaluación del cumplimiento del plan mensual y elaboración del informe AT-F9', fecha: '27/11/2026', hora: '10:00', lugar: 'OFICINA JUT – CAR CUSCO', observaciones: '' },
      ],
    },
  })

  // --- AT-F9 octubre 2026 (evaluación de ejemplo coherente con datos) ---
  await db.formatoF9.create({
    data: {
      periodo: '2026-10', jefe: 'JEFE DE UNIDAD TÉCNICA CAR CUSCO',
      planificadas: 8, cumplidas: 8,
      evaluacionCumplimiento: 'Se cumplieron las 8 tareas/actividades programadas para el mes de octubre, con un cumplimiento del 100 %.',
      cumplimientoPreparacion: 95.5, asistenciaPromedio: 96.8,
      dificultades: 'Alimentación: optimizar los horarios de suministro de alimentos, especialmente durante la mañana, procurando que el desayuno se brinde mínimo una hora antes del entrenamiento.',
      resenaRevision: 'Se realizó la revisión y el seguimiento de los planes de entrenamiento presentados por los entrenadores. La mayoría cumplen con la estructura metodológica establecida (objetivos, volumen, intensidad y evaluación); se recomendó ajustar los microciclos de los deportistas U-18 para equilibrar carga y recuperación.',
      visitas: 10, evaluacionVisitas: '18/20',
      resumenDificultades: 'Durante las 10 visitas técnicas realizadas en el periodo evaluado, se identificaron necesidades relacionadas con la reposición de material deportivo menor (conos, vallas y cintas métricas) y con la puntualidad de algunos deportistas externos en las sesiones de la tarde.',
      baseDatos: true, calendario: true, capacitaciones: true,
      analisisObjetivos: 'Se alcanzó un cumplimiento del 95 % de los objetivos operativos establecidos para el periodo evaluado. Entre los logros destacan la ejecución del control de topes de octubre y la actualización completa de los registros de asistencia; como aspecto por mejorar, la sistematización de los resultados de los controles.',
      otrosInteres: 'Se identifica como necesidad operativa prioritaria la cobertura de la plaza de conductor, a fin de disponer del vehículo para el traslado de los deportistas externos a las sesiones de entrenamiento.',
      calificacion: 'BUENO',
    },
  })

  const total = await db.deportista.count()
  const totalRes = await db.resultado.count()
  console.log(`SEED OK: ${total} deportistas, ${totalRes} resultados de ejemplo`)
}

main().catch((e) => { console.error(e); process.exit(1) }).finally(() => db.$disconnect())
