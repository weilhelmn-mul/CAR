import { NextRequest, NextResponse } from 'next/server'
import { calcularEstadisticas } from '@/lib/analisis'
import type { TipoPeriodo } from '@/lib/periodos'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const tipo = (searchParams.get('tipo') ?? 'MENSUAL') as TipoPeriodo
  const ref = searchParams.get('ref') ?? '2026-11'
  const dep = searchParams.get('deportistaId')
  try {
    const ag = await calcularEstadisticas(tipo, ref, dep ? Number(dep) : undefined)
    return NextResponse.json(ag)
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : 'Error de cálculo' }, { status: 500 })
  }
}
