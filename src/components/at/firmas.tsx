'use client'

// FIRMAS — carga y gestión de las firmas que se incrustan en los formatos oficiales (AT-F1, AT-F3, AT-F8, AT-F9)
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Upload, Trash2, Loader2, FileSignature, Download, CheckCircle2, XCircle, RefreshCw, Pencil, Plus } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api } from './ui-at'

type Firma = { id: number; clave: string; nombre: string; cargo: string; imagen: string; formatos: string; activo: boolean; createdAt: string }

// Formatos donde se pueden incrustar firmas
const FORMATOS = [
  { codigo: 'F1', etiqueta: 'AT-F1 · Consolidado mensual del CAR' },
  { codigo: 'F3', etiqueta: 'AT-F3 · Informe mensual del deportista' },
  { codigo: 'F8', etiqueta: 'AT-F8 · Plan de trabajo mensual del JUT' },
  { codigo: 'F9', etiqueta: 'AT-F9 · Informe de cumplimiento del JUT' },
] as const
const CODIGOS = FORMATOS.map((f) => f.codigo)
const etiquetaFormato = (c: string) => FORMATOS.find((f) => f.codigo === c)?.etiqueta ?? c

// Ranuras oficiales: alimentan las zonas de firma fijas de las plantillas IPD
const SLOTS = [
  { clave: 'JUT', titulo: 'Jefe de Unidad Técnica', cargoBase: 'JEFE DE UNIDAD TECNICA', formatosDefecto: ['F1', 'F9', 'F8'] },
  { clave: 'ENTRENADOR', titulo: 'Entrenador responsable', cargoBase: 'ENTRENADOR', formatosDefecto: ['F3', 'F1'] },
  { clave: 'DINADAF', titulo: 'Representante DINADAF', cargoBase: 'REPRESENTANTE DE LA DINADAF', formatosDefecto: ['F1', 'F8'] },
]
const CLAVES_OFICIALES = SLOTS.map((s) => s.clave)

// Redimensiona la imagen en el navegador (máx. 800 px de ancho, PNG con transparencia)
const procesarImagen = (archivo: File): Promise<string> => new Promise((resolve, reject) => {
  const lector = new FileReader()
  lector.onload = () => {
    const img = new Image()
    img.onload = () => {
      const escala = Math.min(1, 800 / (img.width || 1))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round((img.width || 1) * escala)
      canvas.height = Math.round((img.height || 1) * escala)
      const ctx = canvas.getContext('2d')
      if (!ctx) return reject(new Error('No se pudo procesar la imagen'))
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/png'))
    }
    img.onerror = () => reject(new Error('Formato de imagen no válido'))
    img.src = String(lector.result)
  }
  lector.onerror = () => reject(new Error('No se pudo leer el archivo'))
  lector.readAsDataURL(archivo)
})

type Editando = { clave: string; titulo: string; cargoBase?: string; esNueva: boolean; esOficial: boolean }

