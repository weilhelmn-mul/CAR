'use client'

// FORMATO SEGURO — lista de deportistas del CAR Cusco
import { useEffect, useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toast } from '@/hooks/use-toast'
import { api, estadoAval, BotonesExportar, SelectorMes, BadgeCat } from './ui-at'
import { fmtFecha } from '@/lib/periodos'
import type { Deportista } from './ui-at'

export default function FormatoSeguro() {
  const [mes, setMes] = useState(new Date().toISOString().slice(0, 7))
  const [lista, setLista] = useState<Deportista[]>([])
  const [cargando, setCargando] = useState(true)

  const cargar = async () => {
    setCargando(true)
    try { setLista(await api<Deportista[]>('/api/deportistas')) } finally { setCargando(false) }
  }
  useEffect(() => { cargar() }, [])

  const togglePad = async (d: Deportista) => {
    try {
      await api(`/api/deportistas/${d.id}`, { method: 'PUT', body: JSON.stringify({ pad: !d.pad }) })
      setLista((l) => l.map((x) => x.id === d.id ? { ...x, pad: !x.pad } : x))
    } catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const conPad = lista.filter((d) => d.pad).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <SelectorMes valor={mes} onChange={setMes} />
        <span className="text-sm font-medium text-slate-600">{lista.length} deportistas · {conPad} con PAD</span>
        <div className="ml-auto"><BotonesExportar params={{ tipo: 'seguro', periodo: mes }} nombreBase={`SEGURO - ${mes}`} /></div>
      </div>

      <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
        <div className="border-b bg-red-50 px-4 py-2">
          <p className="text-center text-sm font-bold uppercase text-red-900">LISTA DE DEPORTISTAS DEL CAR CUSCO - SEGURO - {mes}</p>
        </div>
        <Table>
          <TableHeader><TableRow className="bg-white">
            {['N°', 'APELLIDOS', 'NOMBRES', 'DNI', 'SEXO', 'F. INGRESO', 'DEPORTE', 'F. NAC.', 'NIVEL TÉC.', 'MODALIDAD', 'TELÉFONO', 'PROCEDENCIA', 'CATEG.', 'VENC. CONTINUIDAD', 'AVAL MÉDICO', 'PAD'].map((h) => <TableHead key={h} className="text-red-900">{h}</TableHead>)}
          </TableRow></TableHeader>
          <TableBody>
            {cargando && <TableRow><TableCell colSpan={16} className="py-8 text-center">Cargando…</TableCell></TableRow>}
            {lista.map((d, i) => (
              <TableRow key={d.id}>
                <TableCell>{i + 1}</TableCell>
                <TableCell className="font-medium">{d.apellidoPaterno} {d.apellidoMaterno}</TableCell>
                <TableCell>{d.nombres}</TableCell>
                <TableCell>{d.dni}</TableCell>
                <TableCell>{d.sexo === 'FEMENINO' ? 'FEMENINO' : 'MASCULINO'}</TableCell>
                <TableCell>{fmtFecha(d.fechaIngreso)}</TableCell>
                <TableCell>{d.deporte}</TableCell>
                <TableCell>{fmtFecha(d.fechaNacimiento)}</TableCell>
                <TableCell>{d.nivelTecnico}</TableCell>
                <TableCell>{d.modalidad}</TableCell>
                <TableCell>{d.telefono ?? '—'}</TableCell>
                <TableCell className="max-w-44 truncate text-xs">{d.procedencia}</TableCell>
                <TableCell><BadgeCat>{d.categoria}</BadgeCat></TableCell>
                <TableCell className="text-sm">{fmtFecha(d.fechaVencimientoContinuidad) || '—'}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-bold ${estadoAval(d.fechaCaducidadAval).clase}`}>
                    {estadoAval(d.fechaCaducidadAval).texto}
                  </span>
                  {d.fechaCaducidadAval && <span className="block text-xs text-slate-500">{fmtFecha(d.fechaCaducidadAval)}</span>}
                </TableCell>
                <TableCell>
                  <button onClick={() => togglePad(d)} className={`rounded px-2 py-0.5 text-xs font-bold ${d.pad ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-500'}`}>
                    {d.pad ? 'SI' : 'NO'}
                  </button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-slate-500">La columna PAD se puede marcar/desmarcar haciendo clic (se guarda al instante). Las columnas «VENC. CONTINUIDAD» y «AVAL MÉDICO» se registran desde la pestaña Deportistas → Editar; el aval muestra VIGENTE, POR VENCER (≤30 días) o EXPIRADO según su fecha de caducidad.</p>
    </div>
  )
}
