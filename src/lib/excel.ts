// Servicio Excel — llena las PLANTILLAS OFICIALES del IPD preservando diseño,
// celdas combinadas, bordes y configuración de página. Solo escribe celdas de datos.
import ExcelJS from 'exceljs'
import path from 'path'
import fs from 'fs'
import sharp from 'sharp'
import type { AnalisisRend } from './rendimiento'
import { infoQuincena, cumpleEnQuincena, MESES_ES, rangoPeriodo, fmtFecha, marcaTexto, nombreCompleto, type TipoPeriodo } from './periodos'

const plantilla = (nombre: string) => path.join(process.cwd(), 'templates', nombre)

async function abrir(archivo: string): Promise<ExcelJS.Workbook> {
  const wb = new ExcelJS.Workbook()
  await wb.xlsx.load(fs.readFileSync(archivo))
  return wb
}

async function buffer(wb: ExcelJS.Workbook): Promise<Buffer> {
  const ab = await wb.xlsx.writeBuffer()
  return Buffer.from(ab as ArrayBuffer)
}

type Celda = string | number | Date | null

// Celdas esclavas de rangos combinados: NUNCA se les escribe (borraría el valor del maestro)
const cacheEsclavas = new WeakMap<ExcelJS.Worksheet, Set<string>>()

function dirAFilaCol(dir: string): { fila: number; col: number } {
  const m = /^([A-Z]+)(\d+)$/.exec(dir.trim())
  if (!m) return { fila: NaN, col: NaN }
  let col = 0
  for (const ch of m[1]) col = col * 26 + (ch.charCodeAt(0) - 64)
  return { fila: parseInt(m[2]), col }
}

function esclavasDe(ws: ExcelJS.Worksheet): Set<string> {
  let s = cacheEsclavas.get(ws)
  if (s) return s
  s = new Set<string>()
  for (const m of (ws.model.merges as unknown[]) ?? []) {
    if (typeof m !== 'string' || !m.includes(':')) continue
    const [a, b] = m.split(':')
    const p1 = dirAFilaCol(a), p2 = dirAFilaCol(b)
    if (Number.isNaN(p1.fila) || Number.isNaN(p2.fila)) continue
    for (let r = p1.fila; r <= p2.fila; r++) {
      for (let c = p1.col; c <= p2.col; c++) {
        if (r === p1.fila && c === p1.col) continue // el maestro sí se escribe
        s.add(`${ws.getColumn(c).letter}${r}`)
      }
    }
  }
  cacheEsclavas.set(ws, s)
  return s
}

function p(ws: ExcelJS.Worksheet, dir: string, valor: Celda, multilinea = false) {
  if (esclavasDe(ws).has(dir)) return
  const c = ws.getCell(dir)
  c.value = valor as ExcelJS.CellValue
  if (multilinea) c.alignment = { wrapText: true, vertical: 'top', horizontal: 'left' }
}

/** dirección "B24" construida manualmente (independiente del build de exceljs) */
function dirDe(ws: ExcelJS.Worksheet, fila: number, col: number): string {
  return `${ws.getColumn(col).letter}${fila}`
}

/** Ajuste de impresión para que el PDF no recorte el borde derecho (no altera el diseño) */
function prepararImpresion(ws: ExcelJS.Worksheet, horizontal = false) {
  ws.pageSetup = {
    orientation: horizontal ? 'landscape' : 'portrait', fitToPage: true, fitToWidth: 1, fitToHeight: 0,
    paperSize: 9, horizontalCentered: true,
    margins: { left: 0.3, right: 0.3, top: 0.4, bottom: 0.4, header: 0.2, footer: 0.2 },
  }
}

/** Escribe filas de datos desde primeraFila; borra valores de filas plantilla sobrantes. Omite celdas esclavas de merges. */
function escribirFilas(ws: ExcelJS.Worksheet, primeraFila: number, ultimaFila: number, colIni: number, colFin: number, filas: Celda[][]) {
  const total = ultimaFila - primeraFila + 1
  const escl = esclavasDe(ws)
  for (let i = 0; i < Math.max(total, filas.length); i++) {
    const r = ws.getRow(primeraFila + i)
    const datos = filas[i] ?? []
    for (let c = colIni; c <= colFin; c++) {
      if (escl.has(dirDe(ws, primeraFila + i, c))) continue
      const cell = r.getCell(c)
      cell.value = (datos[c - colIni] ?? null) as ExcelJS.CellValue
    }
  }
}

