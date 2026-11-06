'use client'

// INICIO — panel general: KPIs, composición de la población, alertas y actividad del mes
import { useEffect, useMemo, useState } from 'react'
import { Users, ShieldCheck, CalendarDays, Trophy, Activity, HeartPulse, AlertTriangle, Cake, Utensils, BarChart3, Bot, FileSignature, ChevronRight } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts'
import { Kpi, TituloSeccion, api, PALETA, useDeportistas, BadgeCat, estadoAval, calcularEdad, nombreCompletoUI } from './ui-at'
import { MESES_ES, fmtFecha } from '@/lib/periodos'

type Estad = {
  activos: number; pad: number; ingresos: number; resultados: number
  porCategoria: { clave: string; total: number }[]
  porSexo: { clave: string; total: number }[]
  porDeporte: { clave: string; total: number }[]
  porModalidad: { clave: string; total: number }[]
  detalle: { fecha: string; nombre: string; categoria: string; prueba: string; marca: string; puesto: number | null; competencia: string; nivel: string | null }[]
}

const COLOR_AVAL: Record<string, string> = { VIGENTE: '#16a34a', 'POR VENCER': '#d97706', EXPIRADO: '#dc2626', 'SIN REGISTRO': '#94a3b8' }
const GRUPOS_EDAD = ['≤ 15', '16-17', '18-19', '20-22', '23-25', '26+'] as const
const enGrupo = (e: number | null) => (e == null ? -1 : e <= 15 ? 0 : e <= 17 ? 1 : e <= 19 ? 2 : e <= 22 ? 3 : e <= 25 ? 4 : 5)
const DIAS_ALERTA = 60

// Leyenda propia (chips con punto de color): reemplaza la leyenda de recharts para que no se superponga en pantallas pequeñas
const Chips = ({ items }: { items: { clave: string; total: number; color: string }[] }) => (
  <div className="flex flex-wrap justify-center gap-1.5 pt-1">
    {items.map((x) => (
      <span key={x.clave} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: x.color }} />{x.clave}: {x.total}
      </span>
    ))}
  </div>
)

