import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'
import { crearToken } from '@/proxy'

const USUARIO = process.env.CAR_USUARIO || 'car'
const CONTRASENA = process.env.CAR_CONTRASENA || 'CAR-Cusco-2026'

function igualSeguro(a: string, b: string): boolean {
  const ha = crypto.createHash('sha256').update(a).digest()
  const hb = crypto.createHash('sha256').update(b).digest()
  return crypto.timingSafeEqual(ha, hb)
}

export async function POST(req: NextRequest) {
  const b = await req.json().catch(() => ({}))
  const usuario = String(b.usuario ?? '')
  const contrasena = String(b.contrasena ?? '')
  if (!igualSeguro(usuario, USUARIO) || !igualSeguro(contrasena, CONTRASENA)) {
    return NextResponse.json({ error: 'Usuario o contraseña incorrectos' }, { status: 401 })
  }
  const token = await crearToken()
  const res = NextResponse.json({ ok: true })
  res.cookies.set('car_sesion', token, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 12 * 3600,
    secure: process.env.NODE_ENV === 'production',
  })
  return res
}
