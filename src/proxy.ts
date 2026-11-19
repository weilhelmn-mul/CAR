// Protección de sesión del sistema CAR Cusco (Edge runtime, WebCrypto).
// Cookie firmada con HMAC-SHA256; 12 horas de validez.
import { NextRequest, NextResponse } from 'next/server'

const SECRETO = process.env.CAR_SECRETO || 'car-cusco-secreto-2026'
const COOKIE = 'car_sesion'

async function hmac(texto: string): Promise<string> {
  const enc = new TextEncoder()
  const clave = await crypto.subtle.importKey('raw', enc.encode(SECRETO), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  const firma = await crypto.subtle.sign('HMAC', clave, enc.encode(texto))
  return Array.from(new Uint8Array(firma)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function validar(token: string): Promise<boolean> {
  if (!token) return false
  const partes = token.split('.')
  if (partes.length !== 3 || partes[0] !== 'v1') return false
  const esperada = await hmac(`v1.${partes[1]}`)
  if (esperada !== partes[2]) return false
  const exp = Number(partes[1])
  return Number.isFinite(exp) && exp > Date.now()
}

export async function crearToken(): Promise<string> {
  const carga = `v1.${Date.now() + 12 * 3600 * 1000}`
  return `${carga}.${await hmac(carga)}`
}

export async function proxy(req: NextRequest) {
  const valido = await validar(req.cookies.get(COOKIE)?.value ?? '')
  if (valido) return NextResponse.next()
  const { pathname } = req.nextUrl
  if (pathname.startsWith('/api/')) {
    return NextResponse.json({ error: 'Sesión no iniciada' }, { status: 401 })
  }
  return NextResponse.redirect(new URL('/login', req.url))
}

export default proxy

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|login|api/auth).*)'],
}
