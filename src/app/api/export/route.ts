import { NextRequest } from 'next/server'
import { db } from '@/lib/db'
import {
  exportSeguro, exportAlimentacion, exportF3, exportF1, exportF8, exportF9,
  exportAnalisis, exportFicha, exportRendimiento, type DatosF1, type FichaData,
} from '@/lib/excel'
import { xlsxAPdf } from '@/lib/pdf'
import { calcularEstadisticas } from '@/lib/analisis'
import { analisisRendimiento } from '@/lib/rendimiento'
import { infoQuincena, MESES_ES, nombreCompleto, HORARIO_DEFAULT, type TipoPeriodo } from '@/lib/periodos'

async function imagenFirma(clave: string): Promise<string | null> {
  const f = await db.firma.findUnique({ where: { clave } })
  return f?.activo ? f.imagen : null
}

function respuesta(buf: Buffer, tipo: string, nombre: string) {
  return new Response(new Uint8Array(buf), {
    headers: {
      'Content-Type': tipo === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': `attachment; filename="archivo.${tipo}"; filename*=UTF-8''${encodeURIComponent(nombre)}`,
      'Cache-Control': 'no-store',
    },
  })
}

function nombreMes(ref: string) { return MESES_ES[parseInt(ref.split('-')[1]) - 1] }
function anioDe(ref: string) { return ref.split('-')[0] }

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const tipo = searchParams.get('tipo') ?? ''
  const formato = searchParams.get('formato') ?? 'xlsx'
  const refMes = searchParams.get('periodo') ?? new Date().toISOString().slice(0, 7)
  try {
    let xlsx: Buffer | null = null
    let nombre = 'archivo.xlsx'

    if (tipo === 'seguro') {
      const deps = await db.deportista.findMany({ where: { activo: true, retirado: false }, orderBy: { orden: 'asc' } })
      xlsx = await exportSeguro(deps as unknown as { [k: string]: unknown }[], refMes)
      nombre = `SEGURO - ${nombreMes(refMes)} - ${anioDe(refMes)}.xlsx`
    } else if (tipo === 'alimentacion') {
      const periodo = refMes.includes('-Q') ? refMes : `${refMes}-Q1`
      const q = infoQuincena(periodo)
      const deps = await db.deportista.findMany({ where: { activo: true, retirado: false }, orderBy: { apellidoPaterno: 'asc' } })
      const registros = await db.alimentacion.findMany({ where: { periodo } })
      xlsx = await exportAlimentacion(deps as unknown as { [k: string]: unknown }[], new Map(registros.map((r) => [r.deportistaId, r])), periodo)
      nombre = `ALIMENTACIÓN DEL ${q.d1} AL ${q.d2} DE ${nombreMes(`${periodo.slice(0, 7)}-01`)} ${q.anio}.xlsx`
    } else if (tipo === 'f3') {
      const depId = Number(searchParams.get('depId'))
      const dep = await db.deportista.findUnique({ where: { id: depId } })
      if (!dep) return Response.json({ error: 'Deportista no encontrado' }, { status: 404 })
      const f3 = await db.formatoF3.findUnique({ where: { deportistaId_periodo: { deportistaId: depId, periodo: refMes } } })
      xlsx = await exportF3(
        dep as unknown as { [k: string]: unknown },
        {
          objetivos: f3?.objetivos ?? '', horario: (f3?.horario as typeof HORARIO_DEFAULT) ?? HORARIO_DEFAULT,
          asistencia: f3?.asistencia ?? null, cumplimiento: f3?.cumplimiento ?? null,
          testControles: f3?.testControles ?? '', detallePreparacion: f3?.detallePreparacion ?? '',
          competencias: f3?.competencias ?? '', cumplimientoObjetivos: f3?.cumplimientoObjetivos ?? '',
          evaluacionGeneral: f3?.evaluacionGeneral ?? '', observaciones: f3?.observaciones ?? '',
        },
        refMes,
        await imagenFirma('ENTRENADOR'),
      )
      nombre = `FORMATO AT-F3 - ${nombreCompleto(dep)} - ${nombreMes(refMes)} ${anioDe(refMes)}.xlsx`
    } else if (tipo === 'f1') {
      const datos = await armarF1(refMes)
      xlsx = await exportF1(datos, refMes, await imagenFirma('JUT'), await imagenFirma('ENTRENADOR'))
      nombre = `FORMATO AT-F1 CAR - ${nombreMes(refMes)} ${anioDe(refMes)}.xlsx`
    } else if (tipo === 'f8') {
      const rec = await db.formatoF8.findUnique({ where: { periodo: refMes } })
      xlsx = await exportF8({
        federacion: rec?.federacion ?? 'FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO',
        jefe: rec?.jefe ?? '', actividades: (rec?.actividades as unknown as { actividad: string; fecha: string; hora: string; lugar: string; observaciones: string }[]) ?? [],
      }, refMes)
      nombre = `FORMATO AT-F8 - ${nombreMes(refMes)} ${anioDe(refMes)}.xlsx`
    } else if (tipo === 'f9') {
      const rec = await db.formatoF9.findUnique({ where: { periodo: refMes } })
      xlsx = await exportF9(rec ? {
        jefe: rec.jefe, planificadas: rec.planificadas, cumplidas: rec.cumplidas, evaluacionCumplimiento: rec.evaluacionCumplimiento,
        cumplimientoPreparacion: rec.cumplimientoPreparacion, asistenciaPromedio: rec.asistenciaPromedio, dificultades: rec.dificultades,
        resenaRevision: rec.resenaRevision, visitas: rec.visitas, evaluacionVisitas: rec.evaluacionVisitas, resumenDificultades: rec.resumenDificultades,
        baseDatos: rec.baseDatos, calendario: rec.calendario, capacitaciones: rec.capacitaciones, analisisObjetivos: rec.analisisObjetivos,
        otrosInteres: rec.otrosInteres, calificacion: rec.calificacion,
      } : {}, refMes, await imagenFirma('JUT'))
      nombre = `FORMATO AT-F9 - ${nombreMes(refMes)} ${anioDe(refMes)}.xlsx`
    } else if (tipo === 'analisis') {
      const tipoP = (searchParams.get('tipoPeriodo') ?? 'MENSUAL') as TipoPeriodo
      const ag = await calcularEstadisticas(tipoP, refMes)
      xlsx = await exportAnalisis(ag)
      nombre = `ANALISIS DEPORTIVO - ${ag.etiqueta}.xlsx`
    } else if (tipo === 'rendimiento') {
      const depIdR = Number(searchParams.get('depId'))
      const pruebaR = searchParams.get('prueba') ?? ''
      const anioR = Number(searchParams.get('anio')) || new Date().getUTCFullYear()
      if (!depIdR || !pruebaR) return Response.json({ error: 'Faltan depId o prueba' }, { status: 400 })
      const rend = await analisisRendimiento(depIdR, pruebaR, anioR)
      xlsx = await exportRendimiento(rend)
      nombre = `ANALISIS DE RENDIMIENTO - ${rend.nombre} - ${pruebaR} - ${anioR}.xlsx`
    } else if (tipo === 'ficha') {
      const depId = Number(searchParams.get('depId'))
      const dep = await db.deportista.findUnique({ where: { id: depId }, include: { resultados: { orderBy: { fecha: 'desc' } } } })
      if (!dep) return Response.json({ error: 'Deportista no encontrado' }, { status: 404 })
      const hoy = new Date()
      let edadN = hoy.getUTCFullYear() - dep.fechaNacimiento.getUTCFullYear()
      if (hoy.getUTCMonth() < dep.fechaNacimiento.getUTCMonth() || (hoy.getUTCMonth() === dep.fechaNacimiento.getUTCMonth() && hoy.getUTCDate() < dep.fechaNacimiento.getUTCDate())) edadN--
      const mejores: { etiqueta: string; marca: string; fecha: string; competencia: string }[] = []
      const [yy, mm] = refMes.split('-').map(Number)
      for (const [tp, rf, et] of [
        ['MENSUAL', refMes, 'MES ACTUAL'], ['BIMESTRAL', `${yy}-${String(mm).padStart(2, '0')}`, 'BIMESTRE ACTUAL'],
        ['TRIMESTRAL', `${yy}-${String(mm).padStart(2, '0')}`, 'TRIMESTRE ACTUAL'], ['ANUAL', String(yy), `AÑO ${yy}`],
      ] as [TipoPeriodo, string, string][]) {
        const e = await calcularEstadisticas(tp, rf, depId)
        e.mejores.forEach((x) => mejores.push({ etiqueta: `${et} · ${x.prueba}`, marca: x.marca, fecha: x.fecha, competencia: x.competencia }))
      }
      const ficha: FichaData = {
        dep: dep as unknown as { [k: string]: unknown }, edad: edadN,
        resultados: dep.resultados.map((r) => ({ fecha: r.fecha.toISOString(), competencia: r.competencia, prueba: r.prueba, marca: r.marca, puesto: r.puesto, sede: r.sede, nivel: r.nivel })),
        mejores,
      }
      xlsx = await exportFicha(ficha)
      nombre = `FICHA 360 - ${nombreCompleto(dep)}.xlsx`
    } else {
      return Response.json({ error: 'Tipo de exportación no válido' }, { status: 400 })
    }

    if (formato === 'pdf') {
      const pdf = await xlsxAPdf(xlsx!, nombre.replace(/\.xlsx$/, '.pdf'))
      return respuesta(pdf, 'pdf', nombre.replace(/\.xlsx$/, '.pdf'))
    }
    return respuesta(xlsx!, 'xlsx', nombre)
  } catch (e) {
    console.error('EXPORT ERROR', e)
    return Response.json({ error: e instanceof Error ? e.message : 'Error de exportación' }, { status: 500 })
  }
}

