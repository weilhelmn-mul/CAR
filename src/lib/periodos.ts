// Utilidades de periodos — compartidas cliente/servidor (funciones puras)

export const MESES_ES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

export type TipoPeriodo = 'MENSUAL' | 'BIMESTRAL' | 'TRIMESTRAL' | 'ANUAL'
export const TIPOS_PERIODO: TipoPeriodo[] = ['MENSUAL', 'BIMESTRAL', 'TRIMESTRAL', 'ANUAL']

export function diasMes(anio: number, mes1a12: number): number {
  return new Date(Date.UTC(anio, mes1a12, 0)).getUTCDate()
}

/** ref: 'YYYY-MM' (mes/bimestre/trimestre empieza en ese mes) o 'YYYY' para anual */
export function rangoPeriodo(tipo: TipoPeriodo, ref: string): { desde: Date; hasta: Date; etiqueta: string; meses: number[] } {
  if (tipo === 'ANUAL') {
    const y = parseInt(ref.slice(0, 4))
    return {
      desde: new Date(Date.UTC(y, 0, 1)),
      hasta: new Date(Date.UTC(y + 1, 0, 1)),
      etiqueta: `AÑO ${y}`,
      meses: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    }
  }
  const y = parseInt(ref.slice(0, 4))
  const m = parseInt(ref.slice(5, 7))
  const nMeses = tipo === 'MENSUAL' ? 1 : tipo === 'BIMESTRAL' ? 2 : 3
  const meses: number[] = []
  for (let i = 0; i < nMeses; i++) meses.push(((m - 1 + i) % 12) + 1)
  const anios = meses.map((mm, i) => (m - 1 + i >= 12 ? y + 1 : y))
  const etiqueta = meses.length === 1 ? `${MESES_ES[m - 1]} ${y}` : `${MESES_ES[meses[0] - 1]} – ${MESES_ES[meses[meses.length - 1] - 1]} ${anios[anios.length - 1]}`
  const ultimoMes = meses[meses.length - 1]
  const ultimoAnio = anios[anios.length - 1]
  return {
    desde: new Date(Date.UTC(y, m - 1, 1)),
    // ultimoMes es 1-based: Date.UTC lo interpreta 0-based, por lo que (ultimoMes, día 1) = 1er día del mes siguiente
    hasta: new Date(Date.UTC(ultimoAnio, ultimoMes, 1)),
    etiqueta,
    meses,
  }
}

/** periodo anterior de igual duración (para comparar mejoras) */
export function periodoAnterior(tipo: TipoPeriodo, ref: string): string {
  if (tipo === 'ANUAL') return String(parseInt(ref) - 1)
  const y = parseInt(ref.slice(0, 4))
  const m = parseInt(ref.slice(5, 7))
  const paso = tipo === 'MENSUAL' ? 1 : tipo === 'BIMESTRAL' ? 2 : 3
  const mm = m - paso
  return mm <= 0 ? `${y - 1}-${String(mm + 12).padStart(2, '0')}` : `${y}-${String(mm).padStart(2, '0')}`
}

export type Quincena = { periodo: string; anio: number; mes: number; qn: 1 | 2; desde: Date; hasta: Date; d1: number; d2: number; etiqueta: string; etiquetaCorta: string }

/** periodo 'YYYY-MM-Q1' | 'YYYY-MM-Q2' */
export function infoQuincena(periodo: string): Quincena {
  const [y, m, q] = periodo.split('-')
  const anio = parseInt(y), mes = parseInt(m), qn = (q === 'Q2' ? 2 : 1)
  const d1 = qn === 1 ? 1 : 16
  const d2 = qn === 1 ? 15 : diasMes(anio, mes)
  const etiquetaCorta = `${String(d1).padStart(2, '0')} AL ${String(d2).padStart(2, '0')} ${MESES_ES[mes - 1]}`
  return {
    periodo, anio, mes, qn,
    desde: new Date(Date.UTC(anio, mes - 1, d1)),
    hasta: new Date(Date.UTC(anio, mes - 1, d2)),
    d1, d2,
    etiqueta: `DEL ${d1} AL ${d2} DE ${MESES_ES[mes - 1]} ${anio}`,
    etiquetaCorta,
  }
}

export function quincenasDeMes(ref: string): string[] {
  return [`${ref}-Q1`, `${ref}-Q2`]
}

/** ¿cumpleaños cae dentro de la quincena? (compara día y mes) */
export function cumpleEnQuincena(fechaNac: Date, q: Quincena): boolean {
  const mes = fechaNac.getUTCMonth() + 1
  const dia = fechaNac.getUTCDate()
  return mes === q.mes && dia >= q.d1 && dia <= q.d2
}

export function fmtFecha(d: Date | string | null | undefined): string {
  if (!d) return ''
  const dt = typeof d === 'string' ? new Date(d) : d
  return `${String(dt.getUTCDate()).padStart(2, '0')}/${String(dt.getUTCMonth() + 1).padStart(2, '0')}/${dt.getUTCFullYear()}`
}

export function fmtFechaCorta(d: Date | string): string {
  const dt = typeof d === 'string' ? new Date(d) : d
  return `${String(dt.getUTCDate()).padStart(2, '0')}/${String(dt.getUTCMonth() + 1).padStart(2, '0')}`
}

/** marca legible: seg → "11.21" o "2:28.0"; metros → "7.12" */
export function marcaTexto(valor: number, unidad: string): string {
  if (unidad === 'seg') {
    if (valor >= 60) {
      const m = Math.floor(valor / 60)
      const s = valor - m * 60
      return `${m}:${s.toFixed(1).padStart(4, '0')}`
    }
    return valor.toFixed(2)
  }
  return `${valor.toFixed(2)} m`
}

export function nombreCompleto(d: { apellidoPaterno: string; apellidoMaterno: string; nombres: string }): string {
  return `${d.apellidoPaterno} ${d.apellidoMaterno} ${d.nombres}`.replace(/\s+/g, ' ').trim()
}

export const CATEGORIAS = ['U-18', 'U-20', 'U-23', 'MAY', 'JUV']
export const NIVELES = ['DC', 'DECAN', 'DP']
export const MODALIDADES = ['INTERNO', 'EXTERNO']
export const DEPORTES = ['ATLETISMO', 'PARA ATLETISMO']
export const SEXOS = ['MASCULINO', 'FEMENINO']

export const HORARIO_DEFAULT = {
  manana: ['7:00–10:00', '7:00–10:00', '7:00–10:00', '7:00–10:00', '7:00–10:00', '6:00–11:00', 'DESCANSO'],
  tarde: ['16:00–18:00', '16:00–18:00', '16:00–18:00', '16:00–18:00', '16:00–18:00', 'DESCANSO', 'DESCANSO'],
  noche: ['DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO', 'DESCANSO'],
}
export const DIAS_SEM = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO']
