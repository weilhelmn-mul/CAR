'use client'

// Componentes compartidos del Sistema AT
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { FileSpreadsheet, FileText, Sparkles, Loader2 } from 'lucide-react'
import { MESES_ES } from '@/lib/periodos'

export async function api<T>(url: string, opciones?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...opciones, headers: { 'Content-Type': 'application/json', ...(opciones?.headers ?? {}) } })
  const datos = await res.json()
  if (!res.ok) throw new Error(datos?.error ?? 'Error de comunicación')
  return datos as T
}

export async function descargar(url: string, nombre: string) {
  const res = await fetch(url)
  if (!res.ok) {
    const e = await res.json().catch(() => null)
    throw new Error(e?.error ?? 'Error al generar el archivo')
  }
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 4000)
}

export function Kpi({ titulo, valor, detalle, icono }: { titulo: string; valor: string | number; detalle?: string; icono?: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
        {icono && <span className="text-red-800">{icono}</span>}
      </div>
      <p className="mt-1 text-2xl font-bold text-slate-900">{valor}</p>
      {detalle && <p className="mt-0.5 text-xs text-slate-500">{detalle}</p>}
    </div>
  )
}

export function TituloSeccion({ children, accion }: { children: React.ReactNode; accion?: React.ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
      <h3 className="text-sm font-bold uppercase tracking-wide text-red-900">{children}</h3>
      {accion}
    </div>
  )
}

export function BotonesExportar({ params, nombreBase }: { params: Record<string, string>; nombreBase: string }) {
  const [cargando, setCargando] = useState<'xlsx' | 'pdf' | null>(null)
  const descargar1 = async (formato: 'xlsx' | 'pdf') => {
    setCargando(formato)
    try {
      const qs = new URLSearchParams({ ...params, formato }).toString()
      await descargar(`/api/export?${qs}`, nombreBase + (formato === 'pdf' ? '.pdf' : '.xlsx'))
    } finally {
      setCargando(null)
    }
  }
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="outline" className="border-red-800 text-red-900 hover:bg-red-50" disabled={!!cargando} onClick={() => descargar1('xlsx')}>
        {cargando === 'xlsx' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4" />} Excel
      </Button>
      <Button size="sm" variant="outline" className="border-red-800 text-red-900 hover:bg-red-50" disabled={!!cargando} onClick={() => descargar1('pdf')}>
        {cargando === 'pdf' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />} PDF
      </Button>
    </div>
  )
}

export function BotonIA({ onClick, children, cargando }: { onClick: () => void; children?: React.ReactNode; cargando: boolean }) {
  return (
    <Button size="sm" className="bg-red-800 text-white hover:bg-red-900" disabled={cargando} onClick={onClick}>
      {cargando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
      {children || 'Redactar con IA'}
    </Button>
  )
}

export function AreaIA({ etiqueta, valor, onChange, onGenerar, cargando, filas = 4 }: {
  etiqueta: string; valor: string; onChange: (v: string) => void; onGenerar: () => void; cargando: boolean; filas?: number
}) {
  return (
    <div className="grid gap-1">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-600">{etiqueta}</label>
        <BotonIA onClick={onGenerar} cargando={cargando} />
      </div>
      <textarea
        className="min-h-24 w-full rounded-md border border-slate-300 bg-white p-2 text-sm focus:border-red-700 focus:outline-none"
        rows={filas} value={valor} onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

export function SelectorMes({ valor, onChange, incluirAnio }: { valor: string; onChange: (v: string) => void; incluirAnio?: boolean }) {
  if (incluirAnio) {
    return (
      <select
        className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm"
        value={valor.slice(0, 4)}
        onChange={(e) => onChange(`${e.target.value}-01`)}
      >
        {[2024, 2025, 2026, 2027].map((y) => <option key={y} value={y}>{`AÑO ${y}`}</option>)}
      </select>
    )
  }
  return <input type="month" className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm" value={valor} onChange={(e) => onChange(e.target.value)} />
}

export const etiquetaMes = (ref: string) => {
  const [y, m] = ref.split('-').map(Number)
  return `${MESES_ES[m - 1]} ${y}`
}

export type Deportista = {
  id: number; orden: number; apellidoPaterno: string; apellidoMaterno: string; nombres: string; dni: string
  sexo: string; fechaIngreso: string | null; deporte: string; fechaNacimiento: string; nivelTecnico: string
  modalidad: string; telefono: string | null; procedencia: string; categoria: string; pad: boolean
  entrenador: string | null; prueba: string | null; activo: boolean; retirado: boolean
}

export function useDeportistas() {
  const [lista, setLista] = useState<Deportista[]>([])
  const [cargando, setCargando] = useState(true)
  const recargar = async () => {
    setCargando(true)
    try { setLista(await api<Deportista[]>('/api/deportistas')) } finally { setCargando(false) }
  }
  useEffect(() => { recargar() }, [])
  return { lista, cargando, recargar, setLista }
}

export const nombreCompletoUI = (d: Pick<Deportista, 'apellidoPaterno' | 'apellidoMaterno' | 'nombres'>) =>
  `${d.apellidoPaterno} ${d.apellidoMaterno} ${d.nombres}`.replace(/\s+/g, ' ').trim()

export const BadgeCat = ({ children }: { children: React.ReactNode }) => (
  <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-900">{children}</span>
)

export const PALETA = ['#b91c1c', '#ea580c', '#ca8a04', '#166534', '#57534e', '#7c2d12']
