'use client'

// FORMATO AT-F9 — informe de cumplimiento del plan del mes anterior (con IA)
import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Save, Info } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, SelectorMes, BotonesExportar, BotonIA, etiquetaMes, AreaIA, TituloSeccion } from './ui-at'

type DatosF9 = {
  jefe: string; planificadas: number; cumplidas: number; evaluacionCumplimiento: string
  cumplimientoPreparacion: number | null; asistenciaPromedio: number | null
  dificultades: string; resenaRevision: string; visitas: number | null; evaluacionVisitas: string
  resumenDificultades: string; baseDatos: boolean; calendario: boolean; capacitaciones: boolean
  analisisObjetivos: string; otrosInteres: string; calificacion: string
}

const vacio: DatosF9 = {
  jefe: '', planificadas: 0, cumplidas: 0, evaluacionCumplimiento: '', cumplimientoPreparacion: null,
  asistenciaPromedio: null, dificultades: '', resenaRevision: '', visitas: null, evaluacionVisitas: '',
  resumenDificultades: '', baseDatos: true, calendario: true, capacitaciones: true, analisisObjetivos: '',
  otrosInteres: '', calificacion: 'BUENO',
}

export default function FormatoF9() {
  const mesAnterior = (() => {
    const h = new Date()
    const m = h.getUTCMonth() // 0-based: mes actual - 1
    const y = m === 0 ? h.getUTCFullYear() - 1 : h.getUTCFullYear()
    return `${y}-${String(m === 0 ? 12 : m).padStart(2, '0')}`
  })()
  const [mes, setMes] = useState(mesAnterior)
  const [d, setD] = useState<DatosF9>(vacio)
  const [sugerencia, setSugerencia] = useState<{ asistenciaPromedio: number | null; cumplimientoPreparacion: number | null; informesF3: number } | null>(null)
  const [cargando, setCargando] = useState(false)
  const [iaCargando, setIaCargando] = useState(false)

  const cargar = async () => {
    setCargando(true)
    try {
      const r = await api<{ rec: (DatosF9 & { periodo: string }) | null; sugerencia: typeof sugerencia; base: DatosF9 }>(`/api/formatos?f=f9&periodo=${mes}`)
      setSugerencia(r.sugerencia)
      setD(r.rec ? { ...vacio, ...r.rec } : { ...vacio, jefe: r.base.jefe })
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setCargando(false) }
  }
  useEffect(() => { cargar() }, [mes])

  const guardar = async () => {
    try {
      await api('/api/formatos', { method: 'POST', body: JSON.stringify({ f: 'f9', periodo: mes, ...d }) })
      toast({ title: 'Informe AT-F9 guardado' })
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const generar = async () => {
    setIaCargando(true)
    try {
      const r = await api<{ json: Record<string, string> }>('/api/ia', { method: 'POST', body: JSON.stringify({ tipo: 'f9', periodo: mes, planificadas: d.planificadas, cumplidas: d.cumplidas }) })
      setD((x) => ({
        ...x,
        evaluacionCumplimiento: r.json.evaluacionCumplimiento ?? x.evaluacionCumplimiento,
        dificultades: r.json.dificultades ?? x.dificultades,
        resenaRevision: r.json.resenaRevision ?? x.resenaRevision,
        resumenDificultades: r.json.resumenDificultades ?? x.resumenDificultades,
        analisisObjetivos: r.json.analisisObjetivos ?? x.analisisObjetivos,
        otrosInteres: r.json.otrosInteres ?? x.otrosInteres,
      }))
      toast({ title: 'Secciones redactadas con IA' })
    } catch (e) { toast({ title: 'IA no disponible', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setIaCargando(false) }
  }

  const set = (k: keyof DatosF9, v: unknown) => setD((x) => ({ ...x, [k]: v }))
  const pct = d.planificadas > 0 ? Math.round((d.cumplidas / d.planificadas) * 100) : 0

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <SelectorMes valor={mes} onChange={setMes} />
        <span className="text-sm font-medium text-slate-600">Mes evaluado: {etiquetaMes(mes)} (plan del mes anterior)</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <BotonIA onClick={generar} cargando={iaCargando} />
          <Button size="sm" className="bg-red-800 hover:bg-red-900" onClick={guardar}><Save className="h-4 w-4" /> Guardar</Button>
          <BotonesExportar params={{ tipo: 'f9', periodo: mes }} nombreBase={`FORMATO AT-F9 - ${etiquetaMes(mes)}`} />
        </div>
      </div>

      {sugerencia && (sugerencia.asistenciaPromedio != null || sugerencia.cumplimientoPreparacion != null) && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <p>Según los AT-F3 del mes ({sugerencia.informesF3} informes): asistencia promedio <b>{sugerencia.asistenciaPromedio ?? '—'} %</b> · cumplimiento promedio <b>{sugerencia.cumplimientoPreparacion ?? '—'} %</b>. Puede usarlos en las secciones 2 del informe.</p>
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <label className="text-xs font-medium text-slate-600">Nombres y apellidos (Jefe de Unidad Técnica)
          <Input value={d.jefe} onChange={(e) => set('jefe', e.target.value)} /></label>
        <div className="grid grid-cols-3 gap-2">
          <label className="text-xs font-medium text-slate-600">Tareas planificadas
            <Input type="number" value={d.planificadas} onChange={(e) => set('planificadas', Number(e.target.value))} /></label>
          <label className="text-xs font-medium text-slate-600">Cumplidas
            <Input type="number" value={d.cumplidas} onChange={(e) => set('cumplidas', Number(e.target.value))} /></label>
          <div className="text-xs font-medium text-slate-600">% cumplimiento
            <div className="flex h-9 items-center justify-center rounded-md border bg-red-50 font-bold text-red-900">{pct} %</div></div>
        </div>
      </div>

      <AreaIA etiqueta="1. Evaluación del cumplimiento de las tareas/actividades" valor={d.evaluacionCumplimiento} onChange={(v) => set('evaluacionCumplimiento', v)} onGenerar={generar} cargando={iaCargando} filas={2} />

      <div className="grid gap-3 rounded-xl border bg-white p-3 shadow-sm sm:grid-cols-2">
        <TituloSeccion>2. Reuniones de trabajo educativo</TituloSeccion>
        <div />
        <label className="text-xs font-medium text-slate-600">% cumplimiento de la preparación del deportista
          <Input type="number" step="0.1" value={d.cumplimientoPreparacion ?? ''} onChange={(e) => set('cumplimientoPreparacion', e.target.value === '' ? null : Number(e.target.value))} /></label>
        <label className="text-xs font-medium text-slate-600">% de asistencia a los entrenamientos
          <Input type="number" step="0.1" value={d.asistenciaPromedio ?? ''} onChange={(e) => set('asistenciaPromedio', e.target.value === '' ? null : Number(e.target.value))} /></label>
        <div className="sm:col-span-2">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-600">Dificultades analizadas</label>
          <textarea className="mt-1 min-h-20 w-full rounded-md border border-slate-300 p-2 text-sm" rows={3} value={d.dificultades} onChange={(e) => set('dificultades', e.target.value)} />
        </div>
      </div>

      <div className="grid gap-3">
        <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-600">3. Reseña de la evaluación, revisión y chequeo de la documentación técnico-metodológica
          <textarea className="min-h-20 rounded-md border border-slate-300 p-2 text-sm" rows={3} value={d.resenaRevision} onChange={(e) => set('resenaRevision', e.target.value)} /></label>
        <div className="grid grid-cols-2 gap-3 rounded-xl border bg-white p-3 shadow-sm sm:grid-cols-4">
          <label className="text-xs font-medium text-slate-600">Cantidad de visitas
            <Input type="number" value={d.visitas ?? ''} onChange={(e) => set('visitas', e.target.value === '' ? null : Number(e.target.value))} /></label>
          <label className="text-xs font-medium text-slate-600">Evaluación (ej. 18/20)
            <Input value={d.evaluacionVisitas} onChange={(e) => set('evaluacionVisitas', e.target.value)} /></label>
          <label className="flex items-end gap-2 pb-1 text-xs font-medium"><input type="checkbox" className="h-4 w-4 accent-red-800" checked={d.baseDatos} onChange={(e) => set('baseDatos', e.target.checked)} /> Actualización base de datos</label>
          <label className="flex items-end gap-2 pb-1 text-xs font-medium"><input type="checkbox" className="h-4 w-4 accent-red-800" checked={d.calendario} onChange={(e) => set('calendario', e.target.checked)} /> Cumplimiento del calendario</label>
          <label className="flex items-end gap-2 pb-1 text-xs font-medium"><input type="checkbox" className="h-4 w-4 accent-red-800" checked={d.capacitaciones} onChange={(e) => set('capacitaciones', e.target.checked)} /> Capacitaciones realizadas</label>
        </div>
        <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-600">Resumen de dificultades de las visitas técnicas
          <textarea className="min-h-20 rounded-md border border-slate-300 p-2 text-sm" rows={3} value={d.resumenDificultades} onChange={(e) => set('resumenDificultades', e.target.value)} /></label>
        <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-600">5. Análisis del cumplimiento de los objetivos permanentes del plan operativo
          <textarea className="min-h-20 rounded-md border border-slate-300 p-2 text-sm" rows={3} value={d.analisisObjetivos} onChange={(e) => set('analisisObjetivos', e.target.value)} /></label>
        <label className="grid gap-1 text-xs font-semibold uppercase tracking-wide text-slate-600">6. Otros datos de interés
          <textarea className="min-h-16 rounded-md border border-slate-300 p-2 text-sm" rows={2} value={d.otrosInteres} onChange={(e) => set('otrosInteres', e.target.value)} /></label>
        <div className="flex items-center gap-4 rounded-xl border bg-white p-3 shadow-sm">
          <p className="text-xs font-bold uppercase text-red-900">8. Evaluación del cumplimiento del plan:</p>
          {['BUENO', 'REGULAR', 'MALO'].map((c) => (
            <label key={c} className="flex items-center gap-1 text-sm font-medium">
              <input type="radio" name="calif" className="h-4 w-4 accent-red-800" checked={d.calificacion === c} onChange={() => set('calificacion', c)} /> {c}
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
