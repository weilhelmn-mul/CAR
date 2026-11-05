// Servicio de IA — redacción técnica de formularios (ciencias del deporte)
// z-ai-web-dev-sdk SOLO en el servidor.
import ZAI from 'z-ai-web-dev-sdk'

const SISTEMA_BASE = `Eres el asesor técnico deportivo del Instituto Peruano del Deporte (IPD) — Dirección Nacional de Deportes Afiliados (DINADAF), Centro Alto Rendimiento (CAR) Cusco, especialista en ciencias del deporte aplicadas al atletismo.
Escribes textos TÉCNICOS, FORMALES y ORIGINALES en español, con terminología propia del entrenamiento deportivo: periodización (macrociclo, mesociclo, microciclo), preparación general y específica, volumen, intensidad, densidad, carga interna y externa, transferencia, test de campo, control y chequeo, profilaxis, balance nutricional.
Reglas:
- USA SOLO los datos del contexto entregado; NO inventes cifras, nombres, marcas, fechas, lesiones ni resultados.
- Si un dato falta, redacta de forma general sin inventarlo.
- Tono institucional IPD, tercera persona o primera persona institucional, sinmarkdown.
- Extensión según lo pedido; frases completas y precisas.`

function quitarCercas(texto: string): string {
  let t = texto.trim()
  t = t.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '')
  return t.trim()
}

export async function pedirTexto(sistemaExtra: string, usuario: string): Promise<string> {
  const zai = await ZAI.create()
  const completion = await zai.chat.completions.create({
    messages: [
      { role: 'assistant', content: `${SISTEMA_BASE}\n\n${sistemaExtra}` },
      { role: 'user', content: usuario },
    ],
    thinking: { type: 'disabled' },
  })
  const contenido = completion.choices[0]?.message?.content ?? ''
  if (!contenido.trim()) throw new Error('Respuesta vacía del modelo')
  return quitarCercas(contenido)
}

export async function pedirJSON<T>(sistemaExtra: string, usuario: string): Promise<T> {
  const texto = await pedirTexto(sistemaExtra, usuario)
  try {
    return JSON.parse(quitarCercas(texto)) as T
  } catch {
    // último intento: extraer el primer bloque {...} o [...]
    const m = texto.match(/[[{][\s\S]*[\]}]/)
    if (m) return JSON.parse(m[0]) as T
    throw new Error('La IA no devolvió JSON válido')
  }
}

// ---------- Constructores de prompts por tipo ----------

export type ContextoAtleta = {
  nombre: string; sexo: string; categoria: string; deporte: string; prueba: string
  nivelTecnico: string; modalidad: string; entrenador: string; edad: number
  asistencia?: number | null; cumplimiento?: number | null
  resultados: { fecha: string; competencia: string; prueba: string; marca: string }[]
  mejoresAnteriores?: string[]
}

export type TipoIA =
  | 'f3_objetivos' | 'f3_testControles' | 'f3_detallePreparacion' | 'f3_competencias'
  | 'f3_cumplimientoObjetivos' | 'f3_evaluacionGeneral'
  | 'f1_textos' | 'f8' | 'f9'
  | 'informe_analisis' | 'ficha_informe' | 'chat'

