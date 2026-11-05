import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

// GET: roster + registros de la quincena (default: incluido = true)
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const periodo = searchParams.get('periodo') ?? '2026-11-Q1'
  const [deps, registros] = await Promise.all([
    db.deportista.findMany({ where: { activo: true, retirado: false }, orderBy: { apellidoPaterno: 'asc' } }),
    db.alimentacion.findMany({ where: { periodo } }),
  ])
  const mapa = new Map(registros.map((r) => [r.deportistaId, r]))
  const filas = deps.map((d) => {
    const reg = mapa.get(d.id)
    return { deportista: d, incluido: reg ? reg.incluido : true, observaciones: reg?.observaciones ?? null }
  })
  return NextResponse.json({ periodo, filas })
}

// POST: upsert {deportistaId, periodo, incluido?, observaciones?}
export async function POST(req: NextRequest) {
  const b = await req.json()
  if (!b.deportistaId || !b.periodo) return NextResponse.json({ error: 'Faltan datos' }, { status: 400 })
  const data: { incluido?: boolean; observaciones?: string | null } = {}
  if (b.incluido !== undefined) data.incluido = !!b.incluido
  if (b.observaciones !== undefined) data.observaciones = b.observaciones || null
  const reg = await db.alimentacion.upsert({
    where: { deportistaId_periodo: { deportistaId: Number(b.deportistaId), periodo: String(b.periodo) } },
    create: { deportistaId: Number(b.deportistaId), periodo: String(b.periodo), incluido: b.incluido === undefined ? true : !!b.incluido, observaciones: b.observaciones || null },
    update: data,
  })
  return NextResponse.json(reg)
}
