'use client'

// FORMATO AT-F8 — plan de trabajo mensual del JUT (con generación IA)
import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Save, Plus, Trash2 } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, SelectorMes, BotonesExportar, BotonIA, etiquetaMes, TituloSeccion } from './ui-at'

type Act = { actividad: string; fecha: string; hora: string; lugar: string; observaciones: string }

export default function FormatoF8() {
  const [mes, setMes] = useState(new Date().toISOString().slice(0, 7))
  const [jefe, setJefe] = useState('')
  const [acts, setActs] = useState<Act[]>([])
  const [cargando, setCargando] = useState(false)
  const [iaCargando, setIaCargando] = useState(false)

  const cargar = async () => {
    setCargando(true)
    try {
      const r = await api<{ periodo: string; jefe: string | null; actividades: Act[] }>(`/api/formatos?f=f8&periodo=${mes}`)
      setJefe(r.jefe ?? '')
      setActs(r.actividades ?? [])
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setCargando(false) }
  }
  useEffect(() => { cargar() }, [mes])

  const guardar = async () => {
    try {
      await api('/api/formatos', { method: 'POST', body: JSON.stringify({ f: 'f8', periodo: mes, jefe, actividades: acts }) })
      toast({ title: 'Plan AT-F8 guardado' })
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const generar = async () => {
    setIaCargando(true)
    try {
      const r = await api<{ json: { actividades: Act[] } }>('/api/ia', { method: 'POST', body: JSON.stringify({ tipo: 'f8', periodo: mes }) })
      setActs(r.json.actividades ?? [])
      toast({ title: `Plan generado: ${r.json.actividades?.length ?? 0} actividades` })
    } catch (e) { toast({ title: 'IA no disponible', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setIaCargando(false) }
  }

  const setAct = (i: number, k: keyof Act, v: string) => setActs((a) => a.map((x, j) => j === i ? { ...x, [k]: v } : x))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <SelectorMes valor={mes} onChange={setMes} />
        <span className="text-sm font-medium text-slate-600">PLAN DE TRABAJO MENSUAL DEL JUT · {etiquetaMes(mes)}</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <BotonIA onClick={generar} cargando={iaCargando} />
          <Button size="sm" className="bg-red-800 hover:bg-red-900" onClick={guardar}><Save className="h-4 w-4" /> Guardar</Button>
          <BotonesExportar params={{ tipo: 'f8', periodo: mes }} nombreBase={`FORMATO AT-F8 - ${etiquetaMes(mes)}`} />
        </div>
      </div>

      <div className="rounded-xl border bg-white p-3 shadow-sm">
        <TituloSeccion>Datos del responsable</TituloSeccion>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-xs font-medium text-slate-600">Federación
            <Input value="FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO" readOnly className="bg-slate-100" /></label>
          <label className="text-xs font-medium text-slate-600">Nombres y apellidos (Jefe de Unidad Técnica)
            <Input value={jefe} onChange={(e) => setJefe(e.target.value)} placeholder="NOMBRES Y APELLIDOS" /></label>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-3 shadow-sm">
        <TituloSeccion accion={
          <Button size="sm" variant="outline" className="border-red-800 text-red-900" onClick={() => setActs((a) => [...a, { actividad: '', fecha: '', hora: '', lugar: '', observaciones: '' }])}>
            <Plus className="h-4 w-4" /> Añadir actividad
          </Button>
        }>Actividades / tareas del mes</TituloSeccion>
        <div className="max-h-[55vh] overflow-y-auto">
          <table className="w-full text-xs">
            <thead><tr className="bg-red-50">
              {['N°', 'ACTIVIDAD / TAREA', 'FECHA', 'HORA', 'LUGAR', 'OBSERVACIONES', ''].map((h) => <th key={h} className="border p-1 text-red-900">{h}</th>)}
            </tr></thead>
            <tbody>
              {acts.length === 0 && <tr><td colSpan={7} className="py-6 text-center text-slate-500">Sin actividades. Genere el plan con IA o añada manualmente.</td></tr>}
              {acts.map((a, i) => (
                <tr key={i}>
                  <td className="border p-1 text-center font-bold">{i + 1}</td>
                  <td className="border p-0"><textarea className="min-h-10 w-full px-1 py-1 focus:bg-amber-50 focus:outline-none" rows={2} value={a.actividad} onChange={(e) => setAct(i, 'actividad', e.target.value)} /></td>
                  <td className="border p-0"><input className="w-24 px-1 py-1 text-center focus:bg-amber-50 focus:outline-none" value={a.fecha} onChange={(e) => setAct(i, 'fecha', e.target.value)} placeholder="DD/MM/AAAA" /></td>
                  <td className="border p-0"><input className="w-16 px-1 py-1 text-center focus:bg-amber-50 focus:outline-none" value={a.hora} onChange={(e) => setAct(i, 'hora', e.target.value)} /></td>
                  <td className="border p-0"><input className="w-36 px-1 py-1 focus:bg-amber-50 focus:outline-none" value={a.lugar} onChange={(e) => setAct(i, 'lugar', e.target.value)} /></td>
                  <td className="border p-0"><input className="w-full px-1 py-1 focus:bg-amber-50 focus:outline-none" value={a.observaciones} onChange={(e) => setAct(i, 'observaciones', e.target.value)} /></td>
                  <td className="border p-1 text-center"><button className="text-red-600" onClick={() => setActs((a) => a.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