const CAMPOS_F3: Record<string, { titulo: string; instruccion: string; ext: string }> = {
  f3_objetivos: { titulo: 'OBJETIVOS Y METAS DE LA PREPARACIÓN', instruccion: 'Redacta los objetivos y metas de la preparación del deportista para el mes indicado (2–4 objetivos concretos coherentes con su etapa y prueba). Numéralos.', ext: '120–180 palabras' },
  f3_testControles: { titulo: 'RESULTADOS DE TEST PEDAGÓGICOS, CONTROLES INTERNOS Y AVANCES', instruccion: 'Redacta un análisis de los resultados de los test/controles del mes a partir de las marcas registradas (comparación con registros previos si se dan, avances de la preparación).', ext: '100–160 palabras' },
  f3_detallePreparacion: { titulo: 'DETALLE DE LA PREPARACIÓN EN LA ETAPA O PERIODO ACTUAL', instruccion: 'Describe la etapa/periodo de preparación en que se encuentra el deportista (general, específica, competitiva), contenidos y orientación de las cargas según su prueba y categoría.', ext: '100–160 palabras' },
  f3_competencias: { titulo: 'PARTICIPACIÓN EN COMPETENCIAS NACIONALES E INTERNACIONALES', instruccion: 'Detalla la participación del deportista en competencias/controles del mes SOLO con los datos entregados (nombre, fecha, marca, puesto). Si no hay registros de competencia oficial, indica la participación en controles internos y las metas competitivas próximas de forma general.', ext: '100–160 palabras' },
  f3_cumplimientoObjetivos: { titulo: 'CUMPLIMIENTO DE LOS OBJETIVOS DEL ENTRENAMIENTO Y/O COMPETENCIAS', instruccion: 'Evalúa el cumplimiento de los objetivos en función de los porcentajes de asistencia y cumplimiento del plan entregados, y las marcas registradas.', ext: '90–140 palabras' },
  f3_evaluacionGeneral: { titulo: 'EVALUACIÓN GENERAL DE LA PREPARACIÓN Y PROGRESOS DEPORTIVOS', instruccion: 'Redacta la evaluación general de la preparación del mes: nivel de cumplimiento, progresos observados, aspectos a reforzar y recomendaciones técnicas.', ext: '120–180 palabras' },
}