// ============================================================
// SEGURO — LISTA DE DEPORTISTAS DEL CAR CUSCO - SEGURO
// ============================================================
export async function exportSeguro(deps: { [k: string]: unknown }[], refMes: string): Promise<Buffer> {
  const wb = await abrir(plantilla('PLANTILLA SEGURO.xlsx'))
  const ws = wb.getWorksheet('Hoja1')!
  prepararImpresion(ws, true)
  const [y, m] = refMes.split('-')
  const mes = MESES_ES[parseInt(m) - 1]
  p(ws, 'A1', `LISTA DE DEPORTISTAS DEL CAR CUSCO - SEGURO- ${mes} -${y}`)
  const filas: Celda[][] = deps.map((d, i) => {
    const pad = d.pad ? 'SI' : 'NO'
    const tel = d.telefono ? String(d.telefono) : null
    const telV = tel && /^\d+$/.test(tel) ? Number(tel) : tel
    return [
      i + 1, d.apellidoPaterno, d.apellidoMaterno, d.nombres,
      /^\d+$/.test(String(d.dni)) ? Number(d.dni) : String(d.dni),
      d.sexo, d.fechaIngreso ? new Date(String(d.fechaIngreso)) : null, d.deporte,
      new Date(String(d.fechaNacimiento)), d.nivelTecnico, d.modalidad, telV,
      d.procedencia, d.categoria, pad,
    ]
  })
  escribirFilas(ws, 3, 20, 1, 15, filas)
  return buffer(wb)
}

// ============================================================
// ALIMENTACIÓN — PROGRAMACIÓN DEL SERVICIO POR QUINCENA
// ============================================================
export async function exportAlimentacion(
  deps: { [k: string]: unknown }[],
  registros: Map<number, { incluido: boolean; observaciones: string | null }>,
  periodo: string,
): Promise<Buffer> {
  const wb = await abrir(plantilla('PLANTILLA ALIMENTACION.xlsx'))
  const q = infoQuincena(periodo)
  const ws = wb.getWorksheet('ALIMENTACION NOVIEMBRE') ?? wb.worksheets[0]
  ws.name = `ALIMENTACION ${MESES_ES[q.mes - 1]}`
  prepararImpresion(ws, true)
  p(ws, 'B2', `LISTA DE DEPORTISTAS CAR CUSCO QUE PARA LA PROGRAMACIÓN DEL SERVICIO DE ALIMENTACIÓN ${q.etiqueta}`)
  p(ws, 'H4', q.etiquetaCorta)
  // Nota: la columna G (CUMPLEAÑOS) viene combinada G5:G22 en la plantilla oficial y se mantiene
  // tal cual (vacía); los cumpleaños de la quincena se indican en OBSERVACIONES.
  const filas: Celda[][] = deps.map((d, i) => {
    const reg = registros.get(Number(d.id))
    const nac = new Date(String(d.fechaNacimiento))
    const cumple = cumpleEnQuincena(nac, q) ? `CUMPLEAÑOS ${fmtFecha(nac)}` : null
    return [
      i + 1, 'CUSCO', d.apellidoPaterno, d.apellidoMaterno, d.nombres,
      null, reg && !reg.incluido ? 'No' : 'Sí', cumple ?? reg?.observaciones ?? null,
    ]
  })
  escribirFilas(ws, 5, 22, 2, 9, filas)
  return buffer(wb)
}

// ============================================================
// AT-F3 — INFORME TÉCNICO MENSUAL DEL DEPORTISTA
// ============================================================
export type DatosF3 = {
  objetivos?: string | null; horario?: { manana: string[]; tarde: string[]; noche: string[] } | null
  asistencia?: number | null; cumplimiento?: number | null; testControles?: string | null
  detallePreparacion?: string | null; competencias?: string | null; cumplimientoObjetivos?: string | null
  evaluacionGeneral?: string | null; observaciones?: string | null
}

export async function exportF3(dep: { [k: string]: unknown }, datos: DatosF3, refMes: string, firmaImagen?: string | null): Promise<Buffer> {
  const wb = await abrir(plantilla('PLANTILLA FORMATO AT-F3.xlsx'))
  const ws = wb.getWorksheet('Hoja1')!
  prepararImpresion(ws)
  const [y, m] = refMes.split('-')
  const hor = datos.horario ?? { manana: ['', '', '', '', '', '', ''], tarde: ['', '', '', '', '', '', ''], noche: ['', '', '', '', '', '', ''] }
  p(ws, 'D8', nombreCompleto(dep as never))
  p(ws, 'J8', 'CUSCO')
  p(ws, 'D9', String(dep.deporte ?? ''))
  p(ws, 'J9', Number(y))
  p(ws, 'D10', MESES_ES[parseInt(m) - 1])
  p(ws, 'D11', String(dep.entrenador ?? ''))
  p(ws, 'B14', datos.objetivos ?? '', true)
  // horario (D..J = lunes..domingo)
  const dias = ['D', 'E', 'F', 'G', 'H', 'I', 'J']
  dias.forEach((col, i) => {
    p(ws, `${col}19`, hor.manana?.[i] ?? '')
    p(ws, `${col}20`, hor.tarde?.[i] ?? '')
    p(ws, `${col}21`, hor.noche?.[i] ?? '')
  })
  p(ws, 'B24', datos.asistencia != null ? `${datos.asistencia} %` : '', true)
  p(ws, 'B28', datos.cumplimiento != null ? `${datos.cumplimiento} %` : '', true)
  p(ws, 'B32', datos.testControles ?? '', true)
  p(ws, 'B36', datos.detallePreparacion ?? '', true)
  p(ws, 'B40', datos.competencias ?? '', true)
  p(ws, 'B46', datos.cumplimientoObjetivos ?? '', true)
  p(ws, 'B51', datos.evaluacionGeneral ?? '', true)
  const notaOficial = '*EN EL CASO QUE EL DEPORTISTA NO CUMPLA CON LOS PORCENTAJES DE ASISTENCIA Y DE PREPRACION, INDICAR LOS MOTIVOS.'
  const obs = datos.observaciones ? `\n${datos.observaciones}` : ''
  p(ws, 'B57', `${notaOficial}${obs}`, true)
  ponerFirma(ws, await cargarFirma(wb, firmaImagen), 3.4, 62.9) // zona de firma D66 (FIRMA DEL ENTRENADOR O JUT)
  return buffer(wb)
}

