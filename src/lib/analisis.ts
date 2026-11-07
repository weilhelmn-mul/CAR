// Agregación estadística para análisis deportivo (solo servidor)
import { db } from '@/lib/db'
import { rangoPeriodo, periodoAnterior, MESES_ES, marcaTexto, nombreCompleto, type TipoPeriodo } from './periodos'

export type MejorFila = {
  deportistaId: number; nombre: string; categoria: string; sexo: string; prueba: string
  marca: string; marcaValor: number; unidad: string; fecha: string; competencia: string; mejora: number | null
}

export async function calcularEstadisticas(tipo: TipoPeriodo, ref: string, deportistaId?: number) {
  const r = rangoPeriodo(tipo, ref)
  const rPrev = rangoPeriodo(tipo, periodoAnterior(tipo, ref))

  const [todos, resultados, resultadosPrev] = await Promise.all([
    db.deportista.findMany({ orderBy: [{ activo: 'desc' }, { orden: 'asc' }] }),
    db.resultado.findMany({ where: { fecha: { gte: r.desde, lt: r.hasta }, ...(deportistaId ? { deportistaId } : {}) }, include: { deportista: true }, orderBy: { fecha: 'asc' } }),
    db.resultado.findMany({ where: { fecha: { gte: rPrev.desde, lt: rPrev.hasta }, ...(deportistaId ? { deportistaId } : {}) } }),
  ])

  const activos = todos.filter((d) => d.activo && !d.retirado)
  const fuente = deportistaId ? todos.filter((d) => d.id === deportistaId) : activos

  const contar = (fn: (d: (typeof todos)[0]) => string) => {
    const m = new Map<string, number>()
    fuente.forEach((d) => { const k = fn(d); m.set(k, (m.get(k) ?? 0) + 1) })
    return [...m.entries()].map(([clave, total]) => ({ clave, total })).sort((a, b) => b.total - a.total)
  }

  // mejores marcas por deportista y prueba dentro del rango
  const mejores: MejorFila[] = []
  const prevBest = new Map<string, { v: number; unidad: string }>()
  resultadosPrev.forEach((res) => {
    const k = `${res.deportistaId}|${res.prueba}`
    const actual = prevBest.get(k)
    const mejor = !actual || (res.unidad === 'seg' ? res.marcaValor < actual.v : res.marcaValor > actual.v)
    if (mejor) prevBest.set(k, { v: res.marcaValor, unidad: res.unidad })
  })
  const porDepPrueba = new Map<number, Map<string, typeof resultados>>()
  resultados.forEach((res) => {
    if (!porDepPrueba.has(res.deportistaId)) porDepPrueba.set(res.deportistaId, new Map())
    const inner = porDepPrueba.get(res.deportistaId)!
    if (!inner.has(res.prueba)) inner.set(res.prueba, [])
    inner.get(res.prueba)!.push(res)
  })
  porDepPrueba.forEach((pruebas, depId) => {
    const dep = todos.find((d) => d.id === depId)
    if (!dep) return
    pruebas.forEach((lista, prueba) => {
      let mejor = lista[0]
      for (const res of lista) {
        const mejorActual = res.unidad === 'seg' ? res.marcaValor < mejor.marcaValor : res.marcaValor > mejor.marcaValor
        if (mejorActual) mejor = res
      }
      const pb = prevBest.get(`${depId}|${prueba}`)
      let mejora: number | null = null
      if (pb && pb.v > 0) {
        mejora = mejor.unidad === 'seg'
          ? ((pb.v - mejor.marcaValor) / pb.v) * 100
          : ((mejor.marcaValor - pb.v) / pb.v) * 100
        mejora = Math.round(mejora * 10) / 10
      }
      mejores.push({
        deportistaId: depId, nombre: nombreCompleto(dep), categoria: dep.categoria, sexo: dep.sexo,
        prueba, marca: marcaTexto(mejor.marcaValor, mejor.unidad), marcaValor: mejor.marcaValor, unidad: mejor.unidad,
        fecha: mejor.fecha.toISOString(), competencia: mejor.competencia, mejora,
      })
    })
  })
  mejores.sort((a, b) => a.nombre.localeCompare(b.nombre) || a.prueba.localeCompare(b.prueba))

  // resultados por mes (para gráfico) — serie COMPLETA del periodo, con 0 en los meses sin registros
  const porMes = new Map<string, number>()
  resultados.forEach((res) => {
    const y = res.fecha.getUTCFullYear(), m = res.fecha.getUTCMonth() + 1
    const k = `${MESES_ES[m - 1]} ${y}`
    porMes.set(k, (porMes.get(k) ?? 0) + 1)
  })
  const mesesSerie: { y: number; m: number }[] = []
  if (tipo === 'ANUAL') {
    const y = parseInt(ref.slice(0, 4))
    for (let m = 1; m <= 12; m++) mesesSerie.push({ y, m })
  } else {
    // recorre los meses del rango desde `desde` hasta `hasta`
    const d = new Date(Date.UTC(r.desde.getUTCFullYear(), r.desde.getUTCMonth(), 1))
    while (d < r.hasta) { mesesSerie.push({ y: d.getUTCFullYear(), m: d.getUTCMonth() + 1 }); d.setUTCMonth(d.getUTCMonth() + 1) }
  }
  const resultadosPorMes = mesesSerie.map(({ y, m }) => ({ mes: `${MESES_ES[m - 1]} ${y}`, total: porMes.get(`${MESES_ES[m - 1]} ${y}`) ?? 0 }))

  const ingresos = todos.filter((d) => d.fechaIngreso && d.fechaIngreso >= r.desde && d.fechaIngreso < r.hasta).length

  return {
    etiqueta: r.etiqueta, tipo, ref,
    totalDeportistas: todos.length, activos: activos.length,
    pad: activos.filter((d) => d.pad).length,
    ingresos, resultados: resultados.length,
    porCategoria: contar((d) => d.categoria),
    porSexo: contar((d) => d.sexo),
    porDeporte: contar((d) => d.deporte),
    porModalidad: contar((d) => d.modalidad),
    resultadosPorMes,
    mejores,
    detalle: resultados.map((res) => ({
      fecha: res.fecha.toISOString(), nombre: nombreCompleto(res.deportista), categoria: res.deportista.categoria,
      prueba: res.prueba, marca: res.marca, puesto: res.puesto, competencia: res.competencia, nivel: res.nivel,
    })),
  }
}
