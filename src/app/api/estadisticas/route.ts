import { NextRequest, NextResponse } from 'next/server'
import { calcularEstadisticas } from '@/lib/analisis'
import type { TipoPeriodo } from '@/lib/periodos'

const TIPOS: TipoPeriodo[] = ['MENSUAL', 'BIMESTRAL', 'TRIMESTRAL', 'ANUAL']

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const tipo = (searchParams.get('tipo') ?? 'MENSUAL') as TipoPeriodo
  const ref = searchParams.get('ref') ?? '2026-11'
  const dep = searchParams.get('deportistaId')

  // Validación temprana: evita que un periodo inválido llegue a la base de datos (devolvía el stack de Prisma)
  if (!TIPOS.includes(tipo)) {
    return NextResponse.json({ error: `Tipo de periodo no válido: ${tipo}. Usa MENSUAL, BIMESTRAL, TRIMESTRAL o ANUAL.` }, { status: 400 })
  }
  const patron = tipo === 'ANUAL' ? /^\d{4}$/ : /^\d{4}-(0[1-9]|1[0-2])$/
  if (!patron.test(tipo === 'ANUAL' ? ref.slice(0, 4) : ref)) {
    return NextResponse.json({ error: `Periodo (ref) no válido: "${ref}". Formato esperado: ${tipo === 'ANUAL' ? 'AAAA (ej. 2026)' : 'AAAA-MM (ej. 2026-11)'}.` }, { status: 400 })
  }
  if (dep !== null && dep !== '' && !/^\d+$/.test(dep)) {
    return NextResponse.json({ error: 'deportistaId debe ser numérico' }, { status: 400 })
  }

  try {
    const ag = await calcularEstadisticas(tipo, ref, dep ? Number(dep) : undefined)
    return NextResponse.json(ag)
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : 'Error de cálculo' }, { status: 500 })
  }
}