// ============================================================
// AT-F1 — INFORME MENSUAL CONSOLIDADO CAR
// ============================================================
export type DatosF1 = {
  matriculas: { cat: string; retiros: number; ingresos: number; damas: number; varones: number; total: number; sesiones: number; manana: string; tarde: string }[]
  filas: { deportistaId: number; nombre: string; deporte: string; nivel: string; asistencia: number | null; cumplimiento: number | null; observaciones: string | null }[]
  textos: { valoracionTecnica?: string; dificultades?: string; valoracionMedica?: string; profilactico?: string; balanceNutricional?: string; funcionamientoCar?: string; aspectosCar?: string; otrosAspectos?: string }
}

export async function exportF1(datos: DatosF1, refMes: string, firmaJUT?: string | null, firmaEntrenador?: string | null): Promise<Buffer> {
  const wb = await abrir(plantilla('PLANTILLA FORMATO AT-F1 CAR.xlsx'))
  const ws = wb.getWorksheet('Hoja1')!
  prepararImpresion(ws, true)
  const [y, m] = refMes.split('-')
  p(ws, 'C8', MESES_ES[parseInt(m) - 1])
  p(ws, 'E8', Number(y))
  // I. matrículas (filas 13-17): solo columnas C..J (A/B son la etiqueta de categoría, combinadas)
  const filasMat: Celda[][] = datos.matriculas.map((x) => [x.retiros, x.ingresos, x.damas, x.varones, x.total, x.sesiones, x.manana, x.tarde])
  escribirFilas(ws, 13, 17, 3, 10, filasMat)
  const t = datos.matriculas.reduce((a, x) => ({ retiros: a.retiros + x.retiros, ingresos: a.ingresos + x.ingresos, damas: a.damas + x.damas, varones: a.varones + x.varones, total: a.total + x.total }), { retiros: 0, ingresos: 0, damas: 0, varones: 0, total: 0 })
  p(ws, 'C18', t.retiros); p(ws, 'D18', t.ingresos); p(ws, 'E18', t.damas); p(ws, 'F18', t.varones); p(ws, 'G18', t.total)
  // II.I filas por deportista (plantilla 24-42; espacio fijo 19)
  const filasDep: Celda[][] = datos.filas.map((x, i) => [
    i + 1, x.nombre, null, null, null, x.deporte, x.nivel,
    x.asistencia != null ? Math.round(x.asistencia) / 100 : null,
    x.cumplimiento != null ? Math.round(x.cumplimiento) / 100 : null,
    x.observaciones ?? '',
  ])
  const primera = 24, ultima = 42, max = ultima - primera + 1
  const escl = esclavasDe(ws)
  for (let i = 0; i < Math.max(max, filasDep.length); i++) {
    const r = ws.getRow(primera + i)
    const d = filasDep[i]
    const valores: Celda[] = d ?? [null, null, null, null, null, null, null, null, null, null]
    for (let c = 1; c <= 10; c++) {
      if (escl.has(dirDe(ws, primera + i, c))) continue
      r.getCell(c).value = (valores[c - 1] ?? null) as ExcelJS.CellValue
    }
    const h = r.getCell(8), i2 = r.getCell(9)
    if (typeof h.value === 'number') h.numFmt = '0.0%'
    if (typeof i2.value === 'number') i2.numFmt = '0.0%'
  }
  // textos de secciones
  const tx = datos.textos
  p(ws, 'A45', tx.valoracionTecnica ?? '', true)
  p(ws, 'A48', tx.dificultades ?? '', true)
  p(ws, 'A51', tx.valoracionMedica ?? '', true)
  p(ws, 'A54', tx.profilactico ?? '', true)
  p(ws, 'A58', tx.balanceNutricional ?? '', true)
  p(ws, 'A61', tx.funcionamientoCar ?? '', true)
  p(ws, 'A64', tx.aspectosCar ?? '', true)
  p(ws, 'A66', tx.otrosAspectos ?? '', true)
  ponerFirma(ws, await cargarFirma(wb, firmaJUT), 1.5, 66.9) // zona B67-B68 (JEFE DE UNIDAD TECNICA / DINADAF)
  ponerFirma(ws, await cargarFirma(wb, firmaEntrenador), 8.7, 66.9) // zona derecha (ENTRENADOR)
  return buffer(wb)
}

