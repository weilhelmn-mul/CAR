import { NextRequest, NextResponse } from 'next/server'
import { analisisRendimiento, resumenRendimiento } from '@/lib/rendimiento'

// GET /api/rendimiento?depId=X                      → pruebas y años disponibles
// GET /api/rendimiento?depId=X&prueba=Y&anio=Z      → análisis técnico completo
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const depId = Number(searchParams.get('depId'))
  if (!depId) return NextResponse.json({ error: 'Falta depId' }, { status: 400 })
  const prueba = searchParams.get('prueba') ?? ''
  const anio = Number(searchParams.get('anio')) || new Date().getUTCFullYear()
  try {
    if (!prueba) return NextResponse.json(await resumenRendimiento(depId))
    return NextResponse.json(await analisisRendimiento(depId, prueba, anio))
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : 'Error de análisis' }, { status: 400 })
  }
}
