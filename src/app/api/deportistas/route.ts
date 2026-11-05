import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const q = searchParams.get('q')?.trim() ?? ''
  const categoria = searchParams.get('categoria') ?? ''
  const sexo = searchParams.get('sexo') ?? ''
  const deporte = searchParams.get('deporte') ?? ''
  const modalidad = searchParams.get('modalidad') ?? ''

  const donde: Record<string, unknown> = {}
  if (categoria) donde.categoria = categoria
  if (sexo) donde.sexo = sexo
  if (deporte) donde.deporte = deporte
  if (modalidad) donde.modalidad = modalidad
  if (q) {
    donde.OR = [
      { apellidoPaterno: { contains: q } }, { apellidoMaterno: { contains: q } },
      { nombres: { contains: q } }, { dni: { contains: q } },
    ]
  }
  const lista = await db.deportista.findMany({ where: donde, orderBy: [{ activo: 'desc' }, { orden: 'asc' }] })
  return NextResponse.json(lista)
}

export async function POST(req: NextRequest) {
  const b = await req.json()
  if (!b.apellidoPaterno || !b.nombres || !b.dni || !b.fechaNacimiento) {
    return NextResponse.json({ error: 'Datos obligatorios: apellidos, nombres, DNI y fecha de nacimiento' }, { status: 400 })
  }
  try {
    const nuevo = await db.deportista.create({
      data: {
        apellidoPaterno: String(b.apellidoPaterno).toUpperCase(), apellidoMaterno: String(b.apellidoMaterno ?? '').toUpperCase(),
        nombres: String(b.nombres).toUpperCase(), dni: String(b.dni),
        sexo: b.sexo ?? 'MASCULINO', fechaIngreso: b.fechaIngreso ? new Date(b.fechaIngreso) : null,
        deporte: b.deporte ?? 'ATLETISMO', fechaNacimiento: new Date(b.fechaNacimiento),
        nivelTecnico: b.nivelTecnico ?? 'DC', modalidad: b.modalidad ?? 'INTERNO',
        telefono: b.telefono ? String(b.telefono) : null, procedencia: b.procedencia ?? 'CUSCO',
        categoria: b.categoria ?? 'MAY', pad: !!b.pad, entrenador: b.entrenador ?? null,
        prueba: b.prueba ?? null, orden: b.orden ?? 99,
      },
    })
    return NextResponse.json(nuevo)
  } catch (e) {
    const msg = e instanceof Error && e.message.includes('Unique') ? 'El DNI ya está registrado' : 'Error al crear deportista'
    return NextResponse.json({ error: msg }, { status: 400 })
  }
}
