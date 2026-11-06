import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

const FORMATOS_VALIDOS = ['F1', 'F3', 'F8', 'F9']

// GET: lista de firmas registradas
export async function GET() {
  const lista = await db.firma.findMany({ orderBy: { clave: 'asc' } })
  return NextResponse.json(lista)
}

// POST: guarda/actualiza una firma (upsert por clave).
// - Al crear: la imagen es obligatoria.
// - Al actualizar: la imagen es opcional (si no viene, se conserva la actual) — permite editar solo nombre/cargo/formatos.
export async function POST(req: NextRequest) {
  const b = await req.json()
  const clave = String(b.clave ?? '').trim().toUpperCase()
  const nombre = String(b.nombre ?? '').trim()
  const cargo = String(b.cargo ?? '').trim()
  const imagen = String(b.imagen ?? '')
  const activo = b.activo !== false
  // formatos: array ['F1','F3'] o string 'F1,F3' — se normaliza a string separado por comas
  const fmt = Array.isArray(b.formatos) ? b.formatos.join(',') : String(b.formatos ?? '')
  const formatos = [...new Set(fmt.split(',').map((x) => x.trim().toUpperCase()).filter((x) => FORMATOS_VALIDOS.includes(x)))].join(',')

  if (!clave || !nombre || !cargo) {
    return NextResponse.json({ error: 'Datos incompletos: clave, nombre y cargo son obligatorios' }, { status: 400 })
  }
  const existente = await db.firma.findUnique({ where: { clave } })
  if (!existente && !imagen.startsWith('data:image/')) {
    return NextResponse.json({ error: 'Debes seleccionar la imagen de la firma' }, { status: 400 })
  }
  if (imagen && !imagen.startsWith('data:image/')) {
    return NextResponse.json({ error: 'La imagen de la firma no es válida' }, { status: 400 })
  }
  if (imagen.length > 2_000_000) {
    return NextResponse.json({ error: 'La imagen es demasiado grande (máximo ~1.5 MB). Usa un PNG o JPG más liviano.' }, { status: 400 })
  }
  try {
    const guardada = await db.firma.upsert({
      where: { clave },
      update: { nombre, cargo, activo, formatos, ...(imagen ? { imagen } : {}) },
      create: { clave, nombre, cargo, imagen, activo, formatos },
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
