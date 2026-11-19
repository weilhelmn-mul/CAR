// ============================================================================
// Capa de datos del sistema — doble motor:
//   · DATA_BACKEND=firestore → Firestore (Google) — producción / despliegue.
//     Credenciales: FIREBASE_SERVICE_ACCOUNT (JSON) o ADC (Cloud Run).
//   · resto → Prisma + SQLite (desarrollo local, comportamiento verificado).
// La API expuesta es idéntica al subconjunto de Prisma que usa la aplicación
// (findMany, findUnique, create, update, delete, upsert, include, where con
// contains/gte/lt/OR, orderBy), por eso las rutas API no cambian.
// ============================================================================

import { PrismaClient } from '@prisma/client'
import { getApps, initializeApp, cert, type App } from 'firebase-admin/app'
import { getFirestore, type Firestore, type QueryDocumentSnapshot } from 'firebase-admin/firestore'

const MODO = (process.env.DATA_BACKEND ?? 'prisma').toLowerCase() === 'firestore' ? 'firestore' : 'prisma'

const COLECCIONES: Record<string, string> = {
  deportista: 'deportistas',
  resultado: 'resultados',
  alimentacion: 'alimentaciones',
  firma: 'firmas',
  formatoF1: 'formatos_f1',
  formatoF3: 'formatos_f3',
  formatoF8: 'formatos_f8',
  formatoF9: 'formatos_f9',
}

// Campos de fecha: se guardan como ISO en Firestore y se devuelven como Date (igual que Prisma)
const CAMPOS_FECHA: Record<string, string[]> = {
  deportista: ['fechaIngreso', 'fechaNacimiento', 'fechaVencimientoContinuidad', 'fechaCaducidadAval', 'createdAt'],
  resultado: ['fecha', 'createdAt'],
  firma: ['createdAt'],
  formatoF1: ['updatedAt'],
  formatoF3: ['updatedAt'],
  formatoF8: ['updatedAt'],
  formatoF9: ['updatedAt'],
}

// Relaciones incluidas (include) — fk = campo en el modelo hijo
const RELACIONES: Record<string, { campo: string; modelo: string; fk: string; ordenPor: string }[]> = {
  deportista: [
    { campo: 'resultados', modelo: 'resultado', fk: 'deportistaId', ordenPor: 'fecha' },
    { campo: 'alimentaciones', modelo: 'alimentacion', fk: 'deportistaId', ordenPor: 'periodo' },
    { campo: 'informesF3', modelo: 'formatoF3', fk: 'deportistaId', ordenPor: 'periodo' },
  ],
}

const TIENE_UPDATED_AT = new Set(['formatoF1', 'formatoF3', 'formatoF8', 'formatoF9'])

type Fila = Record<string, unknown>
type Where = Record<string, unknown>

// ---------------- conversión de valores ----------------

function limpiarFirestore(v: unknown): unknown {
  // Firestore no acepta null como elemento directo de un array
  if (Array.isArray(v)) return v.map((x) => (x === null || x === undefined ? '' : limpiarFirestore(x)))
  if (v && typeof v === 'object') {
    const o: Record<string, unknown> = {}
    for (const [k, x] of Object.entries(v as Record<string, unknown>)) o[k] = limpiarFirestore(x)
    return o
  }
  return v
}

function encode(modelo: string, data: Where): Where {
  const fechas = CAMPOS_FECHA[modelo] ?? []
  const out: Where = {}
  for (const [k, v] of Object.entries(data)) {
    if (v === undefined) continue // Prisma: undefined = no tocar el campo
    if (fechas.includes(k)) out[k] = v === null ? null : v instanceof Date ? v.toISOString() : String(v)
    else if (v instanceof Date) out[k] = v.toISOString()
    else out[k] = limpiarFirestore(v)
  }
  return out
}

function decode(modelo: string, snap: QueryDocumentSnapshot): Fila {
  const d = snap.data() ?? {}
  const fechas = CAMPOS_FECHA[modelo] ?? []
  const fila: Fila = { id: Number(snap.id) }
  for (const [k, v] of Object.entries(d)) {
    if (fechas.includes(k)) fila[k] = v === null || v === undefined ? null : new Date(String(v))
    else fila[k] = v
  }
  return fila
}

// ---------------- filtrado y orden (semántica Prisma) ----------------

function comparar(a: unknown, b: unknown): number {
  const vacioA = a === null || a === undefined
  const vacioB = b === null || b === undefined
  if (vacioA && vacioB) return 0
  if (vacioA) return 1
  if (vacioB) return -1
  if (a instanceof Date && b instanceof Date) return a.getTime() - b.getTime()
  if (typeof a === 'number' && typeof b === 'number') return a - b
  if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b)
  const sa = String(a), sb = String(b)
  return sa < sb ? -1 : sa > sb ? 1 : 0
}

