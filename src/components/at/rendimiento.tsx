'use client'

// ANÁLISIS DE RENDIMIENTO — serie mensual, comparación interanual, tendencia, consistencia y exportación
import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Loader2 } from 'lucide-react'
import { Kpi, TituloSeccion, api, useDeportistas, BotonesExportar } from './ui-at'
import { TooltipEst, LeyendaLineas, GraficoBarras } from './charts'
import { MESES_ES } from '@/lib/periodos'

type Resumen = { pruebas: string[]; anios: number[] }

type Analisis = {
  depId: number; nombre: string; categoria: string; sexo: string; prueba: string; unidad: string; anio: number
  nAnio: number; nHistorico: number
  pb: { marca: string; fecha: string; competencia: string; valor: number } | null
  mejorAnio: { marca: string; fecha: string; competencia: string; valor: number } | null
  progreso: number | null; pendiente: number | null; tendencia: string; cv: number | null; consistencia: string
  mejorPuestoAnio: number | null
  meses: { mes: number; mesNombre: string; n: number; mejorValor: number | null; mejorMarca: string | null; promedio: number | null; mejorPuesto: number | null }[]
  porAnio: { anio: number; valores: (number | null)[]; mejorMarca: string | null }[]
  registros: { id: number; fecha: string; competencia: string; sede: string | null; nivel: string | null; marca: string; puesto: number | null; deltaPb: number | null }[]
  analisis: string
}

// Variables que el usuario puede elegir para comparar en los gráficos
const VARIABLES = [
  { key: 'mejorValor', etiqueta: 'MEJOR MARCA' },
  { key: 'promedio', etiqueta: 'PROMEDIO' },
  { key: 'n', etiqueta: 'N° DE REGISTROS' },
  { key: 'mejorPuesto', etiqueta: 'MEJOR PUESTO' },
] as const
type VariableKey = (typeof VARIABLES)[number]['key']