export default function Inicio({ onAbrirFicha, onIrA }: { onAbrirFicha: (id: number) => void; onIrA: (tab: string) => void }) {
  const { lista } = useDeportistas()
  const [est, setEst] = useState<Estad | null>(null)
  const [movil, setMovil] = useState(false)
  const mesHoy = new Date().toISOString().slice(0, 7)

  useEffect(() => {
    api<Estad>(`/api/estadisticas?tipo=MENSUAL&ref=${mesHoy}`).then(setEst).catch(() => null)
  }, [mesHoy])

  // Detecta pantallas pequeñas para redibujar los gráficos (los pasteles se muestran separados)
  useEffect(() => {
    const f = () => setMovil(window.innerWidth < 640)
    f()
    window.addEventListener('resize', f)
    return () => window.removeEventListener('resize', f)
  }, [])

  const activos = useMemo(() => lista.filter((d) => d.activo && !d.retirado), [lista])

  const edades = useMemo(() => activos.map((d) => calcularEdad(d.fechaNacimiento)).filter((e): e is number => e != null), [activos])
  const edadProm = edades.length ? Math.round((edades.reduce((a, b) => a + b, 0) / edades.length) * 10) / 10 : null
  const porEdad = useMemo(() => GRUPOS_EDAD.map((g, i) => ({ clave: g, total: edades.filter((e) => enGrupo(e) === i).length })), [edades])

  const porAval = useMemo(() => {
    const m = new Map<string, number>([['VIGENTE', 0], ['POR VENCER', 0], ['EXPIRADO', 0], ['SIN REGISTRO', 0]])
    activos.forEach((d) => { const t = estadoAval(d.fechaCaducidadAval).texto; m.set(t, (m.get(t) ?? 0) + 1) })
    return [...m.entries()].map(([clave, total]) => ({ clave, total })).filter((x) => x.total > 0)
  }, [activos])

  const alertas = useMemo(() => {
    const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
    const limite = new Date(hoy); limite.setDate(limite.getDate() + DIAS_ALERTA)
    const filas: { id: string; depId: number; nombre: string; tipo: 'AVAL' | 'CONTINUIDAD'; estado: string; fecha: Date | null }[] = []
    activos.forEach((d) => {
      const av = estadoAval(d.fechaCaducidadAval)
      if (av.texto === 'EXPIRADO' || av.texto === 'POR VENCER') {
        filas.push({ id: `a${d.id}`, depId: d.id, nombre: nombreCompletoUI(d), tipo: 'AVAL', estado: av.texto, fecha: d.fechaCaducidadAval ? new Date(d.fechaCaducidadAval) : null })
      }
      if (d.fechaVencimientoContinuidad) {
        const f = new Date(d.fechaVencimientoContinuidad)
        if (f <= limite) filas.push({ id: `c${d.id}`, depId: d.id, nombre: nombreCompletoUI(d), tipo: 'CONTINUIDAD', estado: f < hoy ? 'VENCIDA' : 'POR VENCER', fecha: f })
      }
    })
    return filas.sort((a, b) => (a.fecha?.getTime() ?? 9e15) - (b.fecha?.getTime() ?? 9e15))
  }, [activos])

  const cumpleanosMes = useMemo(() => lista
    .filter((d) => new Date(d.fechaNacimiento).getUTCMonth() === new Date().getUTCMonth())
    .sort((a, b) => new Date(a.fechaNacimiento).getUTCDate() - new Date(b.fechaNacimiento).getUTCDate()), [lista])

  const activosPad = activos.filter((d) => d.pad).length
  const pctPad = activos.length ? Math.round((activosPad / activos.length) * 100) : 0
  const vigentes = porAval.find((x) => x.clave === 'VIGENTE')?.total ?? 0
  const porVencer = porAval.find((x) => x.clave === 'POR VENCER')?.total ?? 0
  const expirados = porAval.find((x) => x.clave === 'EXPIRADO')?.total ?? 0
  const sinAval = porAval.find((x) => x.clave === 'SIN REGISTRO')?.total ?? 0
  const resultadosMes = est?.detalle ?? []
  const badgeAlerta = (e: string) =>
    e === 'VIGENTE' ? 'bg-green-100 text-green-800' : e === 'POR VENCER' ? 'bg-amber-100 text-amber-800' : e === 'VENCIDA' || e === 'EXPIRADO' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-500'

  return (
    <div className="space-y-6">
      {/* ===== KPIs principales ===== */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi titulo="Deportistas activos" valor={est?.activos ?? activos.length} detalle={`${lista.length} registrados en total`} icono={<Users className="h-5 w-5" />} />
        <Kpi titulo="Con seguro PAD" valor={activosPad} detalle={`${pctPad} % del grupo activo`} icono={<ShieldCheck className="h-5 w-5" />} />
        <Kpi titulo="Avales vigentes" valor={vigentes} detalle={`${porVencer} por vencer · ${expirados} expirados`} icono={<HeartPulse className="h-5 w-5" />} />
        <Kpi titulo="Ingresos del mes" valor={est?.ingresos ?? 0} detalle="altas registradas" icono={<CalendarDays className="h-5 w-5" />} />
        <Kpi titulo="Resultados del mes" valor={est?.resultados ?? 0} detalle="marcas registradas" icono={<Trophy className="h-5 w-5" />} />
        <Kpi titulo="Edad promedio" valor={edadProm != null ? `${edadProm} años` : '—'} detalle={edades.length ? `rango ${Math.min(...edades)}–${Math.max(...edades)} años` : 'sin datos'} icono={<Activity className="h-5 w-5" />} />
      </div>

      {/* ===== Gráficos de la población ===== */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion>Composición por categoría</TituloSeccion>
          <div className="h-44 sm:h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={est?.porCategoria ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
                <XAxis dataKey="clave" tick={{ fontSize: 11 }} interval={0} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="total" radius={[6, 6, 0, 0]}>
                  {(est?.porCategoria ?? []).map((_, i) => <Cell key={i} fill={PALETA[i % PALETA.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion>Distribución de edades</TituloSeccion>
          <div className="h-44 sm:h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={porEdad} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
                <XAxis dataKey="clave" tick={{ fontSize: 11 }} interval={0} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [`${v} deportistas`, 'Total']} />
                <Bar dataKey="total" radius={[6, 6, 0, 0]}>{porEdad.map((_, i) => <Cell key={i} fill={PALETA[i % PALETA.length]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion>Sexo y estado del aval médico</TituloSeccion>
          {movil ? (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={est?.porSexo ?? []} dataKey="total" nameKey="clave" cx="50%" cy="50%" innerRadius={20} outerRadius={44}>
                        {(est?.porSexo ?? []).map((_, i) => <Cell key={i} fill={PALETA[i % PALETA.length]} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">Sexo</p>
                <Chips items={(est?.porSexo ?? []).map((x, i) => ({ clave: x.clave, total: x.total, color: PALETA[i % PALETA.length] }))} />
              </div>
              <div>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={porAval} dataKey="total" nameKey="clave" cx="50%" cy="50%" innerRadius={20} outerRadius={44}>
                        {porAval.map((x) => <Cell key={x.clave} fill={COLOR_AVAL[x.clave] ?? '#94a3b8'} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">Aval médico</p>
                <Chips items={porAval.map((x) => ({ clave: x.clave, total: x.total, color: COLOR_AVAL[x.clave] ?? '#94a3b8' }))} />
              </div>
            </div>
          ) : (
            <div>
              <div className="h-44 sm:h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={est?.porSexo ?? []} dataKey="total" nameKey="clave" cx="27%" cy="50%" innerRadius={30} outerRadius={60}>
                      {(est?.porSexo ?? []).map((_, i) => <Cell key={i} fill={PALETA[i % PALETA.length]} />)}
                    </Pie>
                    <Pie data={porAval} dataKey="total" nameKey="clave" cx="73%" cy="50%" innerRadius={30} outerRadius={60}>
                      {porAval.map((x) => <Cell key={x.clave} fill={COLOR_AVAL[x.clave] ?? '#94a3b8'} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <Chips items={[
                ...(est?.porSexo ?? []).map((x, i) => ({ clave: x.clave, total: x.total, color: PALETA[i % PALETA.length] })),
                ...porAval.map((x) => ({ clave: x.clave, total: x.total, color: COLOR_AVAL[x.clave] ?? '#94a3b8' })),
              ]} />
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion>Modalidad · deporte · nivel técnico</TituloSeccion>
          <div className="space-y-1.5">
            {[
              ...(est?.porModalidad ?? []).map((x) => ({ etq: x.clave, total: x.total, tipo: 'MODALIDAD' })),
              ...(est?.porDeporte ?? []).map((x) => ({ etq: x.clave, total: x.total, tipo: 'DEPORTE' })),
            ].map((x, i) => {
              const max = Math.max(1, ...(est?.porModalidad ?? []).map((y) => y.total), ...(est?.porDeporte ?? []).map((y) => y.total))
              return (
                <div key={`${x.tipo}-${x.etq}`} className="flex items-center gap-2">
                  <span className="w-32 shrink-0 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{x.etq}</span>
                  <div className="h-4 flex-1 overflow-hidden rounded bg-slate-100">
                    <div className="h-full rounded bg-red-800" style={{ width: `${(x.total / max) * 100}%` }} />
                  </div>
                  <span className="w-6 text-right text-xs font-bold text-slate-700">{x.total}</span>
                </div>
              )
            })}
            {(est?.porCategoria ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {(est?.porCategoria ?? []).map((c) => <BadgeCat key={c.clave}>{c.clave}: {c.total}</BadgeCat>)}
              </div>
            )}
          </div>
        </div>

        {/* ===== Alertas de vencimiento ===== */}
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion accion={<span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500"><AlertTriangle className="h-3.5 w-3.5 text-amber-600" /> próximos {DIAS_ALERTA} días</span>}>
            Alertas de aval y continuidad
          </TituloSeccion>
          {alertas.length === 0 && <p className="py-6 text-center text-sm text-slate-500">Todo en regla: sin vencimientos próximos</p>}
          <div className="max-h-52 space-y-2 overflow-y-auto pr-1">
            {alertas.map((a) => (
              <button key={a.id} onClick={() => onAbrirFicha(a.depId)} className="flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-left text-sm hover:bg-red-50">
                <span className="min-w-0">
                  <span className="block truncate font-medium">{a.nombre}</span>
                  <span className="text-[11px] text-slate-500">{a.tipo === 'AVAL' ? 'Aval médico' : 'Continuidad CAR'} · {a.fecha ? fmtFecha(a.fecha) : '—'}</span>
                </span>
                <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-bold ${badgeAlerta(a.estado)}`}>{a.estado}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ===== Cumpleaños ===== */}
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion accion={<Cake className="h-4 w-4 text-red-800" />}>Cumpleaños de {MESES_ES[new Date().getUTCMonth()]}</TituloSeccion>
          {cumpleanosMes.length === 0 && <p className="py-6 text-center text-sm text-slate-500">Sin cumpleaños este mes</p>}
          <div className="max-h-52 space-y-2 overflow-y-auto pr-1">
            {cumpleanosMes.map((d) => (
              <button key={d.id} onClick={() => onAbrirFicha(d.id)} className="flex w-full items-center justify-between rounded-lg border px-3 py-1.5 text-left text-sm hover:bg-red-50">
                <span className="font-medium">{d.apellidoPaterno} {d.nombres}</span>
                <span className="text-xs text-slate-500">{fmtFecha(d.fechaNacimiento).slice(0, 5)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ===== Resultados del mes ===== */}
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <TituloSeccion accion={<span className="text-[11px] font-semibold text-slate-500">{resultadosMes.length} registros en el mes</span>}>
          Resultados deportivos de {MESES_ES[new Date().getUTCMonth()]}
        </TituloSeccion>
        {resultadosMes.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">Sin resultados registrados este mes</p>
        ) : (
          <>
            {/* Tabla — tablet y desktop */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-red-900">
                    {['FECHA', 'DEPORTISTA', 'PRUEBA', 'MARCA', 'PUESTO', 'COMPETENCIA'].map((h) => <th key={h} className="px-2 py-1.5 font-bold">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {resultadosMes.slice(0, 8).map((r, i) => (
                    <tr key={i} className={i % 2 ? 'bg-slate-50' : ''}>
                      <td className="px-2 py-1.5 text-slate-600">{fmtFecha(r.fecha)}</td>
                      <td className="px-2 py-1.5 font-medium">{r.nombre}</td>
                      <td className="px-2 py-1.5">{r.prueba}</td>
                      <td className="px-2 py-1.5 font-bold text-red-900">{r.marca}</td>
                      <td className="px-2 py-1.5 text-slate-600">{r.puesto ?? '—'}</td>
                      <td className="px-2 py-1.5 text-slate-600">{r.competencia}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Tarjetas — celular (sin barras de desplazamiento) */}
            <div className="space-y-2 md:hidden">
              {resultadosMes.slice(0, 8).map((r, i) => (
                <div key={i} className="rounded-lg border p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-semibold">{r.nombre}</p>
                    <span className="shrink-0 rounded bg-red-50 px-1.5 py-0.5 text-[11px] font-bold text-red-900">{r.marca}</span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">{fmtFecha(r.fecha)} · {r.prueba} · Puesto {r.puesto ?? '—'}</p>
                  <p className="truncate text-[11px] text-slate-400">{r.competencia}</p>
                </div>
              ))}
            </div>
            {resultadosMes.length > 8 && <p className="pt-2 text-center text-xs text-slate-500">… y {resultadosMes.length - 8} registros más (ver pestaña Análisis deportivo)</p>}
          </>
        )}
      </div>

      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <TituloSeccion>Accesos rápidos</TituloSeccion>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { t: 'Programación de alimentación', d: 'Quincena 1–15 / 16–31, con cumpleaños del periodo', tab: 'formatos', I: Utensils },
            { t: 'Lista para seguro (PAD)', d: 'Roster oficial con datos completos', tab: 'formatos', I: ShieldCheck },
            { t: 'Análisis deportivo', d: 'Rendimiento por deportista, prueba, meses y años', tab: 'analisis', I: BarChart3 },
            { t: 'Asistente IA', d: 'Redacción técnica de los informes AT', tab: 'asistente', I: Bot },
            { t: 'Registro de deportistas', d: 'Datos, filtros, ficha 360° y estado', tab: 'deportistas', I: Users },
            { t: 'Firmas de los formatos', d: 'Sube firmas y elige dónde se incrustan', tab: 'firmas', I: FileSignature },
          ].map(({ t, d, tab, I }) => (
            <button key={t} type="button" onClick={() => onIrA(tab)} className="group flex items-start gap-2 rounded-lg border border-dashed p-3 text-left transition-colors hover:border-red-800 hover:bg-red-50">
              <I className="mt-0.5 h-4 w-4 shrink-0 text-red-800" />
              <span className="min-w-0">
                <span className="flex items-center gap-1 text-sm font-semibold text-slate-800">{t}<ChevronRight className="h-3.5 w-3.5 text-red-800 opacity-0 transition-opacity group-hover:opacity-100" /></span>
                <span className="block text-xs text-slate-500">{d}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
