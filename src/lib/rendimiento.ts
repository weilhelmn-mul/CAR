// Análisis técnico de rendimiento deportivo (solo servidor)
// Serie mensual, comparación interanual, tendencia (regresión lineal),
// consistencia (CV) y progreso sobre la marca personal (PB).
import { db } from '@/lib/db'
import { MESES_ES, marcaTexto, nombreCompleto } from './periodos'

export type RegAnio = {
  id: number; fecha: string; competencia: string; sede: string | null; nivel: string | null
  marca: string; marcaValor: number; unidad: string; puesto: number | null; deltaPb: number | null
}
export type MesSerie = {
  mes: number; mesNombre: string; n: number
  mejorValor: number | null; mejorMarca: string | null
  promedio: number | null; mejorPuesto: number | null
}
export type AnioSerie = { anio: number; valores: (number | null)[]; mejorMarca: string | null }

const mejorDe = <T extends { marcaValor: number; unidad: string }>(lista: T[]): T | null => {
  if (!lista.length) return null
  return lista.reduce((m, r) => (r.unidad === 'seg' ? r.marcaValor < m.marcaValor : r.marcaValor > m.marcaValor) ? r : m)
}

export async function resumenRendimiento(depId: number) {
  const resultados = await db.resultado.findMany({ where: { deportistaId: depId }, orderBy: { fecha: 'asc' } })
  const pruebas = [...new Set(resultados.map((r) => r.prueba))].sort()
  const anios = [...new Set(resultados.map((r) => r.fecha.getUTCFullYear()))].sort((a, b) => b - a)
  return { pruebas, anios }
}