const colorTend = (t: string) => (t === 'MEJORA' ? 'bg-green-100 text-green-800' : t === 'RETROCESO' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600')

// regresión lineal simple (y = a + b·x) sobre los puntos no nulos
function regresion(puntos: { x: number; y: number }[]): (x: number) => number | null {
  if (puntos.length < 2) return () => null
  const n = puntos.length
  const sx = puntos.reduce((a, p) => a + p.x, 0), sy = puntos.reduce((a, p) => a + p.y, 0)
  const sxy = puntos.reduce((a, p) => a + p.x * p.y, 0), sxx = puntos.reduce((a, p) => a + p.x * p.x, 0)
  const den = n * sxx - sx * sx
  if (den === 0) return () => null
  const b = (n * sxy - sx * sy) / den, a = (sy - b * sx) / n
  return (x: number) => Math.round((a + b * x) * 1000) / 1000
}

export default function Rendimiento() {
  const { lista } = useDeportistas()
  const [depId, setDepId] = useState('')
  const [prueba, setPrueba] = useState('')
  const [anio, setAnio] = useState(String(new Date().getUTCFullYear()))
  const [variable, setVariable] = useState<VariableKey>('mejorValor')
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [analisis, setAnalisis] = useState<Analisis | null>(null)
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!depId) { setResumen(null); setPrueba(''); setAnalisis(null); return }
    api<Resumen>(`/api/rendimiento?depId=${depId}`).then((r) => {
      setResumen(r)
      setPrueba((p) => (r.pruebas.includes(p) ? p : (r.pruebas[0] ?? '')))
    }).catch(() => setResumen(null))
  }, [depId])

  useEffect(() => {
    if (!depId || !prueba) { setAnalisis(null); return }
    let vive = true
    setCargando(true)
    api<Analisis>(`/api/rendimiento?depId=${depId}&prueba=${encodeURIComponent(prueba)}&anio=${anio}`)
      .then((a) => { if (vive) setAnalisis(a) })
      .catch(() => { if (vive) setAnalisis(null) })
      .finally(() => { if (vive) setCargando(false) })
    return () => { vive = false }
  }, [depId, prueba, anio])

  // serie mensual del año para la variable elegida + línea de tendencia
  const serieMes = (analisis?.meses ?? []).filter((m) => m.n > 0).map((m, idx) => ({
    mes: m.mesNombre.slice(0, 3),
    valor: m[variable] as number | null,
    promedio: m.promedio,
  }))
  const regresionSerie = regresion(serieMes.map((m, i) => ({ x: i, y: m.valor ?? 0 })).filter((p) => !isNaN(p.y)))
  const serieConTend = serieMes.map((m, i) => ({ ...m, tendencia: regresionSerie(i) }))

  // comparación interanual (una línea por año)
  const filasAnios = MESES_ES.map((_, i) => {
    const fila: Record<string, string | number | null> = { mes: MESES_ES[i].slice(0, 3) }
    analisis?.porAnio.forEach((a) => { fila[String(a.anio)] = a.valores[i] })
    return fila
  })
  const aniosOrden = (analisis?.porAnio ?? []).map((a) => String(a.anio))

  const invertirEje = variable === 'mejorPuesto' // puesto 1 es mejor

  // estilo compartido de ejes para los gráficos de líneas (limpio y legible en PC y celular)
  const ejeX = <XAxis dataKey="mes" axisLine={{ stroke: '#e2e8f0' }} tickLine={false} interval="preserveStartEnd" tick={{ fontSize: 11, fill: '#64748b' }} />
  const ejeY = (invertir: boolean) => <YAxis reversed={invertir} axisLine={false} tickLine={false} width={34} domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} />
  const grid = <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef2f7" />

  return (
    <div className="space-y-4">
      {/* ===== Selectores ===== */}
      <div className="flex flex-wrap items-center gap-2">
        <select className="h-9 min-w-44 rounded-md border border-slate-300 bg-white px-3 text-sm" value={depId} onChange={(e) => setDepId(e.target.value)}>
          <option value="">— Deportista —</option>
          {lista.map((d) => <option key={d.id} value={d.id}>{d.apellidoPaterno} {d.apellidoMaterno} {d.nombres}</option>)}
        </select>
        <select className="h-9 min-w-36 rounded-md border border-slate-300 bg-white px-3 text-sm" value={prueba} onChange={(e) => setPrueba(e.target.value)} disabled={!resumen?.pruebas.length}>
          <option value="">— Prueba —</option>
          {(resumen?.pruebas ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select className="h-9 w-28 rounded-md border border-slate-300 bg-white px-3 text-sm" value={anio} onChange={(e) => setAnio(e.target.value)} disabled={!resumen?.anios.length}>
          {(resumen?.anios.length ? resumen.anios : [new Date().getUTCFullYear()]).map((a) => <option key={a} value={a}>AÑO {a}</option>)}
        </select>
        {analisis && <span className="text-sm font-medium text-slate-600">{analisis.nombre} · {analisis.categoria} · {analisis.prueba}</span>}
        <div className="ml-auto">
          {analisis && (
            <BotonesExportar
              params={{ tipo: 'rendimiento', depId: String(depId), prueba, anio }}
              nombreBase={`ANALISIS DE RENDIMIENTO - ${analisis.nombre} - ${prueba} - ${anio}`}
            />
          )}
        </div>
      </div>

      {!depId && <p className="rounded-xl border bg-white p-8 text-center text-sm text-slate-500 shadow-sm">Selecciona un deportista para analizar su rendimiento por prueba, mes y año.</p>}

      {depId && cargando && <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-red-800" /></div>}

      {depId && !cargando && !analisis && <p className="rounded-xl border bg-white p-8 text-center text-sm text-slate-500 shadow-sm">El deportista no tiene registros suficientes para este análisis.</p>}

      {analisis && !cargando && (
        <>
          {/* ===== KPIs técnicos ===== */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            <Kpi titulo="PB histórica" valor={analisis.pb?.marca ?? '—'} detalle={analisis.pb ? analisis.pb.fecha.slice(0, 10) : ''} />
            <Kpi titulo="Mejor del año" valor={analisis.mejorAnio?.marca ?? '—'} detalle={analisis.mejorAnio ? `${analisis.mejorAnio.competencia.slice(0, 24)}` : ''} />
            <Kpi titulo="Progreso" valor={analisis.progreso != null ? `${analisis.progreso > 0 ? '+' : ''}${analisis.progreso} %` : '—'} detalle="vs 1ª marca del año" />
            <Kpi titulo="Tendencia" valor={analisis.tendencia} detalle={analisis.pendiente != null ? `${analisis.pendiente > 0 ? '+' : ''}${analisis.pendiente} ${analisis.unidad === 'seg' ? 's' : 'm'}/mes` : ''} />
            <Kpi titulo="Consistencia" valor={analisis.consistencia} detalle={analisis.cv != null ? `CV ${analisis.cv} %` : ''} />
            <Kpi titulo="Participaciones" valor={analisis.nAnio} detalle={`${analisis.nHistorico} históricas`} />
            <Kpi titulo="Mejor puesto" valor={analisis.mejorPuestoAnio ?? '—'} detalle={`año ${analisis.anio}`} />
          </div>

          {/* ===== Análisis técnico (texto) ===== */}
          <div className="rounded-xl border border-l-4 border-l-red-800 bg-white p-4 text-sm leading-relaxed text-slate-700 shadow-sm">
            <TituloSeccion>Análisis técnico de rendimiento</TituloSeccion>
            {analisis.analisis}
            <p className="pt-1 text-[11px] text-slate-400">
              {analisis.unidad === 'seg' ? 'En pruebas de tiempo (seg), una marca menor indica mejora.' : 'En pruebas de distancia (m), una marca mayor indica mejora.'}
            </p>
          </div>

          {/* ===== Selector de variable + gráfico mensual ===== */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <TituloSeccion accion={
              <div className="flex overflow-hidden rounded-md border">
                {VARIABLES.map((v) => (
                  <button key={v.key} className={`px-2.5 py-1.5 text-[11px] font-bold ${variable === v.key ? 'bg-red-800 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`} onClick={() => setVariable(v.key)}>
                    {v.etiqueta}
                  </button>
                ))}
              </div>
            }>
              Serie mensual {anio} — {VARIABLES.find((v) => v.key === variable)?.etiqueta.toLowerCase()} por mes
            </TituloSeccion>
            <div className="h-56 sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={serieConTend} margin={{ top: 8, right: 12, bottom: 0, left: -14 }}>
                  {grid}
                  {ejeX}
                  {ejeY(invertirEje)}
                  <TooltipEst />
                  <Line type="monotone" dataKey="valor" name={VARIABLES.find((v) => v.key === variable)?.etiqueta} stroke="#b91c1c" strokeWidth={3} dot={{ r: 4, strokeWidth: 0, fill: '#b91c1c' }} connectNulls activeDot={{ r: 5 }} />
                  {variable === 'mejorValor' && <Line type="monotone" dataKey="promedio" name="Promedio del mes" stroke="#7c2d12" strokeWidth={2} strokeDasharray="6 3" dot={false} connectNulls />}
                  <Line type="monotone" dataKey="tendencia" name="Tendencia (regresión)" stroke="#0284c7" strokeWidth={2} dot={false} connectNulls strokeDasharray="2 4" />
                </LineChart>
              </ResponsiveContainer>
              <LeyendaLineas items={[
                { clave: VARIABLES.find((v) => v.key === variable)?.etiqueta ?? '', color: '#b91c1c' },
                ...(variable === 'mejorValor' ? [{ clave: 'Promedio del mes', color: '#7c2d12' }] : []),
                { clave: 'Tendencia (regresión)', color: '#0284c7' },
              ]} />
            </div>
          </div>

          {/* ===== Comparación interanual ===== */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <TituloSeccion>Comparación interanual — mejor marca de cada mes por año</TituloSeccion>
            <div className="h-56 sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filasAnios} margin={{ top: 8, right: 12, bottom: 0, left: -14 }}>
                  {grid}
                  {ejeX}
                  {ejeY(false)}
                  <TooltipEst />
                  {aniosOrden.map((a, i) => (
                    <Line key={a} type="monotone" dataKey={a} name={`AÑO ${a}`} stroke={['#b91c1c', '#ea580c', '#ca8a04', '#166534', '#57534e', '#0284c7'][i % 6]} strokeWidth={2.5} connectNulls dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <LeyendaLineas items={aniosOrden.map((a, i) => ({ clave: `AÑO ${a}`, color: ['#b91c1c', '#ea580c', '#ca8a04', '#166534', '#57534e', '#0284c7'][i % 6] }))} />
            </div>
          </div>

          {/* ===== Participaciones por mes ===== */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <TituloSeccion>Carga de competencias — registros por mes ({anio})</TituloSeccion>
            <GraficoBarras data={analisis.meses.map((m) => ({ clave: m.mesNombre.slice(0, 3), total: m.n }))} color="#b91c1c" alto="h-40 sm:h-44" ocultarCeros />
          </div>

          {/* ===== Tabla de registros del año ===== */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <TituloSeccion accion={<span className="text-[11px] font-semibold text-slate-500">{analisis.registros.length} registros en {anio}</span>}>
              Registros del año — {analisis.prueba} (Δ% respecto a la PB)
            </TituloSeccion>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-xs">
                <thead>
                  <tr className="bg-red-50 text-left text-red-900">
                    {['N°', 'FECHA', 'COMPETENCIA', 'SEDE', 'NIVEL', 'MARCA', 'PUESTO', 'Δ vs PB'].map((h) => <th key={h} className="border px-2 py-1.5 font-bold">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {analisis.registros.length === 0 && <tr><td colSpan={8} className="py-6 text-center text-slate-500">Sin registros en el año {anio}</td></tr>}
                  {analisis.registros.map((r, i) => (
                    <tr key={r.id} className={i % 2 ? 'bg-slate-50' : ''}>
                      <td className="border px-2 py-1.5 text-center">{i + 1}</td>
                      <td className="border px-2 py-1.5">{r.fecha.slice(0, 10)}</td>
                      <td className="border px-2 py-1.5">{r.competencia}</td>
                      <td className="border px-2 py-1.5 text-slate-600">{r.sede ?? '—'}</td>
                      <td className="border px-2 py-1.5 text-slate-600">{r.nivel ?? '—'}</td>
                      <td className="border px-2 py-1.5 text-center font-bold text-red-900">{r.marca}</td>
                      <td className="border px-2 py-1.5 text-center">{r.puesto ?? '—'}</td>
                      <td className={`border px-2 py-1.5 text-center font-semibold ${r.deltaPb != null && r.deltaPb > 0 ? 'text-slate-500' : r.deltaPb === 0 ? 'text-green-700' : 'text-green-700'}`}>
                        {r.deltaPb == null ? '—' : r.deltaPb === 0 ? 'PB' : `${r.deltaPb > 0 ? '+' : ''}${r.deltaPb} %`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