// ============================================================
// AT-F8 — PLAN DE TRABAJO MENSUAL DEL JUT
// ============================================================
export type DatosF8 = { federacion: string; jefe: string; actividades: { actividad: string; fecha: string; hora: string; lugar: string; observaciones: string }[] }

export async function exportF8(datos: DatosF8, refMes: string): Promise<Buffer> {
  const wb = await abrir(plantilla('PLANTILLA FORMATO ATF8.xlsx'))
  const ws = wb.getWorksheet('Hoja3')!
  prepararImpresion(ws)
  const [y, m] = refMes.split('-')
  p(ws, 'A7', `FEDERACION: ${datos.federacion || 'FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO'}`)
  p(ws, 'A8', `NOMBRES Y APELLIDOS: ${datos.jefe ?? ''}`)
  p(ws, 'A9', `MES: ${MESES_ES[parseInt(m) - 1]}                    AÑO: ${y}`)
  const filas: Celda[][] = datos.actividades.map((a, i) => [i + 1, a.actividad, a.fecha, a.hora, a.lugar, a.observaciones])
  escribirFilas(ws, 12, 25, 1, 6, filas)
  return buffer(wb)
}

// ============================================================
// AT-F9 — INFORME DE CUMPLIMIENTO DEL JUT (MES ANTERIOR)
// ============================================================
export type DatosF9 = {
  jefe?: string | null; planificadas?: number | null; cumplidas?: number | null
  evaluacionCumplimiento?: string | null; cumplimientoPreparacion?: number | null
  asistenciaPromedio?: number | null; dificultades?: string | null; resenaRevision?: string | null
  visitas?: number | null; evaluacionVisitas?: string | null; resumenDificultades?: string | null
  baseDatos?: boolean | null; calendario?: boolean | null; capacitaciones?: boolean | null
  analisisObjetivos?: string | null; otrosInteres?: string | null; calificacion?: string | null
}

export async function exportF9(datos: DatosF9, refMes: string, firmaImagen?: string | null): Promise<Buffer> {
  const wb = await abrir(plantilla('PLANTILLA FORMATO AT -F9.xlsx'))
  const ws = wb.getWorksheet('Hoja1')!
  prepararImpresion(ws)
  const [y, m] = refMes.split('-')
  p(ws, 'D7', datos.jefe ?? '')
  p(ws, 'H9', MESES_ES[parseInt(m) - 1])
  p(ws, 'J9', Number(y))
  const planif = datos.planificadas ?? 0, cumpl = datos.cumplidas ?? 0
  const pct = planif > 0 ? Math.round((cumpl / planif) * 100) : 0
  p(ws, 'D12', planif); p(ws, 'F12', cumpl); p(ws, 'H12', pct)
  p(ws, 'B14', `EVALUACION DEL CUMPLIMIENTO: ${datos.evaluacionCumplimiento ?? ''}`, true)
  p(ws, 'G17', datos.cumplimientoPreparacion != null ? `${datos.cumplimientoPreparacion} %` : '')
  p(ws, 'G18', datos.asistenciaPromedio != null ? `${datos.asistenciaPromedio} %` : '')
  p(ws, 'B20', datos.dificultades ?? '', true)
  p(ws, 'B23', datos.resenaRevision ?? '', true)
  p(ws, 'D26', datos.visitas ?? null)
  p(ws, 'D27', datos.evaluacionVisitas ?? '')
  p(ws, 'B30', datos.resumenDificultades ?? '', true)
  const sn = (v?: boolean | null) => (v ? 'SÍ' : 'NO')
  p(ws, 'F33', sn(datos.baseDatos))
  p(ws, 'F34', sn(datos.calendario))
  p(ws, 'F35', sn(datos.capacitaciones))
  p(ws, 'B38', datos.analisisObjetivos ?? '', true)
  p(ws, 'B42', datos.otrosInteres ?? '', true)
  ;['BUENO', 'REGULAR', 'MALO'].forEach((cal, i) => {
    p(ws, `C${48 + i}`, datos.calificacion === cal ? 'X' : null)
  })
  ponerFirma(ws, await cargarFirma(wb, firmaImagen), 3.4, 52.9) // zona de firma D56 (JEFE DE UNIDAD TECNICA)
  return buffer(wb)
}

