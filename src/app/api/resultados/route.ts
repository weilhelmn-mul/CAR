import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { marcaTexto } from '@/lib/periodos'

export async function POST(req: NextRequest) {
  const b = await req.json()
  if (!b.deportistaId || !b.fecha || !b.prueba || b.marcaValor === undefined) {
    return NextResponse.json({ error: 'Faltan datos: deportista, fecha, prueba y marca' }, { status: 400 })
  }
  const unidad = b.unidad === 'm' ? 'm' : 'seg'
  const valor = Number(b.marcaValor)
  const creado = await db.resultado.create({
    data: {
      deportistaId: Number(b.deportistaId),
      fecha: new Date(`${b.fecha}T00:00:00Z`),
      competencia: String(b.competencia ?? 'CONTROL TÉCNICO INTERNO').toUpperCase(),
      prueba: String(b.prueba), marca: b.marca || marcaTexto(valor, unidad),
      marcaValor: valor, unidad,
      puesto: b.puesto ? Number(b.puesto) : null,
      sede: b.sede ? String(b.sede).toUpperCase() : null,
      nivel: b.nivel ? String(b.nivel).toUpperCase() : 'CONTROL INTERNO',
    },
  })
  return NextResponse.json(creado)
}

export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const id = Number(searchParams.get('id'))
  if (!id) return NextResponse.json({ error: 'Falta id' }, { status: 400 })
  await db.resultado.delete({ where: { id } })
  return NextResponse.json({ ok: true })
}