export async function analisisRendimiento(depId: number, prueba: string, anio: number) {
  const dep = await db.deportista.findUnique({ where: { id: depId } })
  if (!dep) throw new Error('Deportista no encontrado')
  const regs = await db.resultado.findMany({ where: { deportistaId: depId, prueba }, orderBy: { fecha: 'asc' } })
  if (!regs.length) throw new Error('No hay registros para esta prueba')

  const unidad = regs[0].unidad
  const pbReg = mejorDe(regs) // marca personal histórica
  const delAnio = regs.filter((r) => r.fecha.getUTCFullYear() === anio)
  const mejorAnio = mejorDe(delAnio)

  // --- serie mensual del año ---
  const meses: MesSerie[] = Array.from({ length: 12 }, (_, i) => {
    const delMes = delAnio.filter((r) => r.fecha.getUTCMonth() === i)
    const mejor = mejorDe(delMes)
    const promedio = delMes.length ? delMes.reduce((a, r) => a + r.marcaValor, 0) / delMes.length : null
    const puestos = delMes.map((r) => r.puesto).filter((p): p is number => !!p)
    return {
      mes: i + 1, mesNombre: MESES_ES[i], n: delMes.length,
      mejorValor: mejor ? Math.round(mejor.marcaValor * 100) / 100 : null,
      mejorMarca: mejor ? marcaTexto(mejor.marcaValor, unidad) : null,
      promedio: promedio != null ? Math.round(promedio * 100) / 100 : null,
      mejorPuesto: puestos.length ? Math.min(...puestos) : null,
    }
  })

  // --- comparación interanual: mejor marca de cada mes por año ---
  const anios = [...new Set(regs.map((r) => r.fecha.getUTCFullYear()))].sort((a, b) => a - b)
  const porAnio: AnioSerie[] = anios.map((a) => {
    const delA = regs.filter((r) => r.fecha.getUTCFullYear() === a)
    return {
      anio: a,
      valores: Array.from({ length: 12 }, (_, i) => {
        const mejor = mejorDe(delA.filter((r) => r.fecha.getUTCMonth() === i))
        return mejor ? Math.round(mejor.marcaValor * 100) / 100 : null
      }),
      mejorMarca: (() => { const m = mejorDe(delA); return m ? marcaTexto(m.marcaValor, unidad) : null })(),
    }
  })

  // --- KPIs técnicos del año ---
  const primero = delAnio[0] ?? null
  const progreso = primero && mejorAnio && primero.marcaValor > 0
    ? Math.round(
      (unidad === 'seg'
        ? ((primero.marcaValor - mejorAnio.marcaValor) / primero.marcaValor) * 100
        : ((mejorAnio.marcaValor - primero.marcaValor) / primero.marcaValor) * 100) * 10,
    ) / 10
    : null

  // tendencia: regresión lineal mínimos cuadrados (x = mes decimal, y = marca)
  const puntos = delAnio.map((r) => ({ x: r.fecha.getUTCMonth() + (r.fecha.getUTCDate() - 1) / 31, y: r.marcaValor }))
  let pendiente: number | null = null
  if (puntos.length >= 2) {
    const n = puntos.length
    const sx = puntos.reduce((a, p) => a + p.x, 0), sy = puntos.reduce((a, p) => a + p.y, 0)
    const sxy = puntos.reduce((a, p) => a + p.x * p.y, 0), sxx = puntos.reduce((a, p) => a + p.x * p.x, 0)
    const den = n * sxx - sx * sx
    if (den !== 0) pendiente = Math.round(((n * sxy - sx * sy) / den) * 10000) / 10000
  }
  const umbral = unidad === 'seg' ? 0.005 : 0.01 // s/mes o m/mes
  const tendencia = pendiente == null ? 'SIN DATOS SUFICIENTES'
    : Math.abs(pendiente) < umbral ? 'ESTABLE'
      : (unidad === 'seg' ? pendiente < 0 : pendiente > 0) ? 'MEJORA' : 'RETROCESO'

  // consistencia: coeficiente de variación de las marcas del año
  const vals = delAnio.map((r) => r.marcaValor)
  const cv = vals.length >= 2 ? (() => {
    const m = vals.reduce((a, b) => a + b, 0) / vals.length
    const sd = Math.sqrt(vals.reduce((a, b) => a + (b - m) ** 2, 0) / vals.length)
    return Math.round((sd / m) * 1000) / 10
  })() : null
  const consistencia = cv == null ? 'SIN DATOS' : cv <= 2 ? 'ALTA' : cv <= 5 ? 'MEDIA' : 'VARIABLE'

  const puestosAnio = delAnio.map((r) => r.puesto).filter((p): p is number => !!p)

  // --- registros con Δ% respecto a la PB ---
  const aRegistro = (r: (typeof regs)[0]): RegAnio => ({
    id: r.id, fecha: r.fecha.toISOString(), competencia: r.competencia, sede: r.sede, nivel: r.nivel,
    marca: r.marca, marcaValor: r.marcaValor, unidad, puesto: r.puesto,
    deltaPb: pbReg && pbReg.marcaValor > 0
      ? Math.round(
        (unidad === 'seg'
          ? ((r.marcaValor - pbReg.marcaValor) / pbReg.marcaValor) * 100
          : ((pbReg.marcaValor - r.marcaValor) / pbReg.marcaValor) * 100) * 10,
      ) / 10
      : null,
  })
  const registros: RegAnio[] = delAnio.map(aRegistro)
  const historico: RegAnio[] = regs.map(aRegistro) // todos los registros de la prueba (todas las temporadas)

  // --- texto de análisis técnico (determinístico, para el informe y el Excel) ---
  const um = unidad === 'seg' ? 's' : 'm'
  const firmaTend = pendiente != null ? `${pendiente > 0 ? '+' : ''}${pendiente} ${um}/mes` : '—'
  const partes: string[] = []
  partes.push(
    delAnio.length
      ? `Durante ${anio}, ${nombreCompleto(dep)} (${dep.categoria}) registró ${delAnio.length} marca${delAnio.length === 1 ? '' : 's'} en ${prueba}.`
      : `Durante ${anio} no se registraron marcas en ${prueba} para ${nombreCompleto(dep)} (${dep.categoria}).`,
  )
  if (mejorAnio) partes.push(`La mejor marca del año fue ${marcaTexto(mejorAnio.marcaValor, unidad)} (${MESES_ES[mejorAnio.fecha.getUTCMonth()]} ${anio}, ${mejorAnio.competencia}).`)
  if (pbReg && mejorAnio && pbReg.id !== mejorAnio.id) partes.push(`Respecto a su marca personal histórica (PB ${marcaTexto(pbReg.marcaValor, unidad)}, ${MESES_ES[pbReg.fecha.getUTCMonth()]} ${pbReg.fecha.getUTCFullYear()}), la brecha del año es de ${Math.abs(registros.find((r) => r.marcaValor === mejorAnio.marcaValor)?.deltaPb ?? 0)} %.`)
  else if (pbReg && mejorAnio) partes.push(`La marca del año iguala su marca personal histórica (PB ${marcaTexto(pbReg.marcaValor, unidad)}).`)
  if (progreso != null && delAnio.length >= 2) partes.push(`El progreso sobre la primera marca del año es de ${progreso > 0 ? '+' : ''}${progreso} %.`)
  if (tendencia !== 'SIN DATOS SUFICIENTES') partes.push(`La tendencia lineal del año es ${tendencia} (pendiente ${firmaTend}).`)
  if (cv != null) partes.push(`La consistencia técnica fue ${consistencia} (CV ${cv} %).`)
  if (puestosAnio.length) partes.push(`Mejor puesto obtenido en el año: ${Math.min(...puestosAnio)}.`)
  const analisis = partes.join(' ')

  return {
    depId, nombre: nombreCompleto(dep), categoria: dep.categoria, sexo: dep.sexo,
    prueba, unidad, anio, nAnio: delAnio.length, nHistorico: regs.length,
    pb: pbReg ? { marca: marcaTexto(pbReg.marcaValor, unidad), fecha: pbReg.fecha.toISOString(), competencia: pbReg.competencia, valor: pbReg.marcaValor } : null,
    mejorAnio: mejorAnio ? { marca: marcaTexto(mejorAnio.marcaValor, unidad), fecha: mejorAnio.fecha.toISOString(), competencia: mejorAnio.competencia, valor: mejorAnio.marcaValor } : null,
    progreso, pendiente, tendencia, cv, consistencia,
    mejorPuestoAnio: puestosAnio.length ? Math.min(...puestosAnio) : null,
    meses, porAnio, registros, historico, analisis,
  }
}

export type AnalisisRend = Awaited<ReturnType<typeof analisisRendimiento>>