// ============================================================
// ESTILO COMÚN para libros nuevos (Análisis / Ficha 360)
// ============================================================
const ROJO = 'FFC8102E'
const GRIS = 'FFF3F4F6'

function tituloHoja(ws: ExcelJS.Worksheet, texto: string, colFin: number) {
  ws.mergeCells(1, 1, 1, colFin)
  const c = ws.getCell(1, 1)
  c.value = texto
  c.font = { bold: true, size: 12, color: { argb: ROJO } }
  c.alignment = { horizontal: 'left' }
}

function encabezadoTabla(ws: ExcelJS.Worksheet, fila: number, cols: string[]) {
  cols.forEach((t, i) => {
    const c = ws.getCell(fila, i + 1)
    c.value = t
    c.font = { bold: true, color: { argb: 'FFFFFFFF' }, size: 10 }
    c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: ROJO } }
    c.alignment = { wrapText: true, vertical: 'middle', horizontal: 'center' }
    c.border = { top: { style: 'thin' }, left: { style: 'thin' }, bottom: { style: 'thin' }, right: { style: 'thin' } }
  })
}

function filaTabla(ws: ExcelJS.Worksheet, fila: number, valores: Celda[], zebra: boolean) {
  valores.forEach((v, i) => {
    const c = ws.getCell(fila, i + 1)
    c.value = (v ?? null) as ExcelJS.CellValue
    c.font = { size: 10 }
    c.border = { top: { style: 'thin' }, left: { style: 'thin' }, bottom: { style: 'thin' }, right: { style: 'thin' } }
    if (zebra) c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: GRIS } }
  })
}

function anchos(ws: ExcelJS.Worksheet, w: number[]) {
  w.forEach((x, i) => { ws.getColumn(i + 1).width = x })
}

// ============================================================
// FIRMAS — incrusta la imagen de firma subida en la zona de firmas de la plantilla
// ============================================================
export type FirmaImg = { id: number; w: number; h: number }

async function cargarFirma(wb: ExcelJS.Workbook, imagen: string | null | undefined): Promise<FirmaImg | null> {
  if (!imagen || !imagen.startsWith('data:image/')) return null
  try {
    const base64 = imagen.includes(',') ? imagen.split(',')[1] : imagen
    const extension = imagen.startsWith('data:image/png') ? 'png' : 'jpeg'
    const meta = await sharp(Buffer.from(base64, 'base64')).metadata()
    const h = 38
    const proporcion = (meta.width ?? 1) / (meta.height ?? 1)
    const w = Math.min(150, Math.max(55, Math.round(proporcion * h)))
    const id = wb.addImage({ base64, extension })
    return { id, w, h }
  } catch { return null }
}

function ponerFirma(ws: ExcelJS.Worksheet, f: FirmaImg | null, col: number, fila: number) {
  if (!f) return
  ws.addImage(f.id, { tl: { col, row: fila }, ext: { width: f.w, height: f.h } })
}

function pagina(ws: ExcelJS.Worksheet, horizontal = true) {
  ws.pageSetup = { orientation: horizontal ? 'landscape' : 'portrait', fitToPage: true, fitToWidth: 1, fitToHeight: 0, paperSize: 9, margins: { left: 0.4, right: 0.4, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 } }
}

// ============================================================
// ANÁLISIS DEPORTIVO — libro multi-hoja
// ============================================================
export type MejorMarca = { deportistaId: number; nombre: string; categoria: string; sexo: string; prueba: string; marca: string; marcaValor: number; unidad: string; fecha: string; competencia: string; mejora: number | null }
export type Agregados = {
  etiqueta: string; tipo: string; ref: string
  totalDeportistas: number; activos: number; pad: number; ingresos: number; resultados: number
  porCategoria: { clave: string; total: number }[]; porSexo: { clave: string; total: number }[]
  porDeporte: { clave: string; total: number }[]; porModalidad: { clave: string; total: number }[]
  resultadosPorMes: { mes: string; total: number }[]
  mejores: MejorMarca[]
  detalle?: { fecha: string; nombre: string; categoria: string; prueba: string; marca: string; puesto: number | null; competencia: string; nivel: string | null }[]
}

