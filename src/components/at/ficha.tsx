'use client'

import { useEffect, useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Plus, Trash2, Copy, Utensils, Trophy, CalendarDays } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, BotonesExportar, BotonIA, TituloSeccion, BadgeCat, estadoAval } from './ui-at'
import { fmtFecha } from '@/lib/periodos'

type Dep = {
  id: number; apellidoPaterno: string; apellidoMaterno: string; nombres: string; dni: string; sexo: string
  fechaNacimiento: string; fechaIngreso: string | null; deporte: string; nivelTecnico: string; modalidad: string
  telefono: string | null; procedencia: string; categoria: string; pad: boolean; entrenador: string | null
  prueba: string | null; activo: boolean; retirado: boolean
  fechaVencimientoContinuidad: string | null; fechaCaducidadAval: string | null
  resultados: { id: number; fecha: string; competencia: string; prueba: string; marca: string; marcaValor: number; unidad: string; puesto: number | null; sede: string | null; nivel: string | null }[]
  alimentaciones: { id: number; periodo: string; incluido: boolean; observaciones: string | null }[]
}

type Estad = { mejores: { prueba: string; marca: string; fecha: string; competencia: string; mejora: number | null }[] }

const nuevoRes = { fecha: new Date().toISOString().slice(0, 10), competencia: 'CONTROL TÉCNICO INTERNO', prueba: '', marcaValor: '', unidad: 'seg', puesto: '', sede: 'PISTA ATLÉTICA CAR CUSCO', nivel: 'CONTROL INTERNO' }

