'use client'

import { useEffect, useState } from 'react'
import { Users, ShieldCheck, CalendarDays, Trophy, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Kpi, TituloSeccion, api, PALETA, useDeportistas, BadgeCat } from './ui-at'
import { MESES_ES, fmtFecha } from '@/lib/periodos'

type Estad = {
  activos: number; pad: number; ingresos: number; resultados: number
  porCategoria: { clave: string; total: number }[]
  porSexo: { clave: string; total: number }[]
  porDeporte: { clave: string; total: number }[]
  porModalidad: { clave: string; total: number }[]
}

export default function Inicio({ onAbrirFicha }: { onAbrirFicha: (id: number) => void }) {
  const { lista } = useDeportistas()
  const [est, setEst] = useState<Estad | null>(null)
  const mesHoy = new Date().toISOString().slice(0, 7)

  useEffect(() => {
    api<Estad>(`/api/estadisticas?tipo=MENSUAL&ref=${mesHoy}`).then(setEst).catch(() => null)
  }, [mesHoy])

  const cumpleanosMes = lista
    .filter((d) => new Date(d.fechaNacimiento).getUTCMonth() === new Date().getUTCMonth())
    .sort((a, b) => new Date(a.fechaNacimiento).getUTCDate() - new Date(b.fechaNacimiento).getUTCDate())

  const totalActivos = est?.activos ?? 0
  const pctPad = totalActivos ? Math.round(((est?.pad ?? 0) / totalActivos) * 100) : 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi titulo="Deportistas activos" valor={est?.activos ?? lista.filter((d) => d.activo).length} detalle={`${lista.length} registrados en total`} icono={<Users className="h-5 w-5" />} />
        <Kpi titulo="Con seguro PAD" valor={est?.pad ?? 0} detalle={`${pctPad} % del grupo activo`} icono={<ShieldCheck className="h-5 w-5" />} />
        <Kpi titulo="Ingresos del mes" valor={est?.ingresos ?? 0} detalle="altas registradas" icono={<CalendarDays className="h-5 w-5" />} />
        <Kpi titulo="Resultados del mes" valor={est?.resultados ?? 0} detalle="marcas registradas" icono={<Trophy className="h-5 w-5" />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm lg:col-span-2">
          <TituloSeccion>Composición por categoría</TituloSeccion>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={est?.porCategoria ?? []}>
                <XAxis dataKey="clave" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="total" radius={[6, 6, 0, 0]}>
                  {(est?.porCategoria ?? []).map((_, i) => <Cell key={i} fill={PALETA[i % PALETA.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(est?.porSexo ?? []).map((s) => (
              <BadgeCat key={s.clave}>{s.clave}: {s.total}</BadgeCat>
            ))}
            {(est?.porModalidad ?? []).map((s) => (
              <span key={s.clave} className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">{s.clave}: {s.total}</span>
            ))}
          </div>
        </div>

        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <TituloSeccion>Cumpleaños de {MESES_ES[new Date().getUTCMonth()]}</TituloSeccion>
          {cumpleanosMes.length === 0 && <p className="py-6 text-center text-sm text-slate-500">Sin cumpleaños este mes</p>}
          <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
            {cumpleanosMes.map((d) => (
              <button key={d.id} onClick={() => onAbrirFicha(d.id)} className="flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm hover:bg-red-50">
                <span className="font-medium">{d.apellidoPaterno} {d.nombres}</span>
                <span className="text-xs text-slate-500">{fmtFecha(d.fechaNacimiento).slice(0, 5)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <TituloSeccion>Accesos rápidos</TituloSeccion>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { t: 'Programación de alimentación', d: 'Quincena 1–15 / 16–31, con cumpleaños del periodo' },
            { t: 'Lista para seguro (PAD)', d: 'Roster oficial con datos completos' },
            { t: 'Análisis deportivo', d: 'Mejores marcas por mes, bimestre, trimestre y año' },
            { t: 'Asistente IA', d: 'Redacción técnica de los informes AT' },
          ].map((x) => (
            <div key={x.t} className="flex items-start gap-2 rounded-lg border border-dashed p-3">
              <Activity className="mt-0.5 h-4 w-4 shrink-0 text-red-800" />
              <div>
                <p className="text-sm font-semibold">{x.t}</p>
                <p className="text-xs text-slate-500">{x.d}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
