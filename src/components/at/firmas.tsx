'use client'

// FIRMAS — carga y gestión de las firmas que se incrustan en los formatos oficiales (AT-F1, AT-F3, AT-F9)
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Upload, Trash2, Loader2, FileSignature, Download, CheckCircle2, XCircle, RefreshCw } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import { api } from './ui-at'

type Firma = { id: number; clave: string; nombre: string; cargo: string; imagen: string; activo: boolean; createdAt: string }

// Ranuras de firma: cada una alimenta las zonas de firma de los formatos oficiales
const SLOTS = [
  { clave: 'JUT', titulo: 'Jefe de Unidad Técnica', uso: 'Se incrusta en el AT-F1 (consolidado CAR) y en el AT-F9 (evaluación del JUT).', cargoBase: 'JEFE DE UNIDAD TECNICA' },
  { clave: 'ENTRENADOR', titulo: 'Entrenador responsable', uso: 'Se incrusta en el AT-F3 (informe mensual del deportista).', cargoBase: 'ENTRENADOR' },
  { clave: 'DINADAF', titulo: 'Representante DINADAF', uso: 'Firma alternativa del AT-F1 cuando firma la DINADAF.', cargoBase: 'REPRESENTANTE DE LA DINADAF' },
]

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

export default function Firmas() {
  const [lista, setLista] = useState<Firma[]>([])
  const [cargando, setCargando] = useState(true)
  const [slot, setSlot] = useState<typeof SLOTS[number] | null>(null)
  const [form, setForm] = useState({ imagen: '', nombre: '', cargo: '', activo: true })
  const [guardando, setGuardando] = useState(false)
  const [procesando, setProcesando] = useState(false)

  const recargar = async () => {
    setCargando(true)
    try { setLista(await api<Firma[]>('/api/firmas')) } finally { setCargando(false) }
  }
  useEffect(() => { recargar() }, [])

  const porClave = new Map(lista.map((f) => [f.clave, f]))

  const abrirSlot = (s: typeof SLOTS[number]) => {
    const f = porClave.get(s.clave)
    setForm({ imagen: f?.imagen ?? '', nombre: f?.nombre ?? '', cargo: f?.cargo ?? s.cargoBase, activo: f?.activo ?? true })
    setSlot(s)
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
    if (!slot) return
    if (!form.nombre.trim() || !form.cargo.trim() || !form.imagen) {
      toast({ title: 'Datos incompletos', description: 'Selecciona la imagen de la firma e indica nombre y cargo.', variant: 'destructive' })
      return
    }
    setGuardando(true)
    try {
      await api('/api/firmas', { method: 'POST', body: JSON.stringify({ clave: slot.clave, ...form }) })
      toast({ title: 'Firma guardada', description: `Disponible para ${slot.uso.split('Se incrusta en')[1] ?? 'los formatos'}.` })
      setSlot(null)
      recargar()
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Error', variant: 'destructive' })
    } finally { setGuardando(false) }
  }

  const alternarActivo = async (f: Firma) => {
    try {
      await api('/api/firmas', { method: 'POST', body: JSON.stringify({ clave: f.clave, nombre: f.nombre, cargo: f.cargo, imagen: f.imagen, activo: !f.activo }) })
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

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <p className="text-sm text-slate-600">
          Sube aquí las <b>firmas escaneadas</b> (PNG o JPG, ideal con fondo transparente) que se incrustan automáticamente
          en las zonas de firma de los formatos <b>AT-F1</b>, <b>AT-F3</b> y <b>AT-F9</b>, tanto en la versión Excel como en el PDF.
          Cada ranura guarda una imagen, el nombre del firmante y su cargo; puedes reemplazarla o desactivarla cuando cambie el responsable.
        </p>
      </div>

      {cargando ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-red-800" /></div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {SLOTS.map((s) => {
            const f = porClave.get(s.clave)
            return (
              <div key={s.clave} className="flex flex-col rounded-xl border bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-800">{s.titulo}</p>
                    <p className="font-mono text-[11px] uppercase text-slate-400">{s.clave}</p>
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
                    <img src={f.imagen} alt={`Firma ${s.titulo}`} className="max-h-20 max-w-[90%] object-contain" />
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

                <p className="mt-2 flex-1 text-[11px] leading-snug text-slate-500">{s.uso}</p>

                <div className="mt-3 flex flex-wrap gap-1.5 border-t pt-2">
                  <Button size="sm" className="h-7 flex-1 bg-red-800 text-xs text-white hover:bg-red-900" onClick={() => abrirSlot(s)}>
                    <Upload className="h-3.5 w-3.5" /> {f ? 'Reemplazar' : 'Subir firma'}
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
          })}
        </div>
      )}

      {/* ===== Diálogo de carga/edición ===== */}
      <Dialog open={!!slot} onOpenChange={(v) => !v && setSlot(null)}>
        <DialogContent className="max-h-[92vh] max-w-lg overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><FileSignature className="h-5 w-5 text-red-800" /> {slot?.titulo} — firma</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="grid cursor-pointer gap-1 rounded-lg border border-dashed p-3 text-center text-xs font-medium text-slate-600 hover:bg-slate-50">
              <span className="mx-auto inline-flex items-center gap-1 text-red-900"><Upload className="h-4 w-4" /> Seleccionar imagen de la firma (PNG/JPG)</span>
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
              <Input value={form.cargo} onChange={(e) => setForm((f) => ({ ...f, cargo: e.target.value }))} placeholder={slot?.cargoBase} />
            </label>
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm((f) => ({ ...f, activo: e.target.checked }))} className="h-4 w-4 accent-red-800" />
              Firma activa (se incrusta en los formatos)
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSlot(null)}>Cancelar</Button>
            <Button className="bg-red-800 hover:bg-red-900" disabled={guardando || procesando} onClick={guardar}>
              {guardando ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Guardar firma
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
