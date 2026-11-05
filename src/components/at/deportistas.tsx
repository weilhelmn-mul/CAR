'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Plus, Pencil, Trash2, UserSearch } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, useDeportistas, nombreCompletoUI, estadoAval, type Deportista, BadgeCat } from './ui-at'
import { CATEGORIAS, NIVELES, MODALIDADES, DEPORTES, SEXOS, fmtFecha } from '@/lib/periodos'
import Ficha360 from './ficha'

const vacio = {
  apellidoPaterno: '', apellidoMaterno: '', nombres: '', dni: '', sexo: 'MASCULINO',
  fechaNacimiento: '', fechaIngreso: '', deporte: 'ATLETISMO', prueba: '', nivelTecnico: 'DC',
  modalidad: 'INTERNO', categoria: 'U-18', telefono: '', procedencia: '', pad: false,
  entrenador: '', activo: true, retirado: false, fechaVencimientoContinuidad: '', fechaCaducidadAval: '',
}
type FormDep = typeof vacio

export default function Deportistas({ depIdFicha, setDepIdFicha }: { depIdFicha: number | null; setDepIdFicha: (v: number | null) => void }) {
  const { lista, cargando, recargar } = useDeportistas()
  const [q, setQ] = useState('')
  const [fCategoria, setFCategoria] = useState('todas')
  const [fSexo, setFSexo] = useState('todos')
  const [fModalidad, setFModalidad] = useState('todas')
  const [dialogo, setDialogo] = useState(false)
  const [editando, setEditando] = useState<Deportista | null>(null)
  const [form, setForm] = useState<FormDep>(vacio)
  const [guardando, setGuardando] = useState(false)

  const filtrados = useMemo(() => {
    const t = q.trim().toLowerCase()
    return lista.filter((d) => {
      if (t && !`${d.apellidoPaterno} ${d.apellidoMaterno} ${d.nombres} ${d.dni}`.toLowerCase().includes(t)) return false
      if (fCategoria !== 'todas' && d.categoria !== fCategoria) return false
      if (fSexo !== 'todos' && d.sexo !== fSexo) return false
      if (fModalidad !== 'todas' && d.modalidad !== fModalidad) return false
      return true
    })
  }, [lista, q, fCategoria, fSexo, fModalidad])

  const abrirNuevo = () => { setEditando(null); setForm(vacio); setDialogo(true) }
  const abrirEdicion = (d: Deportista) => {
    setEditando(d)
    setForm({
      apellidoPaterno: d.apellidoPaterno, apellidoMaterno: d.apellidoMaterno, nombres: d.nombres, dni: d.dni,
      sexo: d.sexo, fechaNacimiento: d.fechaNacimiento?.slice(0, 10) ?? '', fechaIngreso: d.fechaIngreso?.slice(0, 10) ?? '',
      deporte: d.deporte, prueba: d.prueba ?? '', nivelTecnico: d.nivelTecnico, modalidad: d.modalidad,
      categoria: d.categoria, telefono: d.telefono ?? '', procedencia: d.procedencia, pad: d.pad,
      entrenador: d.entrenador ?? '', activo: d.activo, retirado: d.retirado,
      fechaVencimientoContinuidad: d.fechaVencimientoContinuidad?.slice(0, 10) ?? '',
      fechaCaducidadAval: d.fechaCaducidadAval?.slice(0, 10) ?? '',
    })
    setDialogo(true)
  }

  const guardar = async () => {
    if (!form.apellidoPaterno || !form.nombres || !form.dni || !form.fechaNacimiento) {
      toast({ title: 'Datos incompletos', description: 'Apellidos, nombres, DNI y fecha de nacimiento son obligatorios.', variant: 'destructive' })
      return
    }
    setGuardando(true)
    try {
      if (editando) {
        await api(`/api/deportistas/${editando.id}`, { method: 'PUT', body: JSON.stringify(form) })
        toast({ title: 'Deportista actualizado' })
      } else {
        await api('/api/deportistas', { method: 'POST', body: JSON.stringify(form) })
        toast({ title: 'Deportista registrado' })
      }
      setDialogo(false)
      recargar()
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    } finally { setGuardando(false) }
  }

  const eliminar = async (d: Deportista) => {
    if (!confirm(`¿Eliminar a ${nombreCompletoUI(d)}? Se borrarán también sus resultados.`)) return
    try {
      await api(`/api/deportistas/${d.id}`, { method: 'DELETE' })
      toast({ title: 'Deportista eliminado' })
      recargar()
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    }
  }

  const set = (k: keyof FormDep, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-52">
          <UserSearch className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input placeholder="Buscar por apellido o DNI…" className="pl-8" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <Select value={fCategoria} onValueChange={setFCategoria}>
          <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
          <SelectContent>{['todas', ...CATEGORIAS].map((c) => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={fSexo} onValueChange={setFSexo}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>{['todos', ...SEXOS].map((c) => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={fModalidad} onValueChange={setFModalidad}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>{['todas', ...MODALIDADES].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
        </Select>
        <Button className="bg-red-800 hover:bg-red-900" onClick={abrirNuevo}><Plus className="h-4 w-4" /> Nuevo</Button>
      </div>

      <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-red-50">
              <TableHead className="w-8 text-red-900">N°</TableHead>
              <TableHead className="text-red-900">Apellidos y nombres</TableHead>
              <TableHead className="text-red-900">DNI</TableHead>
              <TableHead className="text-red-900">Categoría</TableHead>
              <TableHead className="text-red-900">Sexo</TableHead>
              <TableHead className="text-red-900">Deporte / prueba</TableHead>
              <TableHead className="text-red-900">Modalidad</TableHead>
              <TableHead className="text-red-900">Ingreso</TableHead>
              <TableHead className="text-red-900">Vence continuidad</TableHead>
              <TableHead className="text-red-900">Aval médico</TableHead>
              <TableHead className="text-red-900">PAD</TableHead>
              <TableHead className="text-red-900">Entrenador</TableHead>
              <TableHead className="text-right text-red-900">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {cargando && <TableRow><TableCell colSpan={12} className="py-8 text-center text-slate-500">Cargando…</TableCell></TableRow>}
            {!cargando && filtrados.length === 0 && <TableRow><TableCell colSpan={12} className="py-8 text-center text-slate-500">Sin resultados</TableCell></TableRow>}
            {filtrados.map((d, i) => (
              <TableRow key={d.id} className={d.retirado ? 'opacity-50' : ''}>
                <TableCell className="text-xs text-slate-500">{i + 1}</TableCell>
                <TableCell className="font-medium">{nombreCompletoUI(d)}</TableCell>
                <TableCell className="text-sm">{d.dni}</TableCell>
                <TableCell><BadgeCat>{d.categoria}</BadgeCat></TableCell>
                <TableCell className="text-sm">{d.sexo === 'FEMENINO' ? 'F' : 'M'}</TableCell>
                <TableCell className="text-sm">{d.deporte}<span className="block text-xs text-slate-500">{d.prueba ?? '—'}</span></TableCell>
                <TableCell className="text-sm">{d.modalidad}</TableCell>
                <TableCell className="text-sm">{fmtFecha(d.fechaIngreso)}</TableCell>
                <TableCell className={`text-sm ${d.fechaVencimientoContinuidad ? 'text-slate-700' : 'text-slate-400'}`}>{fmtFecha(d.fechaVencimientoContinuidad) || '—'}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-bold ${estadoAval(d.fechaCaducidadAval).clase}`}>
                    {estadoAval(d.fechaCaducidadAval).texto}
                  </span>
                  {d.fechaCaducidadAval && <span className="block text-xs text-slate-500">{fmtFecha(d.fechaCaducidadAval)}</span>}
                </TableCell>
                <TableCell className={`text-sm font-semibold ${d.pad ? 'text-green-700' : 'text-slate-400'}`}>{d.pad ? 'SI' : 'NO'}</TableCell>
                <TableCell className="text-sm text-slate-600">{d.entrenador ?? '—'}</TableCell>
                <TableCell className="text-right">
                  <Button size="sm" variant="ghost" className="text-red-900" onClick={() => setDepIdFicha(d.id)}>Ficha 360°</Button>
                  <Button size="sm" variant="ghost" onClick={() => abrirEdicion(d)}><Pencil className="h-4 w-4" /></Button>
                  <Button size="sm" variant="ghost" className="text-red-600" onClick={() => eliminar(d)}><Trash2 className="h-4 w-4" /></Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogo} onOpenChange={setDialogo}>
        <DialogContent className="max-h-[92vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editando ? `Editar: ${nombreCompletoUI(editando)}` : 'Nuevo deportista'}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-3">
            {([['apellidoPaterno', 'Apellido paterno', 'text'], ['apellidoMaterno', 'Apellido materno', 'text'], ['nombres', 'Nombres', 'text'], ['dni', 'DNI', 'text'], ['fechaNacimiento', 'Fecha de nacimiento', 'date'], ['fechaIngreso', 'Fecha de ingreso', 'date'], ['fechaVencimientoContinuidad', 'Vencimiento de continuidad', 'date'], ['fechaCaducidadAval', 'Caducidad del aval médico', 'date'], ['prueba', 'Prueba (ej. 800 m)', 'text'], ['telefono', 'Teléfono', 'text'], ['entrenador', 'Entrenador', 'text']] as const).map(([k, lbl, tp]) => (
              <label key={k} className="grid gap-1 text-xs font-medium text-slate-600">
                {lbl}
                <Input type={tp} value={String(form[k] ?? '')} onChange={(e) => set(k, e.target.value)} />
              </label>
            ))}
            <label className="grid gap-1 text-xs font-medium text-slate-600">Sexo
              <Select value={form.sexo} onValueChange={(v) => set('sexo', v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{SEXOS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Deporte
              <Select value={form.deporte} onValueChange={(v) => set('deporte', v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{DEPORTES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Categoría
              <Select value={form.categoria} onValueChange={(v) => set('categoria', v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{CATEGORIAS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Nivel técnico
              <Select value={form.nivelTecnico} onValueChange={(v) => set('nivelTecnico', v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{NIVELES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Modalidad
              <Select value={form.modalidad} onValueChange={(v) => set('modalidad', v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{MODALIDADES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600 sm:col-span-2">
              Distrito / provincia de procedencia
              <Input value={form.procedencia} onChange={(e) => set('procedencia', e.target.value)} />
            </label>
            <label className="flex items-end gap-2 pb-1 text-xs font-medium text-slate-600">
              <input type="checkbox" checked={form.pad} onChange={(e) => set('pad', e.target.checked)} className="h-4 w-4 accent-red-800" />
              Seguro PAD (SI)
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogo(false)}>Cancelar</Button>
            <Button className="bg-red-800 hover:bg-red-900" disabled={guardando} onClick={guardar}>{guardando ? 'Guardando…' : 'Guardar'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Ficha360 depId={depIdFicha} onClose={() => setDepIdFicha(null)} />
    </div>
  )
}