export default function Firmas() {
  const [lista, setLista] = useState<Firma[]>([])
  const [cargando, setCargando] = useState(true)
  const [editando, setEditando] = useState<Editando | null>(null)
  const [form, setForm] = useState({ imagen: '', nombre: '', cargo: '', activo: true, formatos: [] as string[] })
  const [guardando, setGuardando] = useState(false)
  const [procesando, setProcesando] = useState(false)

  const recargar = async () => {
    setCargando(true)
    try { setLista(await api<Firma[]>('/api/firmas')) } finally { setCargando(false) }
  }
  useEffect(() => { recargar() }, [])

  const porClave = new Map(lista.map((f) => [f.clave, f]))
  const oficiales = lista.filter((f) => CLAVES_OFICIALES.includes(f.clave))
  const personalizadas = lista.filter((f) => !CLAVES_OFICIALES.includes(f.clave))

  // Abrir el diálogo: nueva firma personalizada, ranura oficial vacía o edición de una existente
  const abrirDialogo = (e: Editando) => {
    const f = porClave.get(e.clave)
    const defecto = SLOTS.find((s) => s.clave === e.clave)?.formatosDefecto ?? []
    setForm({
      imagen: f?.imagen ?? '', nombre: f?.nombre ?? '', cargo: f?.cargo ?? e.cargoBase ?? '',
      activo: f?.activo ?? true,
      formatos: f ? (f.formatos ? f.formatos.split(',') : []) : defecto,
    })
    setEditando(e)
  }

  const elegirArchivo = async (archivo: File | null | undefined) => {
    if (!archivo) return
    if (!/image\/(png|jpe?g)/.test(archivo.type)) {
      toast({ title: 'Formato no válido', description: 'Usa una imagen PNG o JPG.', variant: 'destructive' })
      return
    }
    setProcesando(true)
    try {
      const dataUrl = await procesarImagen(archivo)
      setForm((f) => ({ ...f, imagen: dataUrl }))
    }
    catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error al procesar', variant: 'destructive' }) }
    finally { setProcesando(false) }
  }

  const guardar = async () => {
    if (!editando) return
    if (!form.nombre.trim() || !form.cargo.trim()) {
      toast({ title: 'Datos incompletos', description: 'Indica el nombre del firmante y su cargo.', variant: 'destructive' })
      return
    }
    if (!form.imagen) {
      toast({ title: 'Falta la imagen', description: 'Selecciona la imagen de la firma escaneada.', variant: 'destructive' })
      return
    }
    if (form.formatos.length === 0) {
      toast({ title: 'Sin formato de destino', description: 'Marca al menos un formato donde se incrustará la firma.', variant: 'destructive' })
      return
    }
    setGuardando(true)
    try {
      await api('/api/firmas', { method: 'POST', body: JSON.stringify({ clave: editando.clave, ...form, formatos: form.formatos.join(',') }) })
      toast({ title: editando.esNueva ? 'Firma creada' : 'Firma guardada', description: `Se incrustará en: ${form.formatos.map((c) => `AT-${c}`).join(', ')}.` })
      setEditando(null)
      recargar()
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    } finally { setGuardando(false) }
  }

  const alternarActivo = async (f: Firma) => {
    try {
      await api('/api/firmas', { method: 'POST', body: JSON.stringify({ clave: f.clave, nombre: f.nombre, cargo: f.cargo, imagen: f.imagen, formatos: f.formatos, activo: !f.activo }) })
      toast({ title: !f.activo ? 'Firma activada' : 'Firma desactivada', description: !f.activo ? 'Se usará en los formatos.' : 'No se incrustará en los formatos.' })
      recargar()
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    }
  }

  const eliminar = async (f: Firma) => {
    if (!confirm(`¿Eliminar la firma de ${f.nombre}?`)) return
    try { await api(`/api/firmas?id=${f.id}`, { method: 'DELETE' }); toast({ title: 'Firma eliminada' }); recargar() }
    catch (e) { toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' }) }
  }

  const descargarFirma = (f: Firma) => {
    const a = document.createElement('a')
    a.href = f.imagen
    a.download = `FIRMA_${f.clave}_${f.nombre.replace(/\s+/g, '_')}.png`
    document.body.appendChild(a); a.click(); a.remove()
  }

  const nuevaClave = () => {
    let n = personalizadas.length + 1
    let clave = `PERS-${String(n).padStart(2, '0')}`
    while (porClave.has(clave)) { n += 1; clave = `PERS-${String(n).padStart(2, '0')}` }
    return clave
  }

  // ===== Tarjeta de firma (ranura oficial o personalizada) =====
  const TarjetaFirma = ({ titulo, subtitulo, f, formatosMostrar }: { titulo: string; subtitulo: string; f?: Firma; formatosMostrar: string[] }) => (
    <div className="flex flex-col rounded-xl border bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-800">{titulo}</p>
          <p className="font-mono text-[11px] uppercase text-slate-400">{subtitulo}</p>
        </div>
        {f && (
          <span className={`inline-flex shrink-0 items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold ${f.activo ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-500'}`}>
            {f.activo ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />} {f.activo ? 'ACTIVA' : 'INACTIVA'}
          </span>
        )}
      </div>

      <div className={`mt-3 flex h-24 items-center justify-center rounded-lg border ${f ? 'border-slate-200 bg-white' : 'border-dashed bg-slate-50'}`}>
        {f ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={f.imagen} alt={`Firma ${titulo}`} className="max-h-20 max-w-[90%] object-contain" />
        ) : (
          <span className="text-xs text-slate-400">Sin firma registrada</span>
        )}
      </div>

      {f && (
        <div className="mt-2 min-w-0 text-xs">
          <p className="truncate font-semibold text-slate-700">{f.nombre}</p>
          <p className="truncate text-slate-500">{f.cargo}</p>
        </div>
      )}

      {/* Formatos de destino */}
      <div className="mt-2 flex flex-wrap gap-1">
        {(f ? (f.formatos ? f.formatos.split(',') : []) : formatosMostrar).map((c) => (
          <span key={c} className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-bold text-red-900">AT-{c}</span>
        ))}
        {f && !f.formatos && <span className="text-[10px] text-slate-400">Sin formato asignado</span>}
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5 border-t pt-2">
        <Button size="sm" className="h-7 flex-1 bg-red-800 text-xs text-white hover:bg-red-900" onClick={() => abrirDialogo({ clave: subtitulo, titulo, cargoBase: SLOTS.find((s) => s.clave === subtitulo)?.cargoBase, esNueva: !f, esOficial: CLAVES_OFICIALES.includes(subtitulo) })}>
          {f ? <><Pencil className="h-3.5 w-3.5" /> Editar</> : <><Upload className="h-3.5 w-3.5" /> Subir firma</>}
        </Button>
        {f && (
          <>
            <Button size="sm" variant="outline" title="Descargar" className="h-7 w-8 p-0" onClick={() => descargarFirma(f)}><Download className="h-3.5 w-3.5" /></Button>
            <Button size="sm" variant="outline" title={f.activo ? 'Desactivar' : 'Activar'} className="h-7 w-8 p-0" onClick={() => alternarActivo(f)}><RefreshCw className="h-3.5 w-3.5" /></Button>
            <Button size="sm" variant="outline" title="Eliminar" className="h-7 w-8 p-0 text-red-600" onClick={() => eliminar(f)}><Trash2 className="h-3.5 w-3.5" /></Button>
          </>
        )}
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <p className="text-sm text-slate-600">
          Sube aquí las <b>firmas escaneadas</b> (PNG o JPG, ideal con fondo transparente). Cada firma guarda el <b>nombre</b> del firmante,
          su <b>cargo</b> y los <b>formatos donde se incrusta</b> (AT-F1, AT-F3, AT-F8, AT-F9), tanto en la versión Excel como en el PDF.
          Puedes editar cualquier dato, crear firmas adicionales (psicólogo, médico, etc.) y desactivarlas cuando cambie el responsable.
        </p>
      </div>

      {cargando ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-red-800" /></div>
      ) : (
        <>
          {/* ===== Ranuras oficiales ===== */}
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Ranuras oficiales de las plantillas</p>
            <div className="grid gap-4 md:grid-cols-3">
              {SLOTS.map((s) => (
                <TarjetaFirma key={s.clave} titulo={s.titulo} subtitulo={s.clave} f={porClave.get(s.clave)} formatosMostrar={s.formatosDefecto} />
              ))}
            </div>
          </div>

          {/* ===== Firmas personalizadas ===== */}
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Firmas adicionales (psicólogo, médico, etc.)</p>
            <div className="grid gap-4 md:grid-cols-3">
              <button type="button" onClick={() => abrirDialogo({ clave: nuevaClave(), titulo: 'Nueva firma', esNueva: true, esOficial: false })}
                className="flex min-h-44 flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-slate-50 p-4 text-slate-500 transition-colors hover:border-red-800 hover:bg-red-50 hover:text-red-900">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm"><Plus className="h-5 w-5" /></span>
                <span className="text-sm font-semibold">Nueva firma</span>
                <span className="px-2 text-center text-[11px] text-slate-400">Sube otra firma y elige en qué formatos se incrusta</span>
              </button>
              {personalizadas.map((f) => (
                <TarjetaFirma key={f.clave} titulo={f.nombre || f.clave} subtitulo={f.clave} f={f} formatosMostrar={[]} />
              ))}
            </div>
          </div>
        </>
      )}

      {/* ===== Diálogo de carga/edición ===== */}
      <Dialog open={!!editando} onOpenChange={(v) => !v && setEditando(null)}>
        <DialogContent className="max-h-[92vh] max-w-lg overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSignature className="h-5 w-5 text-red-800" />
              {editando?.esNueva ? 'Nueva firma' : `Editar: ${editando?.titulo}`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="grid cursor-pointer gap-1 rounded-lg border border-dashed p-3 text-center text-xs font-medium text-slate-600 hover:bg-slate-50">
              <span className="mx-auto inline-flex items-center gap-1 text-red-900">
                <Upload className="h-4 w-4" /> {form.imagen ? 'Reemplazar imagen (opcional)' : 'Seleccionar imagen de la firma (PNG/JPG)'}
              </span>
              {procesando && <Loader2 className="mx-auto h-4 w-4 animate-spin" />}
              <input type="file" accept="image/png,image/jpeg" className="hidden" onChange={(e) => elegirArchivo(e.target.files?.[0])} />
            </label>
            {form.imagen && (
              <div className="flex h-24 items-center justify-center rounded-lg border bg-white">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={form.imagen} alt="Vista previa de la firma" className="max-h-20 max-w-[90%] object-contain" />
              </div>
            )}
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Nombre del firmante
              <Input value={form.nombre} onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} placeholder="Ej. JUAN PEREZ QUISPE" />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Cargo
              <Input value={form.cargo} onChange={(e) => setForm((f) => ({ ...f, cargo: e.target.value }))} placeholder={editando?.cargoBase ?? 'Ej. PSICOLOGO DEL CAR'} />
            </label>

            {/* Formatos de destino */}
            <div className="rounded-lg border p-3">
              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">¿En qué formatos se incrusta?</p>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {FORMATOS.map((fmt) => (
                  <label key={fmt.codigo} className="flex cursor-pointer items-start gap-2 rounded p-1.5 text-xs text-slate-700 hover:bg-slate-50">
                    <input
                      type="checkbox"
                      checked={form.formatos.includes(fmt.codigo)}
                      onChange={(e) => setForm((f) => ({ ...f, formatos: e.target.checked ? [...f.formatos, fmt.codigo] : f.formatos.filter((c) => c !== fmt.codigo) }))}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-red-800"
                    />
                    <span><b>AT-{fmt.codigo}</b><span className="block text-[10px] text-slate-500">{fmt.etiqueta.split('·')[1]?.trim()}</span></span>
                  </label>
                ))}
              </div>
              <p className="mt-2 text-[10px] leading-snug text-slate-400">
                Cada formato toma la primera firma disponible (ranura oficial y, si falta, una firma adicional).
              </p>
            </div>

            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm((f) => ({ ...f, activo: e.target.checked }))} className="h-4 w-4 accent-red-800" />
              Firma activa (se incrusta en los formatos)
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditando(null)}>Cancelar</Button>
            <Button className="bg-red-800 hover:bg-red-900" disabled={guardando || procesando} onClick={guardar}>
              {guardando ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Guardar firma
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
