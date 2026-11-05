import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

// GET detalle completo (ficha 360): deportista + resultados + alimentaciones
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const dep = await db.deportista.findUnique({
    where: { id: Number(id) },
    include: {
      resultados: { orderBy: { fecha: 'desc' } },
      alimentaciones: { orderBy: { periodo: 'desc' } },
      informesF3: { orderBy: { periodo: 'desc' } },
    },
  })
  if (!dep) return NextResponse.json({ error: 'Deportista no encontrado' }, { status: 404 })
  return NextResponse.json(dep)
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const b = await req.json()
  try {
    const actualizado = await db.deportista.update({
      where: { id: Number(id) },
      data: {
        apellidoPaterno: b.apellidoPaterno !== undefined ? String(b.apellidoPaterno).toUpperCase() : undefined,
        apellidoMaterno: b.apellidoMaterno !== undefined ? String(b.apellidoMaterno).toUpperCase() : undefined,
        nombres: b.nombres !== undefined ? String(b.nombres).toUpperCase() : undefined,
        dni: b.dni !== undefined ? String(b.dni) : undefined,
        sexo: b.sexo, fechaIngreso: b.fechaIngreso ? new Date(b.fechaIngreso) : null,
        deporte: b.deporte, fechaNacimiento: b.fechaNacimiento ? new Date(b.fechaNacimiento) : undefined,
        nivelTecnico: b.nivelTecnico, modalidad: b.modalidad,
        telefono: b.telefono !== undefined ? (b.telefono ? String(b.telefono) : null) : undefined,
        procedencia: b.procedencia, categoria: b.categoria, pad: b.pad,
        entrenador: b.entrenador !== undefined ? b.entrenador : undefined,
        prueba: b.prueba !== undefined ? b.prueba : undefined,
        activo: b.activo, retirado: b.retirado,
        fechaVencimientoContinuidad: b.fechaVencimientoContinuidad !== undefined ? (b.fechaVencimientoContinuidad ? new Date(b.fechaVencimientoContinuidad) : null) : undefined,
        fechaCaducidadAval: b.fechaCaducidadAval !== undefined ? (b.fechaCaducidadAval ? new Date(b.fechaCaducidadAval) : null) : undefined,
      },
    })
    return NextResponse.json(actualizado)
  } catch {
    return NextResponse.json({ error: 'No se pudo actualizar (verifique el DNI)' }, { status: 400 })
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  await db.deportista.delete({ where: { id: Number(id) } })
  return NextResponse.json({ ok: true })
}
