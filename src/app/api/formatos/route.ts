import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { HORARIO_DEFAULT } from '@/lib/periodos'

// ============ FORMATOS F1 / F8 / F9 ============

function matriculasBase(categoriaCounts: Map<string, { damas: number; varones: number }>, ingresosPorCat: Map<string, number>) {
  return ['U-18', 'U-20', 'U-23', 'MAY', 'JUV'].map((cat) => {
    const c = categoriaCounts.get(cat) ?? { damas: 0, varones: 0 }
    return {
      cat, retiros: 0, ingresos: ingresosPorCat.get(cat) ?? 0,
      damas: c.damas, varones: c.varones, total: c.damas + c.varones,
      sesiones: 20, manana: '7:00 - 9:00', tarde: '16:00 - 18:00',
    }
  })
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const f = searchParams.get('f')
  const periodo = searchParams.get('periodo') ?? ''
  if (!periodo) return NextResponse.json({ error: 'Falta periodo' }, { status: 400 })

  if (f === 'f8') {
    const rec = await db.formatoF8.findUnique({ where: { periodo } })
    return NextResponse.json(rec ?? { periodo, federacion: 'FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO', jefe: '', actividades: [] })
  }

  if (f === 'f9') {
    const rec = await db.formatoF9.findUnique({ where: { periodo } })
    // sugerencias calculadas desde los F3 del mes
    const f3s = await db.formatoF3.findMany({ where: { periodo } })
    const asis = f3s.filter((x) => x.asistencia != null)
    const cum = f3s.filter((x) => x.cumplimiento != null)
    const sugerencia = {
      asistenciaPromedio: asis.length ? Math.round((asis.reduce((a, x) => a + (x.asistencia ?? 0), 0) / asis.length) * 10) / 10 : null,
      cumplimientoPreparacion: cum.length ? Math.round((cum.reduce((a, x) => a + (x.cumplimiento ?? 0), 0) / cum.length) * 10) / 10 : null,
      informesF3: f3s.length,
    }
    return NextResponse.json({
      rec: rec ?? null, sugerencia,
      base: { periodo, jefe: '', planificadas: 0, cumplidas: 0, evaluacionCumplimiento: '', cumplimientoPreparacion: null, asistenciaPromedio: null, dificultades: '', resenaRevision: '', visitas: null, evaluacionVisitas: '', resumenDificultades: '', baseDatos: true, calendario: true, capacitaciones: true, analisisObjetivos: '', otrosInteres: '', calificacion: 'BUENO' },
    })
  }

  if (f === 'f1') {
    // datos base computados + registro guardado
    const deps = await db.deportista.findMany({ where: { activo: true, retirado: false }, orderBy: { orden: 'asc' } })
    const f3s = await db.formatoF3.findMany({ where: { periodo } })
    const mapaF3 = new Map(f3s.map((x) => [x.deportistaId, x]))

    const [anio, mes] = periodo.split('-').map(Number)
    const desde = new Date(Date.UTC(anio, mes - 1, 1))
    const hasta = new Date(Date.UTC(anio, mes, 1))
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

    const filas = deps.map((d) => {
      const f3 = mapaF3.get(d.id)
      return {
        deportistaId: d.id, nombre: `${d.apellidoPaterno} ${d.apellidoMaterno} ${d.nombres}`.replace(/\s+/g, ' ').trim(),
        deporte: d.deporte, nivel: d.nivelTecnico,
        asistencia: f3?.asistencia ?? null, cumplimiento: f3?.cumplimiento ?? null,
        observaciones: (f3?.competencias ?? f3?.evaluacionGeneral ?? '') || '',
      }
    })
    const rec = await db.formatoF1.findUnique({ where: { periodo } })
    return NextResponse.json({
      base: { periodo, matriculas: matriculasBase(catCounts, ingresosPorCat), filas, textos: {} },
      rec,
    })
  }

  return NextResponse.json({ error: 'Formato no válido' }, { status: 400 })
}

export async function POST(req: NextRequest) {
  const b = await req.json()
  const f = b.f, periodo = b.periodo
  if (!f || !periodo) return NextResponse.json({ error: 'Faltan datos' }, { status: 400 })

  if (f === 'f8') {
    const rec = await db.formatoF8.upsert({
      where: { periodo },
      create: { periodo, federacion: b.federacion ?? 'FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO', jefe: b.jefe ?? '', actividades: b.actividades ?? [] },
      update: { federacion: b.federacion, jefe: b.jefe, actividades: b.actividades },
    })
    return NextResponse.json(rec)
  }
  if (f === 'f9') {
    const data = {
      jefe: b.jefe ?? null, planificadas: Number(b.planificadas ?? 0), cumplidas: Number(b.cumplidas ?? 0),
      evaluacionCumplimiento: b.evaluacionCumplimiento ?? null, cumplimientoPreparacion: b.cumplimientoPreparacion ?? null,
      asistenciaPromedio: b.asistenciaPromedio ?? null, dificultades: b.dificultades ?? null, resenaRevision: b.resenaRevision ?? null,
      visitas: b.visitas ?? null, evaluacionVisitas: b.evaluacionVisitas ?? null, resumenDificultades: b.resumenDificultades ?? null,
      baseDatos: !!b.baseDatos, calendario: !!b.calendario, capacitaciones: !!b.capacitaciones,
      analisisObjetivos: b.analisisObjetivos ?? null, otrosInteres: b.otrosInteres ?? null, calificacion: b.calificacion ?? 'BUENO',
    }
    const rec = await db.formatoF9.upsert({ where: { periodo }, create: { periodo, ...data }, update: data })
    return NextResponse.json(rec)
  }
  if (f === 'f1') {
    const data = { matriculas: b.matriculas ?? [], textos: b.textos ?? {}, filas: b.filas ?? [] }
    const rec = await db.formatoF1.upsert({ where: { periodo }, create: { periodo, ...data }, update: data })
    return NextResponse.json(rec)
  }
  return NextResponse.json({ error: 'Formato no válido' }, { status: 400 })
}

// nota: HORARIO_DEFAULT se usa en /api/formatos/f3
export const _h = HORARIO_DEFAULT
