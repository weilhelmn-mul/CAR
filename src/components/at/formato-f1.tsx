'use client'

// FORMATO AT-F1 — informe mensual consolidado del CAR (con IA para secciones narrativas)
import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Save, Table2 } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, SelectorMes, BotonesExportar, BotonIA, etiquetaMes, TituloSeccion } from './ui-at'

type Matricula = { cat: string; retiros: number; ingresos: number; damas: number; varones: number; total: number; sesiones: number; manana: string; tarde: string }
type Fila = { deportistaId: number; nombre: string; deporte: string; nivel: string; asistencia: number | null; cumplimiento: number | null; observaciones: string }
type Textos = Record<string, string>

export default function FormatoF1() {
  const [mes, setMes] = useState(new Date().toISOString().slice(0, 7))
  const [matriculas, setMatriculas] = useState<Matricula[]>([])
  const [filas, setFilas] = useState<Fila[]>([])
  const [textos, setTextos] = useState<Textos>({})
  const [cargando, setCargando] = useState(false)
  const [iaCargando, setIaCargando] = useState(false)

  const cargar = async () => {
    setCargando(true)
    try {
      const r = await api<{ base: { matriculas: Matricula[]; filas: Fila[]; textos: Textos }; rec: { matriculas: Matricula[]; filas: Fila[]; textos: Textos } | null }>(`/api/formatos?f=f1&periodo=${mes}`)
      setMatriculas(r.rec?.matriculas ?? r.base.matriculas)
      setFilas(r.rec?.filas ?? r.base.filas)
      setTextos(r.rec?.textos ?? {})
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setCargando(false) }
  }
  useEffect(() => { cargar() }, [mes])

  const guardar = async () => {
    try {
      await api('/api/formatos', { method: 'POST', body: JSON.stringify({ f: 'f1', periodo: mes, matriculas, filas, textos }) })
      toast({ title: 'Informe AT-F1 guardado' })
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const generarTextos = async () => {
    setIaCargando(true)
    try {
      const f3s = filas.filter((f) => f.asistencia != null)
      const prom = (arr: (number | null)[]) => arr.length ? Math.round((arr.reduce<number>((a, x) => a + (x ?? 0), 0) / arr.length) * 10) / 10 : null
      const r = await api<{ json: Record<string, string> }>('/api/ia', {
        method: 'POST',
        body: JSON.stringify({
          tipo: 'f1_textos', periodo: mes,
          deportistas: filas.length,
          asistenciaPromedio: prom(f3s.map((f) => f.asistencia)),
          cumplimientoPromedio: prom(filas.map((f) => f.cumplimiento)),
          mejoresMarcas: filas.length,
        }),
      })
      setTextos((t) => ({ ...t, ...r.json }))
      toast({ title: 'Secciones redactadas con IA' })
    } catch (e) { toast({ title: 'IA no disponible', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setIaCargando(false) }
  }

  const SECCIONES: [string, string][] = [
    ['valoracionTecnica', 'II-II Valoración de la participación en test/controles/topes/competencias'],
    ['dificultades', 'II-III Principales dificultades en el cumplimiento de los planes'],
    ['valoracionMedica', 'III Valoración médica'],
    ['profilactico', 'III-I Cumplimiento del plan profiláctico / tratamientos'],
    ['balanceNutricional', 'III-II Comportamiento del balance nutricional en K/calorías'],
    ['funcionamientoCar', 'IV Valoración del funcionamiento del CAR'],
    ['aspectosCar', 'IV-I Aspectos negativos y principales logros del CAR'],
    ['otrosAspectos', 'IV-II Otros aspectos de interés'],
  ]

  const setMat = (i: number, k: keyof Matricula, v: string) => setMatriculas((ms) => ms.map((m, j) => j === i ? { ...m, [k]: k === 'cat' ? v : (k === 'manana' || k === 'tarde' ? v : Number(v) || 0), total: k === 'damas' || k === 'varones' ? (k === 'damas' ? Number(v) || 0 : m.varones) + (k === 'varones' ? Number(v) || 0 : m.damas) : m.total } : m))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <SelectorMes valor={mes} onChange={setMes} />
        <span className="text-sm font-medium text-slate-600">CAR CUSCO · {etiquetaMes(mes)}</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <BotonIA onClick={generarTextos} cargando={iaCargando}><Table2 className="h-4 w-4" /> Redactar secciones con IA</BotonIA>
          <Button size="sm" className="bg-red-800 hover:bg-red-900" onClick={guardar}><Save className="h-4 w-4" /> Guardar</Button>
          <BotonesExportar params={{ tipo: 'f1', periodo: mes }} nombreBase={`FORMATO AT-F1 CAR - ${etiquetaMes(mes)}`} />
        </div>
      </div>

      {cargando ? <div className="rounded-xl border bg-white p-10 text-center text-sm text-slate-500">Cargando…</div> : (
        <>
          <div className="rounded-xl border bg-white p-3 shadow-sm">
            <TituloSeccion>I. Comportamiento de las matrículas (editable)</TituloSeccion>
            <div className="overflow-x-auto">
              <table className="w-full min-w-160 text-center text-xs">
                <thead><tr className="bg-red-50">
                  {['CATEGORÍA', 'RETIROS', 'INGRESOS', 'DAMAS', 'VARONES', 'TOTAL', 'N° SESIONES', 'MAÑANA', 'TARDE'].map((h) => <th key={h} className="border p-1 text-red-900">{h}</th>)}
                </tr></thead>
                <tbody>
                  {matriculas.map((m, i) => (
                    <tr key={m.cat}>
                      <td className="border bg-slate-50 p-1 font-bold">{m.cat}</td>
                      {(['retiros', 'ingresos', 'damas', 'varones', 'total', 'sesiones'] as const).map((k) => (
                        <td key={k} className="border p-0">
                          <input type="number" className={`w-full px-1 py-1.5 text-center text-xs focus:bg-amber-50 focus:outline-none ${k === 'total' ? 'bg-slate-100 font-bold' : ''}`} readOnly={k === 'total'} value={m[k]} onChange={(e) => setMat(i, k, e.target.value)} />
                        </td>
                      ))}
                      {(['manana', 'tarde'] as const).map((k) => (
                        <td key={k} className="border p-0"><input className="w-full px-1 py-1.5 text-center text-xs focus:bg-amber-50 focus:outline-none" value={m[k]} onChange={(e) => setMat(i, k, e.target.value)} /></td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border bg-white p-3 shadow-sm">
            <TituloSeccion>II.I Cumplimiento de los planes de entrenamiento (por deportista)</TituloSeccion>
            <p className="mb-2 text-xs text-slate-500">Los porcentajes se toman del AT-F3 de cada deportista; puede ajustarlos y redactar las observaciones aquí.</p>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-xs">
                <thead><tr className="bg-red-50">
                  {['N°', 'NOMBRES Y APELLIDOS', 'DEPORTE', 'PRUEBA/MOD.', '% ASIST.', '% CUMPL.', 'RESULTADOS Y OBSERVACIONES TÉCNICAS'].map((h) => <th key={h} className="border p-1 text-red-900">{h}</th>)}
                </tr></thead>
                <tbody>
                  {filas.map((f, i) => (
                    <tr key={f.deportistaId}>
                      <td className="border p-1 text-center">{i + 1}</td>
                      <td className="border p-1 font-medium">{f.nombre}</td>
                      <td className="border p-1 text-center">{f.deporte}</td>
                      <td className="border p-1 text-center">{f.nivel}</td>
                      <td className="border p-0"><input type="number" step="0.1" className="w-16 px-1 py-1 text-center focus:bg-amber-50 focus:outline-none" value={f.asistencia ?? ''} onChange={(e) => setFilas((fs) => fs.map((x, j) => j === i ? { ...x, asistencia: e.target.value === '' ? null : Number(e.target.value) } : x))} /></td>
                      <td className="border p-0"><input type="number" step="0.1" className="w-16 px-1 py-1 text-center focus:bg-amber-50 focus:outline-none" value={f.cumplimiento ?? ''} onChange={(e) => setFilas((fs) => fs.map((x, j) => j === i ? { ...x, cumplimiento: e.target.value === '' ? null : Number(e.target.value) } : x))} /></td>
                      <td className="border p-0"><input className="w-full px-1 py-1 focus:bg-amber-50 focus:outline-none" value={f.observaciones} onChange={(e) => setFilas((fs) => fs.map((x, j) => j === i ? { ...x, observaciones: e.target.value } : x))} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            {SECCIONES.map(([k, lbl]) => (
              <div key={k} className="rounded-xl border bg-white p-3 shadow-sm">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <p className="text-xs font-bold uppercase text-red-900">{lbl}</p>
                  <BotonIA cargando={false} onClick={() => {
                    if (!textos[k]) toast({ title: 'Sugerencia', description: 'Use "Redactar secciones con IA" para generar todas las secciones de una vez.' })
                  }} />
                </div>
                <textarea className="min-h-20 w-full rounded-md border border-slate-300 p-2 text-sm" rows={4} value={textos[k] ?? ''} onChange={(e) => setTextos((t) => ({ ...t, [k]: e.target.value }))} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
