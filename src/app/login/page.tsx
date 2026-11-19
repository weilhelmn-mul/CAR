'use client'

// Pantalla de ingreso al Sistema de Gestión de Formatos AT — CAR Cusco
import { useState } from 'react'

export default function Login() {
  const [usuario, setUsuario] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function enviar(e: React.FormEvent) {
    e.preventDefault()
    if (cargando) return
    setCargando(true)
    setError('')
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario, contrasena }),
      })
      if (res.ok) {
        window.location.href = '/'
        return
      }
      const d = await res.json().catch(() => ({}))
      setError(d.error || 'No se pudo iniciar sesión')
    } catch {
      setError('No se pudo conectar con el servidor')
    }
    setCargando(false)
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-red-950 via-red-900 to-slate-900 p-4">
      <form onSubmit={enviar} className="w-full max-w-sm space-y-5 rounded-2xl bg-white p-8 shadow-2xl">
        <div className="space-y-2 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-800 text-xl font-black text-white">IPD</div>
          <h1 className="text-xl font-black tracking-tight text-red-900">CAR CUSCO</h1>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            IPD · DINADAF · Sistema de Gestión de Formatos AT
          </p>
        </div>

        <div className="space-y-3">
          <div>
            <label htmlFor="usuario" className="mb-1 block text-xs font-semibold text-slate-600">Usuario</label>
            <input
              id="usuario"
              type="text"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              autoComplete="username"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-red-700 focus:ring-2 focus:ring-red-100"
              placeholder="Usuario del CAR"
            />
          </div>
          <div>
            <label htmlFor="contrasena" className="mb-1 block text-xs font-semibold text-slate-600">Contraseña</label>
            <input
              id="contrasena"
              type="password"
              value={contrasena}
              onChange={(e) => setContrasena(e.target.value)}
              autoComplete="current-password"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-red-700 focus:ring-2 focus:ring-red-100"
              placeholder="••••••••"
            />
          </div>
        </div>

        {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={cargando}
          className="w-full rounded-lg bg-red-800 py-2.5 text-sm font-bold text-white transition-colors hover:bg-red-900 disabled:opacity-60"
        >
          {cargando ? 'Ingresando…' : 'Ingresar'}
        </button>

        <p className="text-center text-[10px] text-slate-400">Centro Alto Rendimiento Cusco · Acceso restringido al personal autorizado</p>
      </form>
    </main>
  )
}
