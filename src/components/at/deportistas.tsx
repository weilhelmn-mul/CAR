'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Checkbox } from '@/components/ui/checkbox'
import { Plus, Pencil, Trash2, UserSearch, Filter, Columns3, X, ArrowUp, ArrowDown, ArrowUpDown, FileText, ClipboardList, Power } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api, useDeportistas, nombreCompletoUI, estadoAval, calcularEdad, type Deportista, BadgeCat } from './ui-at'
import { CATEGORIAS, NIVELES, MODALIDADES, DEPORTES, SEXOS, fmtFecha } from '@/lib/periodos'
import Ficha360 from './ficha'

const vacio = {
  apellidoPaterno: '', apellidoMaterno: '', nombres: '', dni: '', sexo: 'MASCULINO',
  fechaNacimiento: '', fechaIngreso: '', deporte: 'ATLETISMO', prueba: '', nivelTecnico: 'DC',
  modalidad: 'INTERNO', categoria: 'U-18', telefono: '', procedencia: '', pad: false,
  entrenador: '', activo: true, retirado: false, fechaVencimientoContinuidad: '', fechaCaducidadAval: '',
}
type FormDep = typeof vacio

// Estado en 3 niveles: ACTIVO (entrena actualmente) · INACTIVO (temporalmente fuera) · RETIRADO (dejó el CAR)
const estadoInfo = (d: Pick<Deportista, 'activo' | 'retirado'>) =>
  d.retirado ? { texto: 'RETIRADO', clase: 'bg-slate-100 text-slate-500' }
  : d.activo ? { texto: 'ACTIVO', clase: 'bg-green-100 text-green-800' }
  : { texto: 'INACTIVO', clase: 'bg-amber-100 text-amber-800' }

// ====== VARIABLES (COLUMNAS) QUE EL USUARIO PUEDE MOSTRAR U OCULTAR ======
type ColKey =
  | 'dni' | 'edad' | 'fechaNacimiento' | 'categoria' | 'sexo' | 'deporte' | 'nivelTecnico'
  | 'modalidad' | 'ingreso' | 'continuidad' | 'aval' | 'pad' | 'procedencia' | 'telefono' | 'entrenador' | 'estado'

const COLUMNAS: { key: ColKey; etiqueta: string; porDefecto: boolean }[] = [
  { key: 'dni', etiqueta: 'DNI', porDefecto: true },
  { key: 'edad', etiqueta: 'Edad', porDefecto: true },
  { key: 'fechaNacimiento', etiqueta: 'F. nacimiento', porDefecto: false },
  { key: 'categoria', etiqueta: 'Categoría', porDefecto: true },
  { key: 'sexo', etiqueta: 'Sexo', porDefecto: true },
  { key: 'deporte', etiqueta: 'Deporte / prueba', porDefecto: true },
  { key: 'nivelTecnico', etiqueta: 'Nivel técnico', porDefecto: false },
  { key: 'modalidad', etiqueta: 'Modalidad', porDefecto: true },
  { key: 'ingreso', etiqueta: 'Ingreso', porDefecto: true },
  { key: 'continuidad', etiqueta: 'Vence continuidad', porDefecto: true },
  { key: 'aval', etiqueta: 'Aval médico', porDefecto: true },
  { key: 'pad', etiqueta: 'PAD', porDefecto: true },
  { key: 'procedencia', etiqueta: 'Procedencia', porDefecto: false },
  { key: 'telefono', etiqueta: 'Teléfono', porDefecto: false },
  { key: 'entrenador', etiqueta: 'Entrenador', porDefecto: true },
  { key: 'estado', etiqueta: 'Estado', porDefecto: true },
]

const LS_COLUMNAS = 'at-deportistas-columnas-v2'
const ETIQUETA_EXTRA: Record<string, string> = { nombres: 'Apellidos y nombres' }
const etiquetaDe = (k: string) => COLUMNAS.find((c) => c.key === k)?.etiqueta ?? ETIQUETA_EXTRA[k] ?? k