export default function Ficha360({ depId, onClose }: { depId: number | null; onClose: () => void }) {
  const [dep, setDep] = useState<Dep | null>(null)
  const [mejores, setMejores] = useState<Record<string, Estad['mejores']>>({})
  const [formRes, setFormRes] = useState({ ...nuevoRes, prueba: '' })
  const [guardandoRes, setGuardandoRes] = useState(false)
  const [informe, setInforme] = useState('')
  const [cargandoIA, setCargandoIA] = useState(false)

  useEffect(() => {
    if (!depId) { setDep(null); setMejores({}); setInforme(''); setFormRes({ ...nuevoRes, prueba: '' }); return }
    api<Dep>(`/api/deportistas/${depId}`).then((d) => {
      setDep(d)
      setFormRes((f) => ({ ...f, prueba: d.prueba ?? '' }))
      const ref = new Date().toISOString().slice(0, 7)
      const anio = ref.slice(0, 4)
      const tipos: [string, string][] = [['MENSUAL', ref], ['BIMESTRAL', ref], ['TRIMESTRAL', ref], ['ANUAL', anio]]
      tipos.forEach(([t, r]) => {
        api<Estad>(`/api/estadisticas?tipo=${t}&ref=${r}&deportistaId=${depId}`).then((e) => setMejores((m) => ({ ...m, [t]: e.mejores }))).catch(() => null)
      })
    }).catch((e) => toast({ title: 'Error', description: e.message, variant: 'destructive' }))
  }, [depId])

  if (!depId) return null

  const eliminarRes = async (id: number) => {
    if (!confirm('¿Eliminar este registro de resultado?')) return
    try { await api(`/api/resultados?id=${id}`, { method: 'DELETE' }); toast({ title: 'Resultado eliminado' }); api<Dep>(`/api/deportistas/${depId}`).then(setDep) }
    catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const guardarRes = async () => {
    if (!formRes.prueba || !formRes.marcaValor) {
      toast({ title: 'Faltan datos', description: 'Indica la prueba y la marca numérica (ej. 11.25 o 7.12).', variant: 'destructive' })
      return
    }
    setGuardandoRes(true)
    try {
      await api('/api/resultados', { method: 'POST', body: JSON.stringify({ ...formRes, deportistaId: depId, marcaValor: Number(formRes.marcaValor) }) })
      toast({ title: 'Resultado registrado' })
      setFormRes({ ...nuevoRes, prueba: dep.prueba ?? '' })
      setDep(await api<Dep>(`/api/deportistas/${depId}`))
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    } finally { setGuardandoRes(false) }
  }

  const informeIA = async () => {
    setCargandoIA(true)
    try {
      const r = await api<{ texto: string }>('/api/ia', { method: 'POST', body: JSON.stringify({ tipo: 'ficha_informe', depId, periodo: new Date().toISOString().slice(0, 7) }) })
      setInforme(r.texto)
    } catch (e) {
      toast({ title: 'IA no disponible', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    } finally { setCargandoIA(false) }
  }

  const edad = (() => {
    if (!dep) return 0
    const h = new Date(), n = new Date(dep.fechaNacimiento)
    let e = h.getUTCFullYear() - n.getUTCFullYear()
    if (h.getUTCMonth() < n.getUTCMonth() || (h.getUTCMonth() === n.getUTCMonth() && h.getUTCDate() < n.getUTCDate())) e--
    return e
  })()

  const datos: [string, string][] = dep ? [
    ['DNI', dep.dni], ['Sexo', dep.sexo], ['Fecha de nacimiento', `${fmtFecha(dep.fechaNacimiento)} (${edad} años)`],
    ['Categoría', dep.categoria], ['Deporte', dep.deporte], ['Prueba', dep.prueba ?? '—'],
    ['Nivel técnico', dep.nivelTecnico], ['Modalidad', dep.modalidad], ['Entrenador', dep.entrenador ?? '—'],
    ['Ingreso al CAR', fmtFecha(dep.fechaIngreso)],
    ['Vence continuidad', fmtFecha(dep.fechaVencimientoContinuidad) || '—'],
    ['Aval médico', dep.fechaCaducidadAval ? `${estadoAval(dep.fechaCaducidadAval).texto} · vence ${fmtFecha(dep.fechaCaducidadAval)}` : 'SIN REGISTRO'],
    ['Teléfono', dep.telefono ?? '—'], ['Procedencia', dep.procedencia],
    ['Seguro PAD', dep.pad ? 'SI' : 'NO'], ['Estado', dep.retirado ? 'RETIRADO' : 'ACTIVO'],
  ] : []

  return (
    <Sheet open={!!depId} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-2xl" side="right">
        <SheetHeader className="border-b pb-3">
          <SheetTitle className="text-lg text-red-900">{dep ? `${dep.apellidoPaterno} ${dep.apellidoMaterno} ${dep.nombres}` : '…'}</SheetTitle>
          <SheetDescription className="flex flex-wrap items-center gap-2">
            {dep && <><BadgeCat>{dep.categoria}</BadgeCat><BadgeCat>{dep.sexo}</BadgeCat><BadgeCat>{dep.deporte}</BadgeCat></>}
          </SheetDescription>
        </SheetHeader>
        {dep && (
          <div className="space-y-5 p-4">
            <Tabs defaultValue="datos">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="datos">Datos</TabsTrigger>
                <TabsTrigger value="rendimiento">Rendimiento</TabsTrigger>
                <TabsTrigger value="informe">Informe IA</TabsTrigger>
              </TabsList>

              <TabsContent value="datos" className="space-y-4">
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border bg-white p-3 text-sm md:grid-cols-3">
                  {datos.map(([k, v]) => (
                    <div key={k}><p className="text-[11px] uppercase tracking-wide text-slate-400">{k}</p><p className="font-medium text-slate-800">{v}</p></div>
                  ))}
                </div>
                <div>
                  <TituloSeccion><span className="inline-flex items-center gap-1"><CalendarDays className="h-4 w-4" /> Programación de alimentación</span></TituloSeccion>
                  {dep.alimentaciones.length === 0 && <p className="text-sm text-slate-500">Sin registros.</p>}
                  <div className="flex flex-wrap gap-2">
                    {dep.alimentaciones.map((a) => (
                      <span key={a.id} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${a.incluido ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                        {a.periodo.replace('-Q', ' · Q')} : {a.incluido ? 'Sí' : 'No'}
                      </span>
                    ))}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="rendimiento" className="space-y-4">
                <div>
                  <TituloSeccion>Mejores marcas por periodo</TituloSeccion>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {(['MENSUAL', 'BIMESTRAL', 'TRIMESTRAL', 'ANUAL'] as const).map((t) => {
                      const m = (mejores[t] ?? [])[0]
                      const etiquetas: Record<string, string> = { MENSUAL: 'Mes', BIMESTRAL: 'Bimestre', TRIMESTRAL: 'Trimestre', ANUAL: 'Año' }
                      return (
                        <div key={t} className="rounded-lg border bg-white p-3">
                          <p className="text-[11px] font-semibold uppercase text-red-900">{etiquetas[t]}</p>
                          {m ? (
                            <p className="mt-0.5 text-sm">
                              <span className="text-lg font-bold text-slate-900">{m.marca}</span>
                              <span className="block text-xs text-slate-500">{m.prueba} · {m.competencia}</span>
                              {m.mejora != null && <span className={`text-xs font-semibold ${m.mejora > 0 ? 'text-green-700' : 'text-slate-500'}`}>{m.mejora > 0 ? `▲ +${m.mejora} % vs periodo anterior` : 'sin mejora vs periodo anterior'}</span>}
                            </p>
                          ) : <p className="text-sm text-slate-500">Sin registros</p>}
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <TituloSeccion>Historial de resultados</TituloSeccion>
                  <div className="mb-3 grid gap-2 rounded-lg border bg-slate-50 p-3 sm:grid-cols-4">
                    <label className="text-xs font-medium text-slate-600">Fecha
                      <Input type="date" className="h-8" value={formRes.fecha} onChange={(e) => setFormRes((f) => ({ ...f, fecha: e.target.value }))} /></label>
                    <label className="text-xs font-medium text-slate-600">Competencia
                      <Input className="h-8" value={formRes.competencia} onChange={(e) => setFormRes((f) => ({ ...f, competencia: e.target.value }))} /></label>
                    <label className="text-xs font-medium text-slate-600">Prueba
                      <Input className="h-8" value={formRes.prueba} onChange={(e) => setFormRes((f) => ({ ...f, prueba: e.target.value }))} /></label>
                    <label className="text-xs font-medium text-slate-600">Marca (número)
                      <Input className="h-8" value={formRes.marcaValor} onChange={(e) => setFormRes((f) => ({ ...f, marcaValor: e.target.value }))} /></label>
                    <label className="text-xs font-medium text-slate-600">Unidad
                      <select className="h-8 w-full rounded-md border bg-white px-2 text-sm" value={formRes.unidad} onChange={(e) => setFormRes((f) => ({ ...f, unidad: e.target.value }))}>
                        <option value="seg">seg (tiempo)</option><option value="m">metros (concursos)</option>
                      </select></label>
                    <label className="text-xs font-medium text-slate-600">Puesto
                      <Input type="number" className="h-8" value={formRes.puesto} onChange={(e) => setFormRes((f) => ({ ...f, puesto: e.target.value }))} /></label>
                    <label className="text-xs font-medium text-slate-600">Nivel
                      <select className="h-8 w-full rounded-md border bg-white px-2 text-sm" value={formRes.nivel} onChange={(e) => setFormRes((f) => ({ ...f, nivel: e.target.value }))}>
                        {['CONTROL INTERNO', 'DEPARTAMENTAL', 'REGIONAL', 'NACIONAL', 'INTERNACIONAL'].map((n) => <option key={n} value={n}>{n}</option>)}
                      </select></label>
                    <div className="flex items-end">
                      <Button size="sm" className="w-full bg-red-800 hover:bg-red-900" disabled={guardandoRes} onClick={guardarRes}>
                        <Plus className="h-4 w-4" /> Agregar
                      </Button>
                    </div>
                  </div>
                  <div className="max-h-72 overflow-y-auto rounded-lg border">
                    <Table>
                      <TableHeader><TableRow className="bg-red-50">
                        <TableHead className="text-red-900">Fecha</TableHead>
                        <TableHead className="text-red-900">Competencia</TableHead>
                        <TableHead className="text-red-900">Prueba</TableHead>
                        <TableHead className="text-red-900">Marca</TableHead>
                        <TableHead className="text-red-900">Nivel</TableHead>
                        <TableHead className="w-10" />
                      </TableRow></TableHeader>
                      <TableBody>
                        {dep.resultados.length === 0 && <TableRow><TableCell colSpan={6} className="py-6 text-center text-sm text-slate-500">Sin resultados registrados</TableCell></TableRow>}
                        {dep.resultados.map((r) => (
                          <TableRow key={r.id}>
                            <TableCell className="text-sm">{fmtFecha(r.fecha)}</TableCell>
                            <TableCell className="text-sm">{r.competencia}</TableCell>
                            <TableCell className="text-sm">{r.prueba}</TableCell>
                            <TableCell className="text-sm font-bold">{r.marca}</TableCell>
                            <TableCell className="text-xs">{r.nivel}</TableCell>
                            <TableCell><Button size="sm" variant="ghost" className="text-red-600" onClick={() => eliminarRes(r.id)}><Trash2 className="h-4 w-4" /></Button></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="informe" className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <BotonIA onClick={informeIA} cargando={cargandoIA}><Trophy className="h-4 w-4" /> Generar informe integral</BotonIA>
                  <BotonesExportar params={{ tipo: 'ficha', depId: String(depId), periodo: new Date().toISOString().slice(0, 7) }} nombreBase={`FICHA 360 - ${dep.apellidoPaterno} ${dep.nombres}`} />
                </div>
                {informe && (
                  <div className="rounded-lg border bg-amber-50 p-3 text-sm leading-relaxed whitespace-pre-wrap">
                    {informe}
                    <Button size="sm" variant="ghost" className="mt-2" onClick={() => { navigator.clipboard.writeText(informe); toast({ title: 'Informe copiado' }) }}>
                      <Copy className="h-4 w-4" /> Copiar
                    </Button>
                  </div>
                )}
                {!informe && <p className="text-sm text-slate-500"><Utensils className="mr-1 inline h-4 w-4" />El asistente IA analizará el perfil, resultados y mejores marcas para redactar un informe técnico integral del deportista.</p>}
              </TabsContent>
            </Tabs>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