type Cond = { contains?: unknown; gte?: unknown; gt?: unknown; lte?: unknown; lt?: unknown; not?: unknown; in?: unknown[] }

function cumpleValor(valorCampo: unknown, c: Cond): boolean {
  if (c.contains !== undefined) {
    return String(valorCampo ?? '').toLowerCase().includes(String(c.contains).toLowerCase())
  }
  if (Array.isArray(c.in)) {
    return c.in.some((x) => comparar(valorCampo, x) === 0)
  }
  if (c.gte !== undefined && !(comparar(valorCampo, c.gte) >= 0)) return false
  if (c.gt !== undefined && !(comparar(valorCampo, c.gt) > 0)) return false
  if (c.lte !== undefined && !(comparar(valorCampo, c.lte) <= 0)) return false
  if (c.lt !== undefined && !(comparar(valorCampo, c.lt) < 0)) return false
  if (c.not !== undefined && comparar(valorCampo, c.not) === 0) return false
  return true
}

function cumple(fila: Fila, donde?: Where): boolean {
  if (!donde) return true
  for (const [k, v] of Object.entries(donde)) {
    if (k === 'OR') {
      const alternativas = (v as Where[]) ?? []
      if (alternativas.length && !alternativas.some((alt) => cumple(fila, alt))) return false
      continue
    }
    if (k === 'AND') {
      const conjuntos = (v as Where[]) ?? []
      if (!conjuntos.every((alt) => cumple(fila, alt))) return false
      continue
    }
    const valorCampo = fila[k]
    if (v !== null && typeof v === 'object' && !(v instanceof Date)) {
      if (!cumpleValor(valorCampo, v as Cond)) return false
    } else {
      if (comparar(valorCampo, v) !== 0) return false
    }
  }
  return true
}

function ordenar(lista: Fila[], orderBy?: unknown): void {
  if (!orderBy) return
  const normas: [string, 'asc' | 'desc'][] = Array.isArray(orderBy)
    ? (orderBy as Where[]).map((o) => [Object.keys(o)[0], (o[Object.keys(o)[0]] as 'asc' | 'desc') ?? 'asc'])
    : Object.entries(orderBy as Where).map(([campo, dir]) => [campo, (dir as 'asc' | 'desc') ?? 'asc'])
  if (!normas.length) return
  lista.sort((a, b) => {
    for (const [campo, dir] of normas) {
      const cmp = comparar(a[campo], b[campo])
      if (cmp !== 0) return dir === 'desc' ? -cmp : cmp
    }
    return 0
  })
}

// ---------------- adaptador Firestore ----------------

let appFirebase: App | null = null

function firestore(): Firestore {
  if (!appFirebase) {
    const opciones: { projectId: string; credential?: unknown } = {
      projectId: process.env.FIREBASE_PROJECT_ID || 'car-cusco',
    }
    const saJson = process.env.FIREBASE_SERVICE_ACCOUNT
    if (saJson) opciones.credential = cert(JSON.parse(saJson))
    appFirebase = getApps().length ? getApps()[0] : initializeApp(opciones as never)
  }
  return getFirestore(appFirebase as never)
}

async function nextId(fs: Firestore, modelo: string): Promise<number> {
  const contRef = fs.collection('meta').doc('contadores')
  return fs.runTransaction(async (t) => {
    const snap = await t.get(contRef)
    let actual = (snap.data() ?? {})[modelo]
    if (typeof actual !== 'number') {
      const todos = await fs.collection(COLECCIONES[modelo]).get()
      actual = todos.docs.reduce((max, d) => Math.max(max, Number(d.id) || 0), 0)
    }
    const siguiente = actual + 1
    t.set(contRef, { [modelo]: siguiente }, { merge: true })
    return siguiente
  })
}

async function buscarDoc(fs: Firestore, modelo: string, donde: Where): Promise<QueryDocumentSnapshot | null> {
  const col = fs.collection(COLECCIONES[modelo])
  if (donde.id !== undefined) {
    const snap = await col.doc(String(Number(donde.id))).get()
    return snap.exists ? (snap as QueryDocumentSnapshot) : null
  }
  if (donde.clave !== undefined) {
    const q = await col.where('clave', '==', donde.clave).limit(1).get()
    return q.docs[0] ?? null
  }
  if (donde.periodo !== undefined) {
    const q = await col.where('periodo', '==', donde.periodo).limit(1).get()
    return q.docs[0] ?? null
  }
  if (donde.deportistaId_periodo !== undefined) {
    const cp = donde.deportistaId_periodo as Where
    const q = await col
      .where('deportistaId', '==', Number(cp.deportistaId))
      .where('periodo', '==', cp.periodo)
      .limit(1)
      .get()
    return q.docs[0] ?? null
  }
  throw new Error(`Criterio de búsqueda no soportado en ${modelo}`)
}