export function construirPrompt(tipo: TipoIA, datos: Record<string, unknown>): { sistema: string; usuario: string; json: boolean } {
  const periodo = String(datos.periodoEtiqueta ?? '')
  const atleta = datos.atleta as ContextoAtleta | undefined

  if (tipo.startsWith('f3_') && atleta) {
    const campo = CAMPOS_F3[tipo]
    const resumen = {
      Deportista: `${atleta.nombre} (${atleta.sexo}, categoría ${atleta.categoria}, ${atleta.edad} años)`,
      Deporte: `${atleta.deporte} — prueba: ${atleta.prueba} — nivel ${atleta.nivelTecnico} (${atleta.modalidad})`,
      Entrenador: atleta.entrenador,
      Periodo: periodo,
      'Asistencia %': atleta.asistencia ?? 'no registrada',
      'Cumplimiento del plan %': atleta.cumplimiento ?? 'no registrado',
      'Resultados del periodo': atleta.resultados,
      'Mejores marcas previas': atleta.mejoresAnteriores ?? [],
    }
    return {
      sistema: 'Redactas secciones del FORMATO AT-F3 (informe técnico mensual del deportista).',
      usuario: `Datos: ${JSON.stringify(resumen, null, 1)}\n\nRedacta la sección "${campo.titulo}" del informe del periodo. ${campo.instruccion} Extensión: ${campo.ext}. Devuelve SOLO el texto de la sección, sin título.`,
      json: false,
    }
  }

  if (tipo === 'f1_textos') {
    return {
      sistema: 'Redactas las secciones narrativas del FORMATO AT-F1 (informe mensual del área técnica JUT del CAR).',
      usuario: `Datos consolidados del mes: ${JSON.stringify(datos, null, 1)}\n\nRedacta en JSON válido (sin markdown) con estas claves: valoracionTecnica, dificultades, valoracionMedica, profilactico, balanceNutricional, funcionamientoCar, aspectosCar, otrosAspectos. Cada valor: párrafo técnico institucional de 2–5 frases, coherente con los datos (no inventes nombres ni lesiones específicas; si no hay datos, redacta en términos generales prudentes).`,
      json: true,
    }
  }

  if (tipo === 'f8') {
    return {
      sistema: 'Elaboras el PLAN DE TRABAJO MENSUAL del Jefe de Unidad Técnica (FORMATO AT-F8) del CAR Cusco.',
      usuario: `Datos: ${JSON.stringify(datos, null, 1)}\n\nGenera el plan mensual de trabajo técnico. Devuelve JSON válido (sin markdown): {"actividades": [{"actividad": "...", "fecha": "DD/MM/AAAA", "hora": "HH:MM", "lugar": "...", "observaciones": "..."}]} con 8 actividades técnicas realistas y coherentes con el calendario del mes (evaluaciones, revisión de planes, controles de topes, reuniones técnicas, capacitación, visitas técnicas, evaluación final), usando fechas dentro del mes indicado y lugares del CAR Cusco.`,
      json: true,
    }
  }

  if (tipo === 'f9') {
    return {
      sistema: 'Redactas el FORMATO AT-F9 (informe de cumplimiento del Jefe de Unidad Técnica sobre el plan del mes anterior).',
      usuario: `Datos del periodo evaluado: ${JSON.stringify(datos, null, 1)}\n\nRedacta en JSON válido (sin markdown) con las claves: evaluacionCumplimiento, dificultades, resenaRevision, resumenDificultades, analisisObjetivos, otrosInteres. Cada valor: 2–5 frases técnicas coherentes con los porcentajes y datos entregados; las dificultades deben incluir un aspecto de alimentación y otro operativo en términos generales prudentes.`,
      json: true,
    }
  }

  if (tipo === 'informe_analisis') {
    return {
      sistema: 'Elaboras informes técnicos de análisis deportivo consolidado para la DINADAF-IPD.',
      usuario: `Datos estadísticos del periodo: ${JSON.stringify(datos, null, 1)}\n\nRedacta un INFORME DE ANÁLISIS DEPORTIVO del periodo en texto plano con esta estructura:\n1) GENERALIDADES DEL PERIODO\n2) COMPOSICIÓN DEL GRUPO (categorías, sexo, deporte)\n3) RENDIMIENTO: MEJORES MARCAS Y PROGRESOS (cita deportistas y marcas de los datos)\n4) ASPECTOS DESTACADOS\n5) DIFICULTADES OBSERVADAS\n6) RECOMENDACIONES TÉCNICAS\nUsa solo los datos entregados. 250–400 palabras.`,
      json: false,
    }
  }

  if (tipo === 'ficha_informe' && atleta) {
    return {
      sistema: 'Elaboras informes técnicos integrales de deportistas (ficha 360°) para el CAR Cusco.',
      usuario: `Ficha del deportista: ${JSON.stringify({ ...atleta, periodo }, null, 1)}\n\nRedacta un INFORME INTEGRAL DEL DEPORTISTA en texto plano con secciones: PERFIL DEL DEPORTISTA / ESTADO DE LA PREPARACIÓN / EVOLUCIÓN DE MARCAS (cita las marcas entregadas) / OBSERVACIONES TÉCNICAS / RECOMENDACIONES. Usa solo los datos entregados. 200–320 palabras.`,
      json: false,
    }
  }

  // chat libre
  const contexto = datos.contexto ? `\n\nContexto actual del sistema: ${JSON.stringify(datos.contexto)}` : ''
  return {
    sistema: `Atiendes consultas del personal técnico del CAR Cusco (IPD-DINADAF). Formatos que gestiona el sistema:
- AT-F3: informe técnico mensual del deportista (objetivos, horario, % asistencia, % cumplimiento, test y controles, competencias, evaluación general).
- AT-F1: informe mensual consolidado del CAR (matrículas por categoría, valoración técnica por deportista, valoración médica y del funcionamiento del CAR).
- AT-F8: plan de trabajo mensual del Jefe de Unidad Técnica (actividades, fechas, horas, lugares).
- AT-F9: informe de cumplimiento del JUT sobre el plan del mes anterior (tareas, dificultades, visitas técnicas, evaluación BUENO/REGULAR/MALO).
- ALIMENTACIÓN: programación del servicio de alimentación por quincena (1-15 y 16-fin de mes).
- SEGURO: lista oficial de deportistas con datos completos y seguro PAD (SI/NO).
Categorías deportivas: U-18, U-20, U-23, MAY, JUV. Responde en texto plano sin markdown, útil, técnico y breve (máx. 250 palabras).`,
    usuario: `${String(datos.mensaje ?? '')}${contexto}`,
    json: false,
  }
}
