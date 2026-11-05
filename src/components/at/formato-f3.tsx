'use client'

// FORMATO AT-F3 — informe técnico mensual por deportista (con IA)
import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Save } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, useDeportistas, SelectorMes, BotonesExportar, AreaIA, etiquetaMes, nombreCompletoUI, TituloSeccion } from './ui-at'
import { DIAS_SEM, HORARIO_DEFAULT } from '@/lib/periodos'

type DatosF3 = {
  objetivos: string; horario: { manana: string[]; tarde: string[]; noche: string[] }
  asistencia: number | null; cumplimiento: number | null; testControles: string
  detallePreparacion: string; competencias: string; cumplimientoObjetivos: string
  evaluacionGeneral: string; observaciones: string
}

const vacio: DatosF3 = { objetivos: '', horario: HORARIO_DEFAULT, asistencia: null, cumplimiento: null, testControles: '', detallePreparacion: '', competencias: '', cumplimientoObjetivos: '', evaluacionGeneral: '', observaciones: '' }

type CampoIA = 'f3_objetivos' | 'f3_testControles' | 'f3_detallePreparacion' | 'f3_competencias' | 'f3_cumplimientoObjetivos' | 'f3_evaluacionGeneral'

export default function FormatoF3() {
  const { lista } = useDeportistas()
  const [depId, setDepId] = useState<number | null>(null)
  const [mes, setMes] = useState(new Date().toISOString().slice(0, 7))
  const [datos, setDatos] = useState<DatosF3>(vacio)
  const [cargando, setCargando] = useState(false)
  const [iaCargando, setIaCargando] = useState<string | null>(null)

  useEffect(() => {
    if (!depId) return
    setCargando(true)
    api<DatosF3>(`/api/formatos/f3?deportistaId=${depId}&periodo=${mes}`)
      .then((d) => setDatos({ ...vacio, ...d, horario: d.horario ?? HORARIO_DEFAULT }))
      .catch((e) => toast({ title: 'Error', description: e.message, variant: 'destructive' }))
      .finally(() => setCargando(false))
  }, [depId, mes])

  const guardar = async () => {
    if (!depId) return
    try {
      await api('/api/formatos/f3', { method: 'POST', body: JSON.stringify({ deportistaId: depId, periodo: mes, ...datos }) })
      toast({ title: 'Informe AT-F3 guardado' })
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const generar = async (campo: CampoIA) => {
    if (!depId) { toast({ title: 'Seleccione un deportista primero' }); return }
    setIaCargando(campo)
    try {
      const r = await api<{ texto: string }>('/api/ia', { method: 'POST', body: JSON.stringify({ tipo: campo, depId, periodo: mes }) })
      setDatos((d) => ({ ...d, [campo.replace('f3_', '')]: r.texto }))
    } catch (e) { toast({ title: 'IA no disponible', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setIaCargando(null) }
  }

  const set = (k: keyof DatosF3, v: unknown) => setDatos((d) => ({ ...d, [k]: v }))
  const dep = lista.find((x) => x.id === depId)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <select className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm" value={depId ?? ''} onChange={(e) => setDepId(Number(e.target.value) || null)}>
          <option value="">— Seleccione deportista —</option>
          {lista.map((d) => <option key={d.id} value={d.id}>{nombreCompletoUI(d)} ({d.categoria})</option>)}
        </select>
        <SelectorMes valor={mes} onChange={setMes} />
        {dep && <span className="text-sm text-slate-500">{dep.deporte} · {dep.prueba ?? 's/prueba'} · {dep.entrenador ?? 's/entrenador'}</span>}
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" className="bg-red-800 hover:bg-red-900" disabled={!depId} onClick={guardar}><Save className="h-4 w-4" /> Guardar</Button>
          <BotonesExportar params={{ tipo: 'f3', depId: String(depId ?? ''), periodo: mes }} nombreBase={`FORMATO AT-F3 - ${dep ? nombreCompletoUI(dep) : ''} - ${etiquetaMes(mes)}`} />
        </div>
      </div>

      {!depId ? (
        <div className="rounded-xl border border-dashed bg-white p-10 text-center text-sm text-slate-500">
          Seleccione un deportista para redactar su informe técnico mensual (FORMATO AT-F3).
        </div>
      ) : cargando ? (
        <div className="rounded-xl border bg-white p-10 text-center text-sm text-slate-500">Cargando informe…</div>
      ) : (
        <div className="space-y-4">
          <AreaIA etiqueta="1. Objetivos y metas de la preparación" valor={datos.objetivos} onChange={(v) => set('objetivos', v)} onGenerar={() => generar('f3_objetivos')} cargando={iaCargando === 'f3_objetivos'} />

          <div className="rounded-xl border bg-white p-3 shadow-sm">
            <TituloSeccion>2. Horario de entrenamiento (semana tipo)</TituloSeccion>
            <div className="overflow-x-auto">
              <table className="w-full min-w-160 text-center text-xs">
                <thead><tr className="bg-red-50">
                  <th className="border p-1 text-red-900">SESIÓN</th>{DIAS_SEM.map((d) => <th key={d} className="border p-1 text-red-900">{d}</th>)}
                </tr></thead>
                <tbody>
                  {(['manana', 'tarde', 'noche'] as const).map((fila, i) => (
                    <tr key={fila}>
                      <td className="border bg-slate-50 p-1 font-bold">{['MAÑANA', 'TARDE', 'NOCHE'][i]}</td>
                      {DIAS_SEM.map((_, j) => (
                        <td key={j} className="border p-0">
                          <input className="w-full min-w-16 px-1 py-1.5 text-center text-xs focus:bg-amber-50 focus:outline-none" value={datos.horario[fila]?.[j] ?? ''} onChange={(e) => {
                            const copia = { ...datos.horario, [fila]: [...(datos.horario[fila] ?? [])] }
                            copia[fila][j] = e.target.value
                            set('horario', copia)
                          }} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="rounded-xl border bg-white p-3 shadow-sm text-sm">
              <span className="text-xs font-bold uppercase text-red-900">3. % de asistencia a los entrenamientos</span>
              <Input type="number" step="0.1" min="0" max="100" className="mt-2" value={datos.asistencia ?? ''} onChange={(e) => set('asistencia', e.target.value === '' ? null : Number(e.target.value))} />
            </label>
            <label className="rounded-xl border bg-white p-3 shadow-sm text-sm">
              <span className="text-xs font-bold uppercase text-red-900">4. % de cumplimiento del plan de entrenamiento</span>
              <Input type="number" step="0.1" min="0" max="100" className="mt-2" value={datos.cumplimiento ?? ''} onChange={(e) => set('cumplimiento', e.target.value === '' ? null : Number(e.target.value))} />
            </label>
          </div>

          <AreaIA etiqueta="5. Resultados de los test pedagógicos, controles internos y avances" valor={datos.testControles} onChange={(v) => set('testControles', v)} onGenerar={() => generar('f3_testControles')} cargando={iaCargando === 'f3_testControles'} />
          <AreaIA etiqueta="6. Detalle de la preparación en la etapa o periodo actual" valor={datos.detallePreparacion} onChange={(v) => set('detallePreparacion', v)} onGenerar={() => generar('f3_detallePreparacion')} cargando={iaCargando === 'f3_detallePreparacion'} />
          <AreaIA etiqueta="7. Participación en competencias nacionales e internacionales" valor={datos.competencias} onChange={(v) => set('competencias', v)} onGenerar={() => generar('f3_competencias')} cargando={iaCargando === 'f3_competencias'} />
          <AreaIA etiqueta="8. Cumplimiento de los objetivos del entrenamiento y/o competencias" valor={datos.cumplimientoObjetivos} onChange={(v) => set('cumplimientoObjetivos', v)} onGenerar={() => generar('f3_cumplimientoObjetivos')} cargando={iaCargando === 'f3_cumplimientoObjetivos'} />
          <AreaIA etiqueta="9. Evaluación general de la preparación y progresos deportivos" valor={datos.evaluacionGeneral} onChange={(v) => set('evaluacionGeneral', v)} onGenerar={() => generar('f3_evaluacionGeneral')} cargando={iaCargando === 'f3_evaluacionGeneral'} />

          <div className="grid gap-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Observaciones (se añaden después de la nota oficial)</label>
            <textarea className="min-h-20 rounded-md border border-slate-300 p-2 text-sm" rows={3} value={datos.observaciones} onChange={(e) => set('observaciones', e.target.value)} />
          </div>
        </div>
      )}
    </div>
  )
}