export async function exportAnalisis(ag: Agregados): Promise<Buffer> {
  const wb = new ExcelJS.Workbook()
  // --- RESUMEN ---
  const r1 = wb.addWorksheet('RESUMEN')
  tituloHoja(r1, `ANÁLISIS DEPORTIVO — CAR CUSCO — ${ag.etiqueta}`, 3)
  const kpis: [string, Celda][] = [
    ['Periodo analizado', ag.etiqueta], ['Tipo de periodo', ag.tipo],
    ['Total de deportistas registrados', ag.totalDeportistas], ['Deportistas activos', ag.activos],
    ['Con seguro PAD', ag.pad], ['Nuevos ingresos en el periodo', ag.ingresos],
    ['Registros de resultados en el periodo', ag.resultados],
  ]
  kpis.forEach((k, i) => {
    r1.getCell(i + 3, 1).value = k[0]; r1.getCell(i + 3, 1).font = { bold: true, size: 10 }
    r1.getCell(i + 3, 2).value = k[1] as ExcelJS.CellValue
  })
  anchos(r1, [40, 26, 14]); pagina(r1, false)
  filaCategoria(r1, ag, 12, 'POR CATEGORÍA', ag.porCategoria)
  filaCategoria(r1, ag, 12 + ag.porCategoria.length + 2, 'POR SEXO', ag.porSexo)
  filaCategoria(r1, ag, 12 + ag.porCategoria.length + ag.porSexo.length + 4, 'POR DEPORTE', ag.porDeporte)

  // --- MEJORES MARCAS ---
  const r2 = wb.addWorksheet('MEJORES MARCAS')
  tituloHoja(r2, `MEJORES MARCAS DEL PERIODO — ${ag.etiqueta}`, 8)
  encabezadoTabla(r2, 3, ['N°', 'APELLIDOS Y NOMBRES', 'CATEG.', 'SEXO', 'PRUEBA', 'MEJOR MARCA', 'FECHA', 'COMPETENCIA', 'MEJORA %'])
  ag.mejores.forEach((x, i) => {
    filaTabla(r2, 4 + i, [i + 1, x.nombre, x.categoria, x.sexo, x.prueba, x.marca, fmtFecha(x.fecha), x.competencia, x.mejora != null ? x.mejora.toFixed(1) : '—'], i % 2 === 1)
  })
  anchos(r2, [5, 34, 8, 11, 20, 13, 12, 26, 10]); pagina(r2)

  // --- RESULTADOS POR MES ---
  const r3 = wb.addWorksheet('RESULTADOS POR MES')
  tituloHoja(r3, `REGISTROS DE RESULTADOS POR MES — ${ag.etiqueta}`, 2)
  encabezadoTabla(r3, 3, ['MES', 'N° DE RESULTADOS REGISTRADOS'])
  ag.resultadosPorMes.forEach((x, i) => filaTabla(r3, 4 + i, [x.mes, x.total], i % 2 === 1))
  anchos(r3, [16, 30]); pagina(r3, false)

  // --- RESULTADOS DETALLE ---
  if (ag.detalle && ag.detalle.length) {
    const r4 = wb.addWorksheet('RESULTADOS')
    tituloHoja(r4, `RESULTADOS DEL PERIODO — ${ag.etiqueta}`, 7)
    encabezadoTabla(r4, 3, ['FECHA', 'DEPORTISTA', 'CATEG.', 'PRUEBA', 'MARCA', 'PUESTO', 'COMPETENCIA', 'NIVEL'])
    ag.detalle.forEach((x: { [k: string]: unknown }, i: number) => {
      filaTabla(r4, 4 + i, [fmtFecha(String(x.fecha)), String(x.nombre), String(x.categoria), String(x.prueba), String(x.marca), (x.puesto as number) ?? '', String(x.competencia), String(x.nivel ?? '')], i % 2 === 1)
    })
    anchos(r4, [12, 34, 8, 20, 12, 8, 26, 16]); pagina(r4)
  }
  return buffer(wb)
}

function filaCategoria(ws: ExcelJS.Worksheet, ag: Agregados, fila: number, titulo: string, datos: { clave: string; total: number }[]) {
  ws.getCell(fila, 1).value = titulo
  ws.getCell(fila, 1).font = { bold: true, size: 11, color: { argb: ROJO } }
  encabezadoTabla(ws, fila + 1, [titulo === 'POR CATEGORÍA' ? 'CATEGORÍA' : titulo === 'POR SEXO' ? 'SEXO' : 'DEPORTE', 'N° DE DEPORTISTAS', '%'])
  datos.forEach((x, i) => {
    const pct = ag.activos > 0 ? ((x.total / ag.activos) * 100).toFixed(1) : '0'
    filaTabla(ws, fila + 2 + i, [x.clave, x.total, `${pct} %`], i % 2 === 1)
  })
}

// ============================================================
// FICHA 360 DEL DEPORTISTA — Excel
// ============================================================
export type FichaData = {
  dep: { [k: string]: unknown }
  resultados: { fecha: string; competencia: string; prueba: string; marca: string; puesto: number | null; sede: string | null; nivel: string | null }[]
  mejores: { etiqueta: string; marca: string; fecha: string; competencia: string }[]
  edad: number
}