async function armarF1(refMes: string): Promise<DatosF1> {
  const deps = await db.deportista.findMany({ where: { activo: true, retirado: false }, orderBy: { orden: 'asc' } })
  const f3s = await db.formatoF3.findMany({ where: { periodo: refMes } })
  const mapaF3 = new Map(f3s.map((x) => [x.deportistaId, x]))
  const [anio, mes] = refMes.split('-').map(Number)
  const desde = new Date(Date.UTC(anio, mes - 1, 1)), hasta = new Date(Date.UTC(anio, mes, 1))
  const catCounts = new Map<string, { damas: number; varones: number }>()
  deps.forEach((d) => {
    const c = catCounts.get(d.categoria) ?? { damas: 0, varones: 0 }
    if (d.sexo === 'FEMENINO') c.damas++; else c.varones++
    catCounts.set(d.categoria, c)
  })
  const ingresosPorCat = new Map<string, number>()
  deps.forEach((d) => {
    if (d.fechaIngreso && d.fechaIngreso >= desde && d.fechaIngreso < hasta) ingresosPorCat.set(d.categoria, (ingresosPorCat.get(d.categoria) ?? 0) + 1)
  })
  const rec = await db.formatoF1.findUnique({ where: { periodo: refMes } })
  return {
    matriculas: ['U-18', 'U-20', 'U-23', 'MAY', 'JUV'].map((cat) => {
      const c = catCounts.get(cat) ?? { damas: 0, varones: 0 }
      const g = (rec?.matriculas as DatosF1['matriculas'] | undefined)?.find((x) => x.cat === cat)
      return {
        cat, retiros: g?.retiros ?? 0, ingresos: g?.ingresos ?? (ingresosPorCat.get(cat) ?? 0),
        damas: c.damas, varones: c.varones, total: c.damas + c.varones,
        sesiones: g?.sesiones ?? 20, manana: g?.manana ?? '7:00 - 9:00', tarde: g?.tarde ?? '16:00 - 18:00',
      }
    }),
    filas: deps.map((d) => {
      const f3 = mapaF3.get(d.id)
      const g = (rec?.filas as DatosF1['filas'] | undefined)?.find((x) => x.deportistaId === d.id)
      return {
        deportistaId: d.id, nombre: nombreCompleto(d), deporte: d.deporte, nivel: d.nivelTecnico,
        asistencia: g?.asistencia ?? f3?.asistencia ?? null,
        cumplimiento: g?.cumplimiento ?? f3?.cumplimiento ?? null,
        observaciones: g?.observaciones ?? ((f3?.competencias ?? f3?.evaluacionGeneral ?? '') || ''),
      }
    }),
    textos: (rec?.textos as DatosF1['textos'] | undefined) ?? {},
  }
}
