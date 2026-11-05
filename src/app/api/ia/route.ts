import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { pedirTexto, pedirJSON, construirPrompt, type ContextoAtleta, type TipoIA } from '@/lib/ia'
import { rangoPeriodo, marcaTexto, nombreCompleto, MESES_ES, type TipoPeriodo } from '@/lib/periodos'
import { calcularEstadisticas } from '@/lib/analisis'

/** los informes se muestran como texto plano: quita negritas/títulos markdown */
function limpiarMarkdown(t: string): string {
  return t.replace(/\*\*/g, '').replace(/^#+ /gm, '')
}

function edad(fechaNac: Date): number {
  const h = new Date()
  let e = h.getUTCFullYear() - fechaNac.getUTCFullYear()
  if (h.getUTCMonth() < fechaNac.getUTCMonth() || (h.getUTCMonth() === fechaNac.getUTCMonth() && h.getUTCDate() < fechaNac.getUTCDate())) e--
  return e
}

async function contextoAtleta(depId: number, desde: Date, hasta: Date): Promise<ContextoAtleta | null> {
  const dep = await db.deportista.findUnique({ where: { id: depId } })
  if (!dep) return null
  const res = await db.resultado.findMany({ where: { deportistaId: depId, fecha: { gte: desde, lt: hasta } }, orderBy: { fecha: 'asc' } })
  const prev = await db.resultado.findMany({ where: { deportistaId: depId, fecha: { lt: desde } }, orderBy: { fecha: 'desc' }, take: 40 })
  const mejoresPrev = new Map<string, { v: number; u: string }>()
  prev.forEach((r) => {
    const k = r.prueba
    const a = mejoresPrev.get(k)
    if (!a || (r.unidad === 'seg' ? r.marcaValor < a.v : r.marcaValor > a.v)) mejoresPrev.set(k, { v: r.marcaValor, u: r.unidad })
  })
  return {
    nombre: nombreCompleto(dep), sexo: dep.sexo, categoria: dep.categoria, deporte: dep.deporte,
    prueba: dep.prueba ?? 'no registrada', nivelTecnico: dep.nivelTecnico, modalidad: dep.modalidad,
    entrenador: dep.entrenador ?? 'no asignado', edad: edad(dep.fechaNacimiento),
    resultados: res.map((r) => ({ fecha: r.fecha.toISOString().slice(0, 10), competencia: r.competencia, prueba: r.prueba, marca: marcaTexto(r.marcaValor, r.unidad) })),
    mejoresAnteriores: [...mejoresPrev.entries()].map(([prueba, m]) => `${prueba}: ${marcaTexto(m.v, m.u)}`),
  }
}

export async function POST(req: NextRequest) {
  try {
    const b = await req.json()
    const tipo = String(b.tipo ?? 'chat') as TipoIA
    const hoy = new Date()
    const refMes = String(b.periodo ?? hoy.toISOString().slice(0, 7))
    const [y, m] = refMes.split('-').map(Number)
    const etiqueta = `${MESES_ES[m - 1]} ${y}`

    if (tipo.startsWith('f3_')) {
      const depId = Number(b.depId)
      const r = rangoPeriodo('MENSUAL', refMes)
      const atleta = await contextoAtleta(depId, r.desde, r.hasta)
      if (!atleta) return NextResponse.json({ error: 'Deportista no encontrado' }, { status: 404 })
      const f3 = await db.formatoF3.findUnique({ where: { deportistaId_periodo: { deportistaId: depId, periodo: refMes } } })
      atleta.asistencia = f3?.asistencia ?? null
      atleta.cumplimiento = f3?.cumplimiento ?? null
      const { sistema, usuario } = construirPrompt(tipo, { atleta, periodoEtiqueta: etiqueta })
      return NextResponse.json({ texto: await pedirTexto(sistema, usuario) })
    }

    if (tipo === 'f1_textos') {
      const r = rangoPeriodo('MENSUAL', refMes)
      const deps = await db.deportista.findMany({ where: { activo: true, retirado: false } })
      const f3s = await db.formatoF3.findMany({ where: { periodo: refMes } })
      const asis = f3s.filter((x) => x.asistencia != null), cum = f3s.filter((x) => x.cumplimiento != null)
      const estad = await calcularEstadisticas('MENSUAL', refMes)
      const datos = {
        Mes: etiqueta, CAR: 'CUSCO',
        Deportistas: deps.length,
        Composicion: { porCategoria: estad.porCategoria, porSexo: estad.porSexo, porDeporte: estad.porDeporte },
        AsistenciaPromedio: asis.length ? Math.round((asis.reduce((a, x) => a + (x.asistencia ?? 0), 0) / asis.length) * 10) / 10 : null,
        CumplimientoPromedio: cum.length ? Math.round((cum.reduce((a, x) => a + (x.cumplimiento ?? 0), 0) / cum.length) * 10) / 10 : null,
        MejoresMarcasDelMes: estad.mejores.map((x) => ({ nombre: x.nombre, prueba: x.prueba, marca: x.marca, mejora: x.mejora })),
      }
      const { sistema, usuario } = construirPrompt('f1_textos', datos)
      return NextResponse.json({ json: await pedirJSON<Record<string, string>>(sistema, usuario) })
    }

    if (tipo === 'f8') {
      const deps = await db.deportista.findMany({ where: { activo: true, retirado: false } })
      const categorias = [...new Set(deps.map((d) => d.categoria))].join(', ')
      const pruebas = [...new Set(deps.map((d) => d.prueba).filter(Boolean))].join(', ')
      const datos = { Mes: etiqueta, CAR: 'CUSCO', NDeportistas: deps.length, Categorias: categorias, Pruebas: pruebas, Deportes: [...new Set(deps.map((d) => d.deporte))].join(', ') }
      const { sistema, usuario } = construirPrompt('f8', datos)
      return NextResponse.json({ json: await pedirJSON<{ actividades: { actividad: string; fecha: string; hora: string; lugar: string; observaciones: string }[] }>(sistema, usuario) })
    }

    if (tipo === 'f9') {
      const f3s = await db.formatoF3.findMany({ where: { periodo: refMes } })
      const asis = f3s.filter((x) => x.asistencia != null), cum = f3s.filter((x) => x.cumplimiento != null)
      const estad = await calcularEstadisticas('MENSUAL', refMes)
      const datos = {
        MesEvaluado: etiqueta, CAR: 'CUSCO',
        TareasPlanificadas: Number(b.planificadas ?? 0), TareasCumplidas: Number(b.cumplidas ?? 0),
        AsistenciaPromedio: asis.length ? Math.round((asis.reduce((a, x) => a + (x.asistencia ?? 0), 0) / asis.length) * 10) / 10 : null,
        CumplimientoPreparacion: cum.length ? Math.round((cum.reduce((a, x) => a + (x.cumplimiento ?? 0), 0) / cum.length) * 10) / 10 : null,
        InformesF3Recibidos: f3s.length, DeportistasActivos: estad.activos,
        MejoresMarcas: estad.mejores.slice(0, 10).map((x) => ({ nombre: x.nombre, prueba: x.prueba, marca: x.marca })),
      }
      const { sistema, usuario } = construirPrompt('f9', datos)
      return NextResponse.json({ json: await pedirJSON<Record<string, string>>(sistema, usuario) })
    }

    if (tipo === 'informe_analisis') {
      const tipoP = (String(b.tipoPeriodo ?? 'MENSUAL')) as TipoPeriodo
      const ref = String(b.ref ?? refMes)
      const estad = await calcularEstadisticas(tipoP, ref)
      const datos = { Periodo: estad.etiqueta, ...estad, detalle: undefined }
      const { sistema, usuario } = construirPrompt('informe_analisis', datos)
      return NextResponse.json({ texto: limpiarMarkdown(await pedirTexto(sistema, usuario)) })
    }

    if (tipo === 'ficha_informe') {
      const depId = Number(b.depId)
      const r = rangoPeriodo('MENSUAL', refMes)
      const atleta = await contextoAtleta(depId, r.desde, r.hasta)
      if (!atleta) return NextResponse.json({ error: 'Deportista no encontrado' }, { status: 404 })
      const mejores: string[] = []
      for (const [tp, rf] of [['MENSUAL', refMes], ['BIMESTRAL', refMes], ['TRIMESTRAL', refMes], ['ANUAL', String(y)]] as [TipoPeriodo, string][]) {
        const e = await calcularEstadisticas(tp, rf, depId)
        e.mejores.forEach((x) => mejores.push(`${tp === 'MENSUAL' ? 'Mes' : tp === 'ANUAL' ? 'Año' : tp.charAt(0) + tp.slice(1).toLowerCase()} (${x.prueba}): ${x.marca}`))
      }
      const { sistema, usuario } = construirPrompt('ficha_informe', { atleta, periodoEtiqueta: r.etiqueta })
      return NextResponse.json({ texto: limpiarMarkdown(await pedirTexto(sistema, `${usuario}\n\nResumen de mejores marcas: ${JSON.stringify(mejores)}`)) })
    }

    // chat libre
    const { sistema, usuario } = construirPrompt('chat', { mensaje: String(b.mensaje ?? ''), contexto: b.contexto ?? null })
    return NextResponse.json({ texto: await pedirTexto(sistema, usuario) })
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : 'Error del asistente IA' }, { status: 500 })
  }
}