async function conRelaciones(fs: Firestore, modelo: string, lista: Fila[], include?: Where): Promise<void> {
  if (!include) return
  for (const [campo, opciones] of Object.entries(include)) {
    // include: { deportista: true } en resultados → adjunta el deportista completo
    if (modelo === 'resultado' && campo === 'deportista') {
      const deps = await fs.collection('deportistas').get()
      const mapa = new Map<number, Fila>(deps.docs.map((d) => [Number(d.id), decode('deportista', d)]))
      for (const fila of lista) fila.deportista = mapa.get(Number(fila.deportistaId)) ?? null
      continue
    }
    const rel = RELACIONES[modelo]?.find((r) => r.campo === campo)
    if (!rel) continue
    for (const fila of lista) {
      const q = await fs.collection(COLECCIONES[rel.modelo]).where(rel.fk, '==', fila.id).get()
      const regs = q.docs.map((d) => decode(rel.modelo, d))
      ordenar(regs, [[rel.ordenPor, 'desc']])
      fila[campo] = regs
    }
  }
}

function crearModelo(modelo: string) {
  return {
    async findMany({ where, orderBy, include, select }: Where = {}): Promise<Fila[]> {
      void select
      const fs = firestore()
      const docs = await fs.collection(COLECCIONES[modelo]).get()
      let lista = docs.docs.map((d) => decode(modelo, d))
      lista = lista.filter((f) => cumple(f, where))
      ordenar(lista, orderBy)
      await conRelaciones(fs, modelo, lista, include as Where | undefined)
      return lista
    },

    async findUnique({ where, include, select }: Where = {}): Promise<Fila | null> {
      void select
      const fs = firestore()
      const snap = await buscarDoc(fs, modelo, where)
      if (!snap) return null
      const lista = [decode(modelo, snap)]
      await conRelaciones(fs, modelo, lista, include as Where | undefined)
      return lista[0]
    },

    async create({ data }: Where): Promise<Fila> {
      const fs = firestore()
      const id = await nextId(fs, modelo)
      const ahora = new Date().toISOString()
      const cuerpo = {
        ...encode(modelo, data as Where),
        createdAt: ahora,
        ...(TIENE_UPDATED_AT.has(modelo) ? { updatedAt: ahora } : {}),
      }
      const ref = fs.collection(COLECCIONES[modelo]).doc(String(id))
      await ref.set(cuerpo)
      return decode(modelo, (await ref.get()) as QueryDocumentSnapshot)
    },

    async update({ where, data }: Where): Promise<Fila> {
      const fs = firestore()
      const snap = await buscarDoc(fs, modelo, where)
      if (!snap) throw new Error(`Registro no encontrado en ${modelo}`)
      const patch = {
        ...encode(modelo, data as Where),
        ...(TIENE_UPDATED_AT.has(modelo) ? { updatedAt: new Date().toISOString() } : {}),
      }
      await snap.ref.set(patch, { merge: true })
      return decode(modelo, (await snap.ref.get()) as QueryDocumentSnapshot)
    },

    async delete({ where }: Where): Promise<Fila> {
      const fs = firestore()
      const snap = await buscarDoc(fs, modelo, where)
      if (!snap) throw new Error(`Registro no encontrado en ${modelo}`)
      const fila = decode(modelo, snap)
      await snap.ref.delete()
      return fila
    },

    async upsert({ where, create, update }: Where): Promise<Fila> {
      const fs = firestore()
      const snap = await buscarDoc(fs, modelo, where)
      const ahora = new Date().toISOString()
      if (snap) {
        const patch = {
          ...encode(modelo, update as Where),
          ...(TIENE_UPDATED_AT.has(modelo) ? { updatedAt: ahora } : {}),
        }
        await snap.ref.set(patch, { merge: true })
        return decode(modelo, (await snap.ref.get()) as QueryDocumentSnapshot)
      }
      const id = await nextId(fs, modelo)
      const cuerpo = {
        ...encode(modelo, create as Where),
        createdAt: ahora,
        ...(TIENE_UPDATED_AT.has(modelo) ? { updatedAt: ahora } : {}),
      }
      const ref = fs.collection(COLECCIONES[modelo]).doc(String(id))
      await ref.set(cuerpo)
      return decode(modelo, (await ref.get()) as QueryDocumentSnapshot)
    },
  }
}

// ---------------- ensamblaje ----------------

let prismaCliente: PrismaClient | null = null

function clientePrisma(): PrismaClient {
  if (!prismaCliente) {
    const globalForPrisma = globalThis as unknown as { prisma: PrismaClient | undefined }
    prismaCliente = globalForPrisma.prisma ?? new PrismaClient({ log: ['query'] })
    if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prismaCliente
  }
  return prismaCliente
}

const dbSalida: Record<string, unknown> = {}
for (const nombre of Object.keys(COLECCIONES)) {
  dbSalida[nombre] = MODO === 'firestore' ? crearModelo(nombre) : clientePrisma()[nombre as keyof PrismaClient]
}

export const db = dbSalida as unknown as PrismaClient
