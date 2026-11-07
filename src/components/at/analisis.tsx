'use client'

// ANÁLISIS DEPORTIVO — panel de población por periodo + análisis de rendimiento técnico
import { useEffect, useState } from 'react'
import { Loader2, Table2 } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Kpi, TituloSeccion, api, SelectorMes, BotonesExportar, BotonIA, PALETA, PALETA_SEXO } from './ui-at'
import { GraficoBarras, GraficoDonut } from './charts'
import type { TipoPeriodo } from '@/lib/periodos'
import Rendimiento from './rendimiento'

type Estad = {
  etiqueta: string; activos: number; pad: number; ingresos: number; resultados: number
  porCategoria: { clave: string; total: number }[]
  porSexo: { clave: string; total: number }[]
  porDeporte: { clave: string; total: number }[]
  porModalidad: { clave: string; total: number }[]
  resultadosPorMes: { mes: string; total: number }[]
  mejores: { deportistaId: number; nombre: string; categoria: string; sexo: string; prueba: string; marca: string; fecha: string; competencia: string; mejora: number | null }[]
  detalle: { fecha: string; nombre: string; categoria: string; prueba: string; marca: string; puesto: number | null; competencia: string; nivel: string | null }[]
}

export default function Analisis() {
  const [tipo, setTipo] = useState<TipoPeriodo>('MENSUAL')
  const [mes, setMes] = useState(new Date().toISOString().slice(0, 7))
  const ref = tipo === 'ANUAL' ? mes.slice(0, 4) : mes
  const [est, setEst] = useState<Estad | null>(null)
  const [cargando, setCargando] = useState(true)
  const [informe, setInforme] = useState('')
  const [iaCargando, setIaCargando] = useState(false)

  useEffect(() => {
    setCargando(true)
    api<Estad>(`/api/estadisticas?tipo=${tipo}&ref=${ref}`).then(setEst).catch(() => null).finally(() => setCargando(false))
    setInforme('')
  }, [tipo, ref])

  const generarInforme = async () => {
    setIaCargando(true)
    try {
      const r = await api<{ texto: string }>('/api/ia', { method: 'POST', body: JSON.stringify({ tipo: 'informe_analisis', tipoPeriodo: tipo, ref }) })
      setInforme(r.texto)
    } catch (e) {
      setInforme(`No se pudo generar el informe IA: ${e instanceof Error ? e.message : 'error'}`)
    } finally { setIaCargando(false) }
  }

  const params = { tipo: 'analisis', tipoPeriodo: tipo, periodo: ref }
  // etiquetas cortas de mes para el eje X cuando hay varios meses ("NOVIEMBRE 2026" → "NOV")
  const cortoMes = (v: string) => v.split(' ')[0].slice(0, 3)

  return (
    <Tabs defaultValue="poblacion">
      <TabsList className="mb-4 flex h-auto flex-wrap gap-1 bg-white p-1 shadow-sm">
        <TabsTrigger value="poblacion" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">Población y periodo</TabsTrigger>
        <TabsTrigger value="rendimiento" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">Rendimiento por deportista</TabsTrigger>
      </TabsList>

      <TabsContent value="rendimiento"><Rendimiento /></TabsContent>

      <TabsContent value="poblacion">
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-md border">
          {(['MENSUAL', 'BIMESTRAL', 'TRIMESTRAL', 'ANUAL'] as const).map((t) => (
            <button key={t} className={`px-3 py-2 text-xs font-bold ${tipo === t ? 'bg-red-800 text-white' : 'bg-white text-slate-600'}`} onClick={() => setTipo(t)}>
              {t === 'MENSUAL' ? 'MES' : t === 'BIMESTRAL' ? 'BIMESTRE' : t === 'TRIMESTRAL' ? 'TRIMESTRE' : 'AÑO'}
            </button>
          ))}
        </div>
        {tipo === 'ANUAL' ? <SelectorMes valor={mes} onChange={setMes} incluirAnio /> : <SelectorMes valor={mes} onChange={setMes} />}
        {est && <span className="text-sm font-medium text-slate-600">{est.etiqueta}</span>}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <BotonIA onClick={generarInforme} cargando={iaCargando}><Table2 className="h-4 w-4" /> Informe técnico IA</BotonIA>
          <BotonesExportar params={params} nombreBase={`ANALISIS DEPORTIVO - ${est?.etiqueta ?? ref}`} />
        </div>
      </div>

      {cargando ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-red-800" /></div>
      ) : !est ? (
        <p className="py-16 text-center text-sm text-slate-500">No se pudo calcular el análisis.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi titulo="Deportistas activos" valor={est.activos} />
            <Kpi titulo="Con seguro PAD" valor={est.pad} detalle={`${est.activos ? Math.round((est.pad / est.activos) * 100) : 0} %`} />
            <Kpi titulo="Ingresos del periodo" valor={est.ingresos} />
            <Kpi titulo="Resultados registrados" valor={est.resultados} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border bg-white p-4 shadow-sm">
              <TituloSeccion>Deportistas por categoría</TituloSeccion>
              <GraficoBarras data={est.porCategoria} colores={PALETA} alto="h-52 sm:h-56" />
            </div>
            {/* Dos donas independientes (sexo y deporte): cada dimensión conserva su propia escala 100 % */}
            <div className="rounded-xl border bg-white p-4 shadow-sm">
              <TituloSeccion>Distribución por sexo y deporte</TituloSeccion>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <GraficoDonut data={est.porSexo.map((x) => ({ clave: x.clave, total: x.total, color: PALETA_SEXO[x.clave] ?? PALETA[0] }))} alto="h-36 sm:h-44" etiquetaCentro="deportistas" />
                  <p className="pt-1 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">Sexo</p>
                </div>
                <div>
                  <GraficoDonut data={est.porDeporte.map((x, i) => ({ clave: x.clave, total: x.total, color: PALETA[i % PALETA.length] }))} alto="h-36 sm:h-44" etiquetaCentro="deportistas" />
                  <p className="pt-1 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">Deporte</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <TituloSeccion>Resultados registrados por mes</TituloSeccion>
            <GraficoBarras data={est.resultadosPorMes.map((r) => ({ clave: r.mes, total: r.total }))} color="#b91c1c" alto="h-48 sm:h-52" formatoX={cortoMes} ocultarCeros />
          </div>

          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <TituloSeccion>Cuadro estadístico: mejores marcas del periodo</TituloSeccion>
            <div className="max-h-96 overflow-auto">
              <table className="w-full min-w-[760px] text-xs">
                <thead><tr className="bg-red-50">
                  {['N°', 'APELLIDOS Y NOMBRES', 'CATEG.', 'SEXO', 'PRUEBA', 'MEJOR MARCA', 'FECHA', 'COMPETENCIA', 'MEJORA'].map((h) => <th key={h} className="sticky top-0 border bg-red-50 p-1.5 text-left text-red-900">{h}</th>)}
                </tr></thead>
                <tbody>
                  {est.mejores.length === 0 && <tr><td colSpan={9} className="py-8 text-center text-slate-500">Sin registros en el periodo seleccionado</td></tr>}
                  {est.mejores.map((m, i) => (
                    <tr key={`${m.deportistaId}-${m.prueba}`} className={i % 2 ? 'bg-slate-50' : ''}>
                      <td className="border p-1.5 text-center">{i + 1}</td>
                      <td className="border p-1.5 font-medium">{m.nombre}</td>
                      <td className="border p-1.5 text-center">{m.categoria}</td>
                      <td className="border p-1.5 text-center">{m.sexo === 'FEMENINO' ? 'F' : 'M'}</td>
                      <td className="border p-1.5">{m.prueba}</td>
                      <td className="border p-1.5 text-center font-bold text-red-900">{m.marca}</td>
                      <td className="border p-1.5 text-center">{m.fecha.slice(0, 10)}</td>
                      <td className="border p-1.5">{m.competencia}</td>
                      <td className={`border p-1.5 text-center font-semibold ${m.mejora != null && m.mejora > 0 ? 'text-green-700' : 'text-slate-400'}`}>
                        {m.mejora != null ? `${m.mejora > 0 ? '+' : ''}${m.mejora} %` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {informe && (
            <div className="rounded-xl border bg-amber-50 p-4 text-sm leading-relaxed whitespace-pre-wrap">
              <TituloSeccion>Informe técnico IA — {est.etiqueta}</TituloSeccion>
              {informe}
            </div>
          )}
        </>
      )}
    </div>
      </TabsContent>
    </Tabs>
  )
}