export async function exportFicha(f: FichaData): Promise<Buffer> {
  const wb = new ExcelJS.Workbook()
  const d = f.dep
  const ws = wb.addWorksheet('FICHA DEL DEPORTISTA')
  tituloHoja(ws, 'FICHA INTEGRAL DEL DEPORTISTA — CAR CUSCO (IPD · DINADAF)', 3)
  const campos: [string, Celda][] = [
    ['Apellidos y nombres', nombreCompleto(d as never)], ['DNI', String(d.dni)], ['Sexo', String(d.sexo)],
    ['Fecha de nacimiento', fmtFecha(String(d.fechaNacimiento))], ['Edad', f.edad], ['Categoría', String(d.categoria)],
    ['Deporte', String(d.deporte)], ['Prueba', String(d.prueba ?? '')], ['Nivel técnico', String(d.nivelTecnico)],
    ['Modalidad', String(d.modalidad)], ['Entrenador', String(d.entrenador ?? '')],
    ['Fecha de ingreso al CAR', fmtFecha(d.fechaIngreso ? String(d.fechaIngreso) : null)],
    ['Teléfono', d.telefono ? String(d.telefono) : '—'], ['Distrito/Provincia de procedencia', String(d.procedencia)],
    ['Seguro PAD', d.pad ? 'SI' : 'NO'], ['Estado', d.retirado ? 'RETIRADO' : 'ACTIVO'],
  ]
  campos.forEach((k, i) => {
    ws.getCell(i + 3, 1).value = k[0]; ws.getCell(i + 3, 1).font = { bold: true, size: 10 }
    ws.getCell(i + 3, 2).value = k[1] as ExcelJS.CellValue; ws.getCell(i + 3, 2).font = { size: 10 }
  })
  anchos(ws, [34, 40, 12]); pagina(ws, false)

  const ws2 = wb.addWorksheet('MEJORES MARCAS POR PERIODO')
  tituloHoja(ws2, 'MEJORES MARCAS POR PERIODO (MES · BIMESTRE · TRIMESTRE · AÑO)', 4)
  encabezadoTabla(ws2, 3, ['PERIODO', 'MEJOR MARCA', 'FECHA', 'COMPETENCIA'])
  f.mejores.forEach((x, i) => filaTabla(ws2, 4 + i, [x.etiqueta, x.marca, fmtFecha(x.fecha), x.competencia], i % 2 === 1))
  anchos(ws2, [22, 14, 12, 30]); pagina(ws2)

  const ws3 = wb.addWorksheet('RESULTADOS')
  tituloHoja(ws3, 'HISTORIAL DE RESULTADOS', 7)
  encabezadoTabla(ws3, 3, ['FECHA', 'COMPETENCIA', 'PRUEBA', 'MARCA', 'PUESTO', 'SEDE', 'NIVEL'])
  f.resultados.forEach((x, i) => filaTabla(ws3, 4 + i, [fmtFecha(x.fecha), x.competencia, x.prueba, marcaTextoTexto(x.marca, x.prueba), x.puesto ?? '', x.sede ?? '', x.nivel ?? ''], i % 2 === 1))
  anchos(ws3, [12, 28, 20, 12, 8, 26, 16]); pagina(ws3)
  return buffer(wb)
}

function marcaTextoTexto(marca: string, _prueba: string): string { return marca }

