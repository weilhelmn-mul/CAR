'use client'

// FORMATO ALIMENTACIÓN — programación del servicio por quincena
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Save, Cake } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, BotonesExportar, SelectorMes, TituloSeccion } from './ui-at'
import { infoQuincena, cumpleEnQuincena, fmtFechaCorta } from '@/lib/periodos'

type Fila = { deportista: { id: number; apellidoPaterno: string; apellidoMaterno: string; nombres: string; fechaNacimiento: string }; incluido: boolean; observaciones: string | null }

export default function FormatoAlimentacion() {
  const hoy = new Date()
  const mesHoy = hoy.toISOString().slice(0, 7)
  const qnHoy = hoy.getUTCDate() <= 15 ? 'Q1' : 'Q2'
  const [mes, setMes] = useState(mesHoy)
  const [qn, setQn] = useState(qnHoy)
  const periodo = `${mes}-${qn}`
  const [filas, setFilas] = useState<Fila[]>([])
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)

  const cargar = async () => {
    setCargando(true)
    try { setFilas((await api<{ filas: Fila[] }>(`/api/alimentacion?periodo=${periodo}`)).filas) }
    catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setCargando(false) }
  }
  useEffect(() => { cargar() }, [periodo])

  const guardar = async () => {
    setGuardando(true)
    try {
      for (const f of filas) {
        await api('/api/alimentacion', { method: 'POST', body: JSON.stringify({ deportistaId: f.deportista.id, periodo, incluido: f.incluido, observaciones: f.observaciones }) })
      }
      toast({ title: 'Programación guardada' })
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
    finally { setGuardando(false) }
  }

  const q = infoQuincena(periodo)
  const incluidos = filas.filter((f) => f.incluido).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <SelectorMes valor={mes} onChange={setMes} />
        <div className="flex overflow-hidden rounded-md border">
          <button className={`px-3 py-2 text-sm font-semibold ${qn === 'Q1' ? 'bg-red-800 text-white' : 'bg-white'}`} onClick={() => setQn('Q1')}>1 AL 15</button>
          <button className={`px-3 py-2 text-sm font-semibold ${qn === 'Q2' ? 'bg-red-800 text-white' : 'bg-white'}`} onClick={() => setQn('Q2')}>16 AL FIN DE MES</button>
        </div>
        <span className="text-sm font-medium text-slate-600">{q.etiqueta}</span>
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" className="bg-red-800 hover:bg-red-900" disabled={guardando} onClick={guardar}><Save className="h-4 w-4" /> {guardando ? 'Guardando…' : 'Guardar'}</Button>
          <BotonesExportar params={{ tipo: 'alimentacion', periodo }} nombreBase={`ALIMENTACIÓN ${q.etiquetaCorta} ${q.anio}`} />
        </div>
      </div>

      <div className="rounded-xl border bg-white shadow-sm">
        <div className="border-b bg-red-50 px-4 py-2">
          <p className="text-center text-sm font-bold uppercase text-red-900">Lista de deportistas CAR Cusco — programación del servicio de alimentación {q.etiqueta}</p>
        </div>
        <div className="max-h-[60vh] overflow-y-auto">
          <Table>
            <TableHeader><TableRow className="bg-white">
              {['N°', 'CAR', 'APELLIDO PATERNO', 'APELLIDO MATERNO', 'NOMBRES', 'CUMPLEAÑOS', q.etiquetaCorta, 'OBSERVACIONES'].map((h) => (
                <TableHead key={h} className="text-red-900">{h}</TableHead>
              ))}
            </TableRow></TableHeader>
            <TableBody>
              {cargando && <TableRow><TableCell colSpan={8} className="py-8 text-center">Cargando…</TableCell></TableRow>}
              {filas.map((f, i) => {
                const cumple = cumpleEnQuincena(new Date(f.deportista.fechaNacimiento), q)
                return (
                  <TableRow key={f.deportista.id} className={cumple ? 'bg-amber-50' : ''}>
                    <TableCell>{i + 1}</TableCell>
                    <TableCell>CUSCO</TableCell>
                    <TableCell className="font-medium">{f.deportista.apellidoPaterno}</TableCell>
                    <TableCell>{f.deportista.apellidoMaterno}</TableCell>
                    <TableCell>{f.deportista.nombres}</TableCell>
                    <TableCell>{cumple ? <span className="inline-flex items-center gap-1 font-semibold text-amber-700"><Cake className="h-4 w-4" />{fmtFechaCorta(f.deportista.fechaNacimiento)}</span> : ''}</TableCell>
                    <TableCell>
                      <Checkbox checked={f.incluido} onCheckedChange={(v) => setFilas((fs) => fs.map((x) => x.deportista.id === f.deportista.id ? { ...x, incluido: !!v } : x))} />
                      <span className="ml-2 text-sm font-semibold">{f.incluido ? 'Sí' : 'No'}</span>
                    </TableCell>
                    <TableCell>
                      <input className="w-full rounded border border-transparent bg-transparent px-1 py-0.5 text-sm hover:border-slate-300 focus:border-red-700 focus:outline-none" value={f.observaciones ?? ''} onChange={(e) => setFilas((fs) => fs.map((x) => x.deportista.id === f.deportista.id ? { ...x, observaciones: e.target.value } : x))} />
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
        <div className="border-t px-4 py-2 text-xs text-slate-500">
          <TituloSeccion>NOTA:</TituloSeccion>
          <p>{incluidos} de {filas.length} deportistas programados. Las filas resaltadas indican cumpleaños dentro de la quincena.</p>
        </div>
      </div>
    </div>
  )
}
