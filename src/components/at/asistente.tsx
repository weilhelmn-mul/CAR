'use client'

// ASISTENTE IA — chat técnico deportivo
import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send, Sparkles, Bot, Loader2 } from 'lucide-react'
import { api, useDeportistas, nombreCompletoUI } from './ui-at'

type Msg = { role: 'user' | 'ia'; texto: string }

const SUGERENCIAS = [
  '¿Cómo debo redactar los objetivos del AT-F3 para un velocista U-18?',
  'Explícame la diferencia entre preparación general y específica en fondo.',
  '¿Qué puntos técnicos debe cubrir el informe AT-F9?',
  'Sugiere un microciclo semanal para mediofondistas en altura.',
]

export default function Asistente() {
  const { lista } = useDeportistas()
  const [mensajes, setMensajes] = useState<Msg[]>([
    { role: 'ia', texto: 'Hola 👋 Soy el asistente técnico del Sistema AT (DINADAF · IPD). Puedo ayudarte a redactar objetivos, evaluaciones e informes con lenguaje de las ciencias del deporte, o responder consultas sobre los formatos AT, categorías, alimentación y seguro. ¿En qué te ayudo?' },
  ])
  const [texto, setTexto] = useState('')
  const [cargando, setCargando] = useState(false)
  const [conContexto, setConContexto] = useState<number | null>(null)
  const fin = useRef<HTMLDivElement>(null)

  const enviar = async (mensaje: string) => {
    const m = mensaje.trim()
    if (!m || cargando) return
    setMensajes((ms) => [...ms, { role: 'user', texto: m }])
    setTexto('')
    setCargando(true)
    setTimeout(() => fin.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    try {
      const dep = lista.find((d) => d.id === conContexto)
      const r = await api<{ texto: string }>('/api/ia', {
        method: 'POST',
        body: JSON.stringify({ tipo: 'chat', mensaje: m, contexto: dep ? `Deportista seleccionado: ${nombreCompletoUI(dep)}, categoría ${dep.categoria}, ${dep.sexo}, prueba ${dep.prueba ?? 'no indicada'}` : null }),
      })
      setMensajes((ms) => [...ms, { role: 'ia', texto: r.texto }])
    } catch (e) {
      setMensajes((ms) => [...ms, { role: 'ia', texto: `⚠️ ${e instanceof Error ? e.message : 'Error del asistente'}` }])
    } finally {
      setCargando(false)
      setTimeout(() => fin.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-220px)] min-h-96 max-w-4xl flex-col rounded-xl border bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-2 border-b bg-red-50 px-4 py-2">
        <Bot className="h-5 w-5 text-red-800" />
        <p className="text-sm font-bold text-red-900">Asistente IA · Ciencias del Deporte</p>
        <select className="ml-auto h-8 rounded-md border bg-white px-2 text-xs" value={conContexto ?? ''} onChange={(e) => setConContexto(Number(e.target.value) || null)}>
          <option value="">Sin contexto de deportista</option>
          {lista.map((d) => <option key={d.id} value={d.id}>Contexto: {nombreCompletoUI(d)}</option>)}
        </select>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {mensajes.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === 'user' ? 'bg-red-800 text-white' : 'border bg-slate-50 text-slate-800'}`}>
              {m.texto}
            </div>
          </div>
        ))}
        {cargando && (
          <div className="flex justify-start"><div className="flex items-center gap-2 rounded-2xl border bg-slate-50 px-4 py-2.5 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Redactando…</div></div>
        )}
        <div ref={fin} />
      </div>

      <div className="border-t p-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {SUGERENCIAS.map((s) => (
            <button key={s} className="rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs text-red-900 hover:bg-red-100" onClick={() => enviar(s)}>
              {s}
            </button>
          ))}
        </div>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); enviar(texto) }}>
          <Input placeholder="Escribe tu consulta técnica…" value={texto} onChange={(e) => setTexto(e.target.value)} disabled={cargando} />
          <Button type="submit" className="bg-red-800 hover:bg-red-900" disabled={cargando || !texto.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
        <p className="mt-1 flex items-center gap-1 text-[11px] text-slate-400"><Sparkles className="h-3 w-3" /> La IA redacta con base en los datos del sistema; revise y ajuste antes de usar en documentos oficiales.</p>
      </div>
    </div>
  )
}