// ============================================================
// ANÁLISIS DE RENDIMIENTO POR DEPORTISTA Y PRUEBA — libro multi-hoja
// ============================================================
export async function exportRendimiento(r: AnalisisRend): Promise<Buffer> {
  const wb = new ExcelJS.Workbook()

  // --- HOJA 1: RESUMEN TÉCNICO ---
  const r1 = wb.addWorksheet('RESUMEN')
  tituloHoja(r1, `ANÁLISIS DE RENDIMIENTO — ${r.nombre} — ${r.prueba} — ${r.anio}`, 3)
  const kpis: [string, Celda][] = [
    ['Deportista', r.nombre], ['Categoría', r.categoria], ['Sexo', r.sexo],
    ['Prueba analizada', r.prueba], ['Unidad de medida', r.unidad === 'seg' ? 'SEGUNDOS (menor es mejor)' : 'METROS (mayor es mejor)'],
    ['Temporada analizada', `AÑO ${r.anio}`], ['Registros en el año', r.nAnio],
    ['Registros históricos de la prueba', r.nHistorico],
    ['Marca personal histórica (PB)', r.pb ? `${r.pb.marca}  (${fmtFecha(r.pb.fecha)}, ${r.pb.competencia})` : '—'],
    ['Mejor marca del año', r.mejorAnio ? `${r.mejorAnio.marca}  (${fmtFecha(r.mejorAnio.fecha)}, ${r.mejorAnio.competencia})` : '—'],
    ['Progreso sobre la primera marca del año', r.progreso != null ? `${r.progreso > 0 ? '+' : ''}${r.progreso} %` : '—'],
    ['Tendencia del año (regresión lineal)', `${r.tendencia}${r.pendiente != null ? ` (pendiente ${r.pendiente > 0 ? '+' : ''}${r.pendiente} ${r.unidad === 'seg' ? 's' : 'm'}/mes)` : ''}`],
    ['Consistencia técnica (CV de marcas)', r.cv != null ? `${r.consistencia} (CV ${r.cv} %)` : '—'],
    ['Mejor puesto del año', r.mejorPuestoAnio ?? '—'],
  ]
  kpis.forEach((k, i) => {
    r1.getCell(i + 3, 1).value = k[0]; r1.getCell(i + 3, 1).font = { bold: true, size: 10 }
    r1.getCell(i + 3, 2).value = k[1] as ExcelJS.CellValue; r1.getCell(i + 3, 2).font = { size: 10 }
  })
  const filaAnalisis = 3 + kpis.length + 1
  r1.getCell(filaAnalisis, 1).value = 'ANÁLISIS TÉCNICO DEL PERIODO'
  r1.getCell(filaAnalisis, 1).font = { bold: true, size: 11, color: { argb: ROJO } }
  r1.mergeCells(filaAnalisis + 1, 1, filaAnalisis + 1, 2)
  const ca = r1.getCell(filaAnalisis + 1, 1)
  ca.value = r.analisis
  ca.alignment = { wrapText: true, vertical: 'top' }
  ca.font = { size: 10 }
  r1.getRow(filaAnalisis + 1).height = 90
  anchos(r1, [42, 52, 12]); pagina(r1, false)

  // --- HOJA 2: SERIE MENSUAL DEL AÑO (variable a comparar) ---
  const r2 = wb.addWorksheet('SERIE MENSUAL')
  tituloHoja(r2, `SERIE MENSUAL ${r.anio} — ${r.prueba}`, 5)
  encabezadoTabla(r2, 3, ['MES', 'N° REGISTROS', 'MEJOR MARCA', 'PROMEDIO', 'MEJOR PUESTO'])
  r.meses.forEach((m, i) => {
    filaTabla(r2, 4 + i, [m.mesNombre, m.n, m.mejorMarca ?? '—', m.promedio != null ? m.promedio.toFixed(2) : '—', m.mejorPuesto ?? '—'], i % 2 === 1)
  })
  anchos(r2, [14, 13, 14, 12, 13]); pagina(r2, false)

  // --- HOJA 3: COMPARACIÓN INTERANUAL ---
  const r3 = wb.addWorksheet('COMPARACIÓN ANUAL')
  tituloHoja(r3, `MEJOR MARCA POR MES SEGÚN AÑO — ${r.prueba}`, 13)
  encabezadoTabla(r3, 3, ['AÑO', ...MESES_ES.map((m) => m.slice(0, 3)), 'MEJOR DEL AÑO'])
  r.porAnio.forEach((a, i) => {
    filaTabla(r3, 4 + i, [String(a.anio), ...a.valores.map((v) => v ?? '—'), a.mejorMarca ?? '—'], i % 2 === 1)
  })
  anchos(r3, [8, ...Array(12).fill(7), 13]); pagina(r3)

  // --- HOJA 4: REGISTROS DEL AÑO (con Δ% vs PB) ---
  const r4 = wb.addWorksheet('REGISTROS DEL AÑO')
  tituloHoja(r4, `REGISTROS ${r.anio} — ${r.prueba} — ${r.nombre}`, 8)
  encabezadoTabla(r4, 3, ['N°', 'FECHA', 'COMPETENCIA', 'SEDE', 'NIVEL', 'MARCA', 'PUESTO', 'Δ% vs PB'])
  r.registros.forEach((x, i) => {
    filaTabla(r4, 4 + i, [i + 1, fmtFecha(x.fecha), x.competencia, x.sede ?? '—', x.nivel ?? '—', x.marca, x.puesto ?? '—', x.deltaPb != null ? `${x.deltaPb > 0 ? '+' : ''}${x.deltaPb} %` : 'PB'], i % 2 === 1)
  })
  anchos(r4, [5, 12, 28, 22, 16, 10, 8, 11]); pagina(r4)

  // --- HOJA 5: HISTÓRICO COMPLETO DE LA PRUEBA ---
  const r5 = wb.addWorksheet('HISTÓRICO COMPLETO')
  tituloHoja(r5, `HISTÓRICO COMPLETO — ${r.prueba} — ${r.nombre}`, 7)
  encabezadoTabla(r5, 3, ['N°', 'AÑO', 'FECHA', 'COMPETENCIA', 'NIVEL', 'MARCA', 'PUESTO', 'Δ% vs PB'])
  r.historico.forEach((x, i) => {
    filaTabla(r5, 4 + i, [i + 1, x.fecha.slice(0, 4), fmtFecha(x.fecha), x.competencia, x.nivel ?? '—', x.marca, x.puesto ?? '—', x.deltaPb != null ? `${x.deltaPb > 0 ? '+' : ''}${x.deltaPb} %` : 'PB'], i % 2 === 1)
  })
  anchos(r5, [5, 7, 12, 28, 16, 10, 8, 11]); pagina(r5)

  return buffer(wb)
}

// reexportar para rutas
export { rangoPeriodo }
export type { TipoPeriodo }
