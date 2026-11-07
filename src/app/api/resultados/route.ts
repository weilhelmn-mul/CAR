import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { marcaTexto } from '@/lib/periodos'

export async function POST(req: NextRequest) {
  try {
    const b = await req.json()
    if (!b.deportistaId || !b.fecha || !b.prueba || b.marcaValor === undefined) {
      return NextResponse.json({ error: 'Faltan datos: deportista, fecha, prueba y marca' }, { status: 400 })
    }
    const valor = Number(b.marcaValor)
    if (!Number.isFinite(valor) || valor <= 0) {
      return NextResponse.json({ error: 'La marca numérica no es válida (ej. 11.25 seg o 7.12 m)' }, { status: 400 })
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(b.fecha)) || isNaN(new Date(`${b.fecha}T00:00:00Z`).getTime())) {
      return NextResponse.json({ error: 'La fecha no es válida' }, { status: 400 })
    }
    const dep = await db.deportista.findUnique({ where: { id: Number(b.deportistaId) }, select: { id: true } })
    if (!dep) return NextResponse.json({ error: 'El deportista indicado no existe' }, { status: 404 })
    const puesto = b.puesto ? Number(b.puesto) : null
    if (puesto !== null && (!Number.isInteger(puesto) || puesto < 1 || puesto > 999)) {
      return NextResponse.json({ error: 'El puesto debe ser un número entero entre 1 y 999' }, { status: 400 })
    }
    const unidad = b.unidad === 'm' ? 'm' : 'seg'
    const creado = await db.resultado.create({
      data: {
        deportistaId: Number(b.deportistaId),
        fecha: new Date(`${b.fecha}T00:00:00Z`),
        competencia: String(b.competencia ?? 'CONTROL TÉCNICO INTERNO').toUpperCase(),
        prueba: String(b.prueba), marca: b.marca || marcaTexto(valor, unidad),
        marcaValor: valor, unidad,
        puesto,
        sede: b.sede ? String(b.sede).toUpperCase() : null,
        nivel: b.nivel ? String(b.nivel).toUpperCase() : 'CONTROL INTERNO',
      },
    })
    return NextResponse.json(creado)
  } catch {
    return NextResponse.json({ error: 'No se pudo registrar el resultado' }, { status: 400 })
  }
}

export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const id = Number(searchParams.get('id'))
  if (!id) return NextResponse.json({ error: 'Falta id' }, { status: 400 })
  try {
    await db.resultado.delete({ where: { id } })
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: 'Resultado no encontrado' }, { status: 404 })
  }
}
