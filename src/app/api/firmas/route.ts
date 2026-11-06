import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

// GET: lista de firmas registradas
export async function GET() {
  const lista = await db.firma.findMany({ orderBy: { clave: 'asc' } })
  return NextResponse.json(lista)
}

// POST: guarda/actualiza una firma (upsert por clave)
export async function POST(req: NextRequest) {
  const b = await req.json()
  const clave = String(b.clave ?? '').trim().toUpperCase()
  const nombre = String(b.nombre ?? '').trim()
  const cargo = String(b.cargo ?? '').trim()
  const imagen = String(b.imagen ?? '')
  const activo = b.activo !== false
  if (!clave || !nombre || !cargo || !imagen.startsWith('data:image/')) {
    return NextResponse.json({ error: 'Datos incompletos: clave, nombre, cargo e imagen son obligatorios' }, { status: 400 })
  }
  if (imagen.length > 2_000_000) {
    return NextResponse.json({ error: 'La imagen es demasiado grande (máximo ~1.5 MB). Usa un PNG o JPG más liviano.' }, { status: 400 })
  }
  try {
    const guardada = await db.firma.upsert({
      where: { clave },
      update: { nombre, cargo, imagen, activo },
      create: { clave, nombre, cargo, imagen, activo },
    })
    return NextResponse.json(guardada)
  } catch {
    return NextResponse.json({ error: 'Error al guardar la firma' }, { status: 500 })
  }
}

// DELETE: elimina una firma por id
export async function DELETE(req: NextRequest) {
  const id = Number(new URL(req.url).searchParams.get('id'))
  if (!id) return NextResponse.json({ error: 'Falta id' }, { status: 400 })
  try {
    await db.firma.delete({ where: { id } })
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: 'Firma no encontrada' }, { status: 404 })
  }
}
