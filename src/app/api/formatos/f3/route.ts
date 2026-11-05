import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { HORARIO_DEFAULT } from '@/lib/periodos'

// ============ AT-F3 por deportista y periodo ============

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const deportistaId = Number(searchParams.get('deportistaId'))
  const periodo = searchParams.get('periodo') ?? ''
  if (!deportistaId || !periodo) return NextResponse.json({ error: 'Faltan datos' }, { status: 400 })
  const rec = await db.formatoF3.findUnique({ where: { deportistaId_periodo: { deportistaId, periodo } } })
  return NextResponse.json(rec ?? { deportistaId, periodo, objetivos: '', horario: HORARIO_DEFAULT, asistencia: null, cumplimiento: null, testControles: '', detallePreparacion: '', competencias: '', cumplimientoObjetivos: '', evaluacionGeneral: '', observaciones: '' })
}

export async function POST(req: NextRequest) {
  const b = await req.json()
  if (!b.deportistaId || !b.periodo) return NextResponse.json({ error: 'Faltan datos' }, { status: 400 })
  const data = {
    objetivos: b.objetivos ?? null, horario: b.horario ?? HORARIO_DEFAULT,
    asistencia: b.asistencia === '' || b.asistencia == null ? null : Number(b.asistencia),
    cumplimiento: b.cumplimiento === '' || b.cumplimiento == null ? null : Number(b.cumplimiento),
    testControles: b.testControles ?? null, detallePreparacion: b.detallePreparacion ?? null,
    competencias: b.competencias ?? null, cumplimientoObjetivos: b.cumplimientoObjetivos ?? null,
    evaluacionGeneral: b.evaluacionGeneral ?? null, observaciones: b.observaciones ?? null,
  }
  const rec = await db.formatoF3.upsert({
    where: { deportistaId_periodo: { deportistaId: Number(b.deportistaId), periodo: String(b.periodo) } },
    create: { deportistaId: Number(b.deportistaId), periodo: String(b.periodo), ...data },
    update: data,
  })
  return NextResponse.json(rec)
}