export default function Deportistas({ depIdFicha, setDepIdFicha }: { depIdFicha: number | null; setDepIdFicha: (v: number | null) => void }) {
  const { lista, cargando, recargar } = useDeportistas()
  const [q, setQ] = useState('')
  const [fCategoria, setFCategoria] = useState('todas')
  const [fSexo, setFSexo] = useState('todos')
  const [fModalidad, setFModalidad] = useState('todas')
  // Filtros avanzados
  const [verFiltros, setVerFiltros] = useState(false)
  const [fDeporte, setFDeporte] = useState('todos')
  const [fNivel, setFNivel] = useState('todos')
  const [fPad, setFPad] = useState('todos') // todos | si | no
  const [fAval, setFAval] = useState('todos') // todos | VIGENTE | POR VENCER | EXPIRADO | SIN REGISTRO
  const [fEstado, setFEstado] = useState('todos') // todos | activos | retirados
  const [edadMin, setEdadMin] = useState('')
  const [edadMax, setEdadMax] = useState('')
  // Ordenamiento
  const [orden, setOrden] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(null)
  // Columnas visibles (elección del usuario, persistente)
  const [visibles, setVisibles] = useState<Set<ColKey>>(new Set(COLUMNAS.filter((c) => c.porDefecto).map((c) => c.key)))
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_COLUMNAS)
      if (raw) {
        const arr = JSON.parse(raw) as ColKey[]
        setVisibles(new Set(COLUMNAS.filter((c) => arr.includes(c.key)).map((c) => c.key)))
      }
    } catch { /* usa valores por defecto */ }
  }, [])
  const toggleColumna = (k: ColKey, activo: boolean) => {
    setVisibles((prev) => {
      const nx = new Set(prev)
      if (activo) nx.add(k); else nx.delete(k)
      try { localStorage.setItem(LS_COLUMNAS, JSON.stringify([...nx])) } catch { /* sin persistencia */ }
      return nx
    })
  }
  const restaurarColumnas = () => {
    const base = new Set(COLUMNAS.filter((c) => c.porDefecto).map((c) => c.key))
    setVisibles(base)
    try { localStorage.setItem(LS_COLUMNAS, JSON.stringify([...base])) } catch { /* sin persistencia */ }
  }

  const [dialogo, setDialogo] = useState(false)
  const [editando, setEditando] = useState<Deportista | null>(null)
  const [form, setForm] = useState<FormDep>(vacio)
  const [guardando, setGuardando] = useState(false)

  const cambiarOrden = (key: string) =>
    setOrden((o) => (o?.key === key ? (o.dir === 'asc' ? { key, dir: 'desc' } : null) : { key, dir: 'asc' }))

  const valorOrden = (d: Deportista, key: string): string | number => {
    switch (key) {
      case 'nombres': return nombreCompletoUI(d).toLowerCase()
      case 'dni': return d.dni
      case 'edad': return calcularEdad(d.fechaNacimiento) ?? -1
      case 'fechaNacimiento': return d.fechaNacimiento?.slice(0, 10) ?? ''
      case 'categoria': return d.categoria
      case 'sexo': return d.sexo
      case 'deporte': return d.deporte
      case 'nivelTecnico': return d.nivelTecnico
      case 'modalidad': return d.modalidad
      case 'ingreso': return d.fechaIngreso?.slice(0, 10) ?? ''
      case 'continuidad': return d.fechaVencimientoContinuidad?.slice(0, 10) ?? ''
      case 'aval': return d.fechaCaducidadAval?.slice(0, 10) ?? ''
      case 'pad': return d.pad ? 1 : 0
      case 'procedencia': return d.procedencia
      case 'telefono': return d.telefono ?? ''
      case 'entrenador': return d.entrenador ?? ''
      case 'estado': return d.retirado ? 2 : d.activo ? 0 : 1
      default: return ''
    }
  }

  const filtrados = useMemo(() => {
    const t = q.trim().toLowerCase()
    const min = edadMin === '' ? null : Number(edadMin)
    const max = edadMax === '' ? null : Number(edadMax)
    let f = lista.filter((d) => {
      if (t && !`${d.apellidoPaterno} ${d.apellidoMaterno} ${d.nombres} ${d.dni}`.toLowerCase().includes(t)) return false
      if (fCategoria !== 'todas' && d.categoria !== fCategoria) return false
      if (fSexo !== 'todos' && d.sexo !== fSexo) return false
      if (fModalidad !== 'todas' && d.modalidad !== fModalidad) return false
      if (fDeporte !== 'todos' && d.deporte !== fDeporte) return false
      if (fNivel !== 'todos' && d.nivelTecnico !== fNivel) return false
      if (fPad === 'si' && !d.pad) return false
      if (fPad === 'no' && d.pad) return false
      if (fAval !== 'todos' && estadoAval(d.fechaCaducidadAval).texto !== fAval) return false
      if (fEstado === 'activos' && (d.retirado || !d.activo)) return false
      if (fEstado === 'inactivos' && (d.retirado || d.activo)) return false
      if (fEstado === 'retirados' && !d.retirado) return false
      const e = calcularEdad(d.fechaNacimiento)
      if (min !== null && !isNaN(min) && (e === null || e < min)) return false
      if (max !== null && !isNaN(max) && (e === null || e > max)) return false
      return true
    })
    if (orden) {
      const { key, dir } = orden
      const s = dir === 'asc' ? 1 : -1
      f = [...f].sort((a, b) => {
        const va = valorOrden(a, key), vb = valorOrden(b, key)
        const vacioA = va === '' || va === -1, vacioB = vb === '' || vb === -1
        if (vacioA && vacioB) return 0
        if (vacioA) return 1 // vacíos al final siempre
        if (vacioB) return -1
        if (va < vb) return -1 * s
        if (va > vb) return 1 * s
        return 0
      })
    }
    return f
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lista, q, fCategoria, fSexo, fModalidad, fDeporte, fNivel, fPad, fAval, fEstado, edadMin, edadMax, orden])

  const numFiltros = [q, fCategoria, fSexo, fModalidad, fDeporte, fNivel, fPad, fAval, fEstado, edadMin, edadMax]
    .filter((v) => v !== '' && v !== 'todos' && v !== 'todas').length

  const limpiarFiltros = () => {
    setQ(''); setFCategoria('todas'); setFSexo('todos'); setFModalidad('todas')
    setFDeporte('todos'); setFNivel('todos'); setFPad('todos'); setFAval('todos'); setFEstado('todos')
    setEdadMin(''); setEdadMax(''); setOrden(null)
  }

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

  const alternarActivo = async (d: Deportista) => {
    const body = d.retirado ? { retirado: false, activo: true } : { activo: !d.activo }
    try {
      await api(`/api/deportistas/${d.id}`, { method: 'PUT', body: JSON.stringify(body) })
      toast({
        title: d.retirado ? `${nombreCompletoUI(d)} reactivado` : d.activo ? `${nombreCompletoUI(d)} → INACTIVO` : `${nombreCompletoUI(d)} → ACTIVO`,
        description: d.retirado
          ? 'Vuelve al grupo activo del CAR.'
          : d.activo
            ? 'Queda fuera del grupo activo (formatos, alimentación y análisis activos lo excluyen).'
            : 'Vuelve al grupo activo del CAR.',
      })
      recargar()
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    }
  }

  const set = (k: keyof FormDep, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }))

  const visiblesList = COLUMNAS.filter((c) => visibles.has(c.key))
  const colSpan = 3 + visiblesList.length
  const thOrden = (key: string, label: string, className = 'text-red-900') => (
    <TableHead key={key} className={`px-2 ${className}`}>
      <button type="button" className="inline-flex items-center gap-1 font-medium hover:underline" onClick={() => cambiarOrden(key)}>
        {label}
        {orden?.key === key
          ? (orden.dir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)
          : <ArrowUpDown className="h-3 w-3 opacity-40" />}
      </button>
    </TableHead>
  )
  const celda = (d: Deportista, key: ColKey) => {
    switch (key) {
      case 'dni': return <span className="text-sm">{d.dni}</span>
      case 'edad': {
        const e = calcularEdad(d.fechaNacimiento)
        return <span className="text-sm font-semibold text-slate-700">{e !== null ? e : '—'}</span>
      }
      case 'fechaNacimiento': return <span className="text-sm">{fmtFecha(d.fechaNacimiento) || '—'}</span>
      case 'categoria': return <BadgeCat>{d.categoria}</BadgeCat>
      case 'sexo': return <span className="text-sm">{d.sexo === 'FEMENINO' ? 'F' : 'M'}</span>
      case 'deporte': return <span className="text-sm">{d.deporte}<span className="block text-xs text-slate-500">{d.prueba ?? '—'}</span></span>
      case 'nivelTecnico': return <span className="text-sm">{d.nivelTecnico}</span>
      case 'modalidad': return <span className="text-sm">{d.modalidad}</span>
      case 'ingreso': return <span className="text-sm">{fmtFecha(d.fechaIngreso) || '—'}</span>
      case 'continuidad': return (
        <span className={`text-sm ${d.fechaVencimientoContinuidad ? 'text-slate-700' : 'text-slate-400'}`}>{fmtFecha(d.fechaVencimientoContinuidad) || '—'}</span>
      )
      case 'aval': return (
        <span>
          <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-bold ${estadoAval(d.fechaCaducidadAval).clase}`}>
            {estadoAval(d.fechaCaducidadAval).texto}
          </span>
          {d.fechaCaducidadAval && <span className="block text-xs text-slate-500">{fmtFecha(d.fechaCaducidadAval)}</span>}
        </span>
      )
      case 'pad': return <span className={`text-sm font-semibold ${d.pad ? 'text-green-700' : 'text-slate-400'}`}>{d.pad ? 'SI' : 'NO'}</span>
      case 'procedencia': return <span className="text-sm">{d.procedencia}</span>
      case 'telefono': return <span className="text-sm">{d.telefono ?? '—'}</span>
      case 'entrenador': return <span className="text-sm text-slate-600">{d.entrenador ?? '—'}</span>
      case 'estado': {
        const ei = estadoInfo(d)
        return <span className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-bold ${ei.clase}`}>{ei.texto}</span>
      }
      default: return null
    }
  }
  const edadForm = calcularEdad(form.fechaNacimiento)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-52 flex-1">
          <UserSearch className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input placeholder="Buscar por apellido o DNI…" className="pl-8" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <Select value={fCategoria} onValueChange={setFCategoria}>
          <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
          <SelectContent>{['todas', ...CATEGORIAS].map((c) => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={fSexo} onValueChange={setFSexo}>
          <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
          <SelectContent>{['todos', ...SEXOS].map((c) => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={fModalidad} onValueChange={setFModalidad}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>{['todas', ...MODALIDADES].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
        </Select>
        <Button variant={verFiltros ? 'default' : 'outline'} className={verFiltros ? 'bg-red-800 hover:bg-red-900' : 'border-red-800 text-red-900 hover:bg-red-50'} onClick={() => setVerFiltros((v) => !v)}>
          <Filter className="h-4 w-4" /> Filtros
          {numFiltros > 0 && <span className="ml-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-800 px-1 text-[11px] font-bold text-white">{numFiltros}</span>}
        </Button>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="border-red-800 text-red-900 hover:bg-red-50">
              <Columns3 className="h-4 w-4" /> Columnas
              <span className="ml-1 text-xs text-slate-500">{visiblesList.length}/{COLUMNAS.length}</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64" align="end">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-600">Variables a visualizar</p>
              <button type="button" className="text-xs font-medium text-red-800 hover:underline" onClick={restaurarColumnas}>Restaurar</button>
            </div>
            <div className="grid max-h-72 gap-1 overflow-y-auto pr-1">
              {COLUMNAS.map((c) => (
                <label key={c.key} className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-sm text-slate-700 hover:bg-slate-50">
                  <Checkbox checked={visibles.has(c.key)} onCheckedChange={(v) => toggleColumna(c.key, v === true)} className="accent-red-800" />
                  {c.etiqueta}
                </label>
              ))}
            </div>
          </PopoverContent>
        </Popover>
        <Button className="bg-red-800 hover:bg-red-900" onClick={abrirNuevo}><Plus className="h-4 w-4" /> Nuevo</Button>
      </div>

      {verFiltros && (
        <div className="rounded-xl border bg-white p-3 shadow-sm">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <label className="grid gap-1 text-xs font-medium text-slate-600">Deporte
              <Select value={fDeporte} onValueChange={setFDeporte}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{['todos', ...DEPORTES].map((c) => <SelectItem key={c} value={c}>{c === 'todos' ? 'TODOS' : c}</SelectItem>)}</SelectContent>
              </Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Nivel técnico
              <Select value={fNivel} onValueChange={setFNivel}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{['todos', ...NIVELES].map((c) => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
              </Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Seguro PAD
              <Select value={fPad} onValueChange={setFPad}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">TODOS</SelectItem>
                  <SelectItem value="si">CON PAD</SelectItem>
                  <SelectItem value="no">SIN PAD</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Aval médico
              <Select value={fAval} onValueChange={setFAval}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['todos', 'VIGENTE', 'POR VENCER', 'EXPIRADO', 'SIN REGISTRO'].map((c) => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}
                </SelectContent>
              </Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Estado
              <Select value={fEstado} onValueChange={setFEstado}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">TODOS</SelectItem>
                  <SelectItem value="activos">ACTIVOS</SelectItem>
                  <SelectItem value="inactivos">INACTIVOS</SelectItem>
                  <SelectItem value="retirados">RETIRADOS</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Edad mínima
              <Input type="number" min={0} max={80} placeholder="Ej. 15" value={edadMin} onChange={(e) => setEdadMin(e.target.value)} />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">Edad máxima
              <Input type="number" min={0} max={80} placeholder="Ej. 23" value={edadMax} onChange={(e) => setEdadMax(e.target.value)} />
            </label>
            <div className="flex items-end justify-end">
              <Button size="sm" variant="ghost" className="text-slate-500" onClick={limpiarFiltros}><X className="h-4 w-4" /> Limpiar filtros</Button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Mostrando <b className="text-slate-700">{filtrados.length}</b> de {lista.length} deportistas</span>
        {orden && <span>Ordenado por <b className="text-slate-700">{etiquetaDe(orden.key)}</b> ({orden.dir === 'asc' ? 'ascendente' : 'descendente'})</span>}
      </div>

      {/* ===== TABLA COMPACTA — tablet y desktop ===== */}
      <div className="hidden overflow-x-auto rounded-xl border bg-white shadow-sm md:block">
        <Table>
          <TableHeader>
            <TableRow className="bg-red-50">
              <TableHead className="w-8 px-2 text-red-900">N°</TableHead>
              {thOrden('nombres', 'Apellidos y nombres')}
              {visiblesList.map((c) => thOrden(c.key, c.etiqueta))}
              <TableHead className="px-2 text-right text-red-900">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {cargando && <TableRow><TableCell colSpan={colSpan} className="py-8 text-center text-slate-500">Cargando…</TableCell></TableRow>}
            {!cargando && filtrados.length === 0 && <TableRow><TableCell colSpan={colSpan} className="py-8 text-center text-slate-500">Sin resultados</TableCell></TableRow>}
            {filtrados.map((d, i) => (
              <TableRow key={d.id} className={d.retirado ? 'opacity-50' : !d.activo ? 'opacity-70' : ''}>
                <TableCell className="px-2 text-xs text-slate-500">{i + 1}</TableCell>
                <TableCell className="px-2 text-sm font-medium">{nombreCompletoUI(d)}</TableCell>
                {visiblesList.map((c) => <TableCell key={c.key} className="px-2">{celda(d, c.key)}</TableCell>)}
                <TableCell className="whitespace-nowrap px-2 text-right">
                  <Button size="icon" variant="ghost" title={d.retirado ? 'Reactivar (volver a ACTIVO)' : d.activo ? 'Pasar a INACTIVO' : 'Pasar a ACTIVO'}
                    className={`h-7 w-7 ${d.retirado ? 'text-slate-400' : d.activo ? 'text-green-700' : 'text-amber-600'}`} onClick={() => alternarActivo(d)}><Power className="h-4 w-4" /></Button>
                  <Button size="icon" variant="ghost" title="Ficha 360°" className="h-7 w-7 text-red-900" onClick={() => setDepIdFicha(d.id)}><FileText className="h-4 w-4" /></Button>
                  <Button size="icon" variant="ghost" title="Editar" className="h-7 w-7" onClick={() => abrirEdicion(d)}><Pencil className="h-4 w-4" /></Button>
                  <Button size="icon" variant="ghost" title="Eliminar" className="h-7 w-7 text-red-600" onClick={() => eliminar(d)}><Trash2 className="h-4 w-4" /></Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* ===== TARJETAS — celular (sin barras de desplazamiento) ===== */}
      <div className="space-y-2.5 md:hidden">
        {cargando && <p className="py-8 text-center text-sm text-slate-500">Cargando…</p>}
        {!cargando && filtrados.length === 0 && <p className="py-8 text-center text-sm text-slate-500">Sin resultados</p>}
        {filtrados.map((d, i) => (
          <div key={d.id} className={`rounded-xl border bg-white p-3 shadow-sm ${d.retirado ? 'opacity-50' : !d.activo ? 'opacity-70' : ''}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-800">{i + 1}. {nombreCompletoUI(d)}</p>
                <p className="text-xs text-slate-500">DNI {d.dni}</p>
              </div>
              <BadgeCat>{d.categoria}</BadgeCat>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
              <span className="rounded bg-slate-100 px-1.5 py-0.5 font-semibold text-slate-700">{calcularEdad(d.fechaNacimiento) ?? '—'} años</span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">{d.sexo === 'FEMENINO' ? 'F' : 'M'}</span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">{d.deporte}{d.prueba ? ` · ${d.prueba}` : ''}</span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">{d.modalidad}</span>
              {d.pad && <span className="rounded bg-green-100 px-1.5 py-0.5 font-bold text-green-800">PAD</span>}
              <span className={`rounded px-1.5 py-0.5 font-bold ${estadoAval(d.fechaCaducidadAval).clase}`}>{estadoAval(d.fechaCaducidadAval).texto}</span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">Ingreso: {fmtFecha(d.fechaIngreso) || '—'}</span>
              {d.fechaVencimientoContinuidad && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">Continuidad: {fmtFecha(d.fechaVencimientoContinuidad)}</span>}
              <span className={`rounded px-1.5 py-0.5 font-bold ${estadoInfo(d).clase}`}>{estadoInfo(d).texto}</span>
            </div>
            <div className="mt-2.5 flex gap-1.5 border-t pt-2">
              <Button size="sm" variant="outline" className="h-7 flex-1 text-xs text-red-900" onClick={() => setDepIdFicha(d.id)}><ClipboardList className="h-3.5 w-3.5" /> Ficha 360°</Button>
              <Button size="sm" variant="outline" title={d.retirado ? 'Reactivar (volver a ACTIVO)' : d.activo ? 'Pasar a INACTIVO' : 'Pasar a ACTIVO'}
                className={`h-7 w-9 p-0 ${d.retirado ? 'text-slate-400' : d.activo ? 'text-green-700' : 'text-amber-600'}`} onClick={() => alternarActivo(d)}><Power className="h-3.5 w-3.5" /></Button>
              <Button size="sm" variant="outline" title="Editar" className="h-7 w-9 p-0" onClick={() => abrirEdicion(d)}><Pencil className="h-3.5 w-3.5" /></Button>
              <Button size="sm" variant="outline" title="Eliminar" className="h-7 w-9 p-0 text-red-600" onClick={() => eliminar(d)}><Trash2 className="h-3.5 w-3.5" /></Button>
            </div>
          </div>
        ))}
      </div>

      <Dialog open={dialogo} onOpenChange={setDialogo}>
        <DialogContent className="max-h-[92vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editando ? `Editar: ${nombreCompletoUI(editando)}` : 'Nuevo deportista'}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-3">
            {([['apellidoPaterno', 'Apellido paterno', 'text'], ['apellidoMaterno', 'Apellido materno', 'text'], ['nombres', 'Nombres', 'text'], ['dni', 'DNI', 'text'], ['fechaNacimiento', 'Fecha de nacimiento', 'date'], ['fechaIngreso', 'Fecha de ingreso', 'date'], ['fechaVencimientoContinuidad', 'Vencimiento de continuidad', 'date'], ['fechaCaducidadAval', 'Caducidad del aval médico', 'date'], ['prueba', 'Prueba (ej. 800 m)', 'text'], ['telefono', 'Teléfono', 'text'], ['entrenador', 'Entrenador', 'text']] as const).map(([k, lbl, tp]) => (
              <label key={k} className="grid gap-1 text-xs font-medium text-slate-600">
                {lbl}{k === 'fechaNacimiento' && edadForm !== null ? ` (Edad: ${edadForm} años)` : ''}
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
            <label className="grid gap-1 text-xs font-medium text-slate-600">Estado
              <Select value={form.retirado ? 'RETIRADO' : form.activo ? 'ACTIVO' : 'INACTIVO'}
                onValueChange={(v) => setForm((f) => ({ ...f, retirado: v === 'RETIRADO', activo: v === 'ACTIVO' }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVO">ACTIVO — entrena actualmente</SelectItem>
                  <SelectItem value="INACTIVO">INACTIVO — temporalmente fuera</SelectItem>
                  <SelectItem value="RETIRADO">RETIRADO — dejó el CAR</SelectItem>
                </SelectContent>
              </Select>
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
