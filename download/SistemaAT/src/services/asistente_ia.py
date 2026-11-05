"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 services/asistente_ia.py — Asistente IA de redacción técnica.

 Redacta, de forma ORIGINAL y con lenguaje de las ciencias del
 deporte, los campos narrativos de los formatos AT-F3, AT-F1,
 AT-F8, AT-F9 y de la evaluación nutricional.

 Dos motores:
 1. LOCAL (predeterminado, sin internet): composición paramétrica
    con bancos de frases por familia deportiva y semilla
    reproducible → cada texto es distinto por deportista/periodo
    pero repetible para auditoría.
 2. API (opcional): endpoint compatible con OpenAI configurado en
    Data/config_ia.json. Si falla, el sistema vuelve al motor local
    sin interrumpir al usuario.
=============================================================
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import unicodedata
import urllib.request
from pathlib import Path

from src import database as db
from src.config import DATA_DIR, FAMILIAS_DEPORTE, MESES
from src.services.excel import _desde_json

log = logging.getLogger("sistema_at.ia")

CONFIG_IA: Path = DATA_DIR / "config_ia.json"


# ======================================================================
# Familia deportiva y semilla
# ======================================================================
def _normalizar(texto: str) -> str:
    """Minúsculas sin tildes para comparar deportes contra las familias."""
    limpio = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in limpio if not unicodedata.combining(c))


def familia_de_deporte(deporte: str) -> str:
    """Clasifica un deporte en su familia técnica (default: 'general')."""
    clave = _normalizar(deporte)
    for familia, palabras in FAMILIAS_DEPORTE.items():
        for palabra in palabras:
            if _normalizar(palabra) in clave:
                return _normalizar(familia)
    return "general"


def _semilla(*partes: object) -> random.Random:
    """Generador pseudoaleatorio reproducible a partir del contexto."""
    material = "|".join(str(p) for p in partes)
    numero = int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:12], 16)
    return random.Random(numero)


def _elegir(aleatorio: random.Random, opciones: list[str]) -> str:
    return aleatorio.choice(opciones)


# ======================================================================
# Bancos de frases técnicas por familia (ciencias del deporte)
# ======================================================================
EJES: dict[str, dict[str, list[str]]] = {
    "resistencia": {
        "fisico": [
            "desarrollo de la potencia aeróbica máxima (VO₂max) y del umbral anaeróbico",
            "ampliación de la base aeróbica mediante volumen progresivo en zona 2",
            "mejora de la economía de carrera y de la tolerancia al lactato",
            "consolidación de la resistencia especial y de la capacidad de repe"
            "tir esfuerzos de alta intensidad",
        ],
        "carga": [
            "microciclos de 3:1 con sobrecarga progresiva y semana regenerativa",
            "distribución polarizada de la intensidad (80/20) entre umbral y series",
            "bloques de volumen con transiciones controladas hacia la intensidad específica",
        ],
        "tecnico": [
            "refinamiento del gesto técnico en fatiga para preservar la economía",
            "trabajo de técnica de zancada y cadencia objetivo",
        ],
    },
    "velocidad": {
        "fisico": [
            "desarrollo de la fuerza explosiva y de la tasa de producción de fuerza (RFD)",
            "mejora de la potencia alactácida y de la reaceleración en distancias cortas",
            "transferencia de fuerza máxima hacia la velocidad punta",
        ],
        "carga": [
            "microciclos con sesiones de alta intensidad y descansos completos",
            "progresión de series cronometradas con pausas completas (1:20–1:30)",
            "control de la carga neuromuscular mediante velocidad de ejecución",
        ],
        "tecnico": [
            "perfeccionamiento de la salida y de la fase de aceleración",
            "mecánica de sprint: frecuencia y amplitud de zancada",
        ],
    },
    "fuerza": {
        "fisico": [
            "desarrollo de la fuerza máxima con cargas al 85–90 % de 1RM",
            "trabajo de potencia con cargas medias a velocidad máxima de ejecución",
            "consolidación de la técnica bajo barra en sentadilla, press y peso muerto",
        ],
        "carga": [
            "ondulación semanal del volumen-intensidad con descargas cada 4 semanas",
            "bloques de fuerza máxima seguidos de bloque de conversión a potencia",
        ],
        "tecnico": [
            "ajuste de posiciones de arranque y de la trayectoria de la barra",
            "automatización técnica con cargas submáximas antes de la intensificación",
        ],
    },
    "combate": {
        "fisico": [
            "desarrollo de la resistencia específica por rondas y de la capacidad de repe"
            "tir acciones explosivas",
            "trabajo de fuerza isométrica de agarre y de core para el cuerpo a cuerpo",
            "adaptación de la capacidad alactácida para ataques explosivos",
        ],
        "carga": [
            "microciclos con sparring controlado y pausas progresivamente menores",
            "sesiones de situación táctica con densidad creciente",
        ],
        "tecnico": [
            "automatización de combinaciones favoritas y defensa activa",
            "estudio de rivales y ajuste de la guardia y distancias preferentes",
        ],
    },
    "equipo": {
        "fisico": [
            "desarrollo de la potencia aeróbica y de la capacidad de repe"
            "tir sprints (RSA)",
            "trabajo intermitente de alta intensidad con cambio de dirección",
            "fuerza explosiva orientada al salto y al duelo aéreo",
        ],
        "carga": [
            "microciclos en rollos con acute:chronic workload ratio controlado",
            "juegos reducidos de alta densidad como estímulo concurrente",
        ],
        "tecnico": [
            "automatización de los principios ofensivos y defensivos del modelo de juego",
            "trabajo de transiciones y de resolución en el último tercio",
        ],
    },
    "precisión": {
        "fisico": [
            "estabilidad postural y fuerza isométrica de hombro y núcleo",
            "control del ritmo respiratorio para la estabilización de la puntería",
        ],
        "carga": [
            "microciclos de alta repetición técnica con baja carga física",
            "sesiones de calidad de tiro por encima del volumen bruto",
        ],
        "tecnico": [
            "automatización de la secuencia de tiro y del control del disparo",
            "entrenamiento con presión simulada y doble puntualización",
        ],
    },
    "arte": {
        "fisico": [
            "desarrollo de la flexibilidad activa y de la fuerza relativa",
            "trabajo de potencia de piernas para elementos de impulso y elevación",
            "control postural y estabilidad central para las figuras",
        ],
        "carga": [
            "microciclos con doble sesión técnica y control de impacto articular",
            "progresión de dificultad de elementos con asistencia progresiva",
        ],
        "tecnico": [
            "pulido de la ejecución artística y de la precisión de los elementos",
            "coreografías de competición con corrección segmentaria",
        ],
    },
    "general": {
        "fisico": [
            "desarrollo de las capacidades físicas básicas con énfasis en la capacidad "
            "condicional dominante del deporte",
            "progresión de la carga orientada al pico de forma del mesociclo",
        ],
        "carga": [
            "microciclos integradores con progresión de volumen e intensidad",
            "control de la relación carga-recuperación mediante registro de bienestar",
        ],
        "tecnico": [
            "refinamiento técnico de los gestos específicos del deporte",
            "consolidación de los patrones motores propios de la especialidad",
        ],
    },
}

RECURSOS = [
    "pliometría de baja intensidad",
    "core estabilizador y trabajo preventivo del manguito rotador",
    "movilidad articular dirigida y descarga post-esfuerzo",
    "trabajo concurrente de fuerza en gimnasio",
    "protocolos de recuperación activa y sueño",
]

INDICADORES = [
    "el registro de la carga externa (RPE × duración)",
    "el control semanal de la frecuencia cardiaca de reposo",
    "la percepción subjetiva de esfuerzo y el cuestionario de bienestar",
    "los test de campo programados al cierre del mesociclo",
]

CATEGORIA_NOTA: dict[str, str] = {
    "U-18": "respetando las ventanas sensibles del desarrollo y la progresión propia de la etapa formativa",
    "U-20": "con cargas progresivas propias de la transición hacia la categoría absoluta",
    "U-23": "con mayor especificidad competitiva en la etapa de consolidación pre-absoluta",
    "MAY": "con orientación al pico de rendimiento en el calendario absoluto",
    "JUV": "con enfoque multilateral propio de la iniciación deportiva estructurada",
}

DESCRIPTORES_PCT: tuple[tuple[float, str, str], ...] = (
    (0.90, "excelente", "se recomienda sostener la estrategia actual e introducir estímulos de complejidad táctica"),
    (0.75, "satisfactoria", "se recomienda consolidar los hábitos alcanzados y revisar las sesiones de menor adherencia"),
    (0.60, "en desarrollo", "se recomienda renegociar horarios con la familia/institución y reforzar el acompañamiento"),
    (0.00, "crítica", "se recomienda reunión técnica inmediata con el deportista y rediseño del plan de carga"),
)

OBJETIVOS_NUTRICION_FRASES: dict[str, list[str]] = {
    "RENDIMIENTO": [
        "garantizar disponibilidad energética estable (> 40 kcal/kg de masa libre de grasa/día) "
        "para sostener las cargas del mesociclo",
        "periodizar los carbohidratos (6–8 g/kg los días de mayor volumen) alrededor de las "
        "sesiones de calidad",
    ],
    "HIPERTROFIA": [
        "superávit calórico moderado (~10–15 %) con 1,6–2,2 g/kg/día de proteína "
        "distribuida en 4 tomas",
        "aporte de carbohidratos alrededor del entrenamiento de fuerza para sostener el volumen",
    ],
    "DESCENSO_PESO": [
        "déficit calórico controlado (~300–500 kcal/día) protegiendo la masa magra y el rendimiento",
        "mantener la proteína alta (2,0–2,2 g/kg/día) y priorizar fibra y saciedad",
    ],
    "ASCENSO_PESO": [
        "superávit progresivo (~300–500 kcal/día) con seguimiento semanal de composición corporal",
        "5–6 comidas con densidad nutricional alta para facilitar el aumento de masa",
    ],
    "RECUPERACION": [
        "ventana nutricional post-entrenamiento (proteína + carbohidratos en relación 1:3)",
        "reposición hidroelectrolítica y apoyo ergonómico del sueño",
    ],
}


# ======================================================================
# Composición de textos (motor local)
# ======================================================================
def _frase_pct(valor: float | None) -> tuple[str, str]:
    """(adjetivo, recomendación) según el porcentaje 0–1."""
    if valor is None:
        return "sin registro", "se recomienda completar el registro de asistencia del periodo"
    for umbral, adjetivo, recomendacion in DESCRIPTORES_PCT:
        if valor >= umbral:
            return adjetivo, recomendacion
    return DESCRIPTORES_PCT[-1][1], DESCRIPTORES_PCT[-1][2]


def _pct_texto(valor: float | None) -> str:
    return "—" if valor is None else f"{round(float(valor) * 100)} %"


def redactar_objetivos_f3(ctx: dict) -> str:
    """Objetivos del mes: mezcla de capacidad física, carga, técnica y recuperación."""
    aleatorio = _semilla("f3-objetivos", ctx["nombre"], ctx["periodo"], ctx["deporte"])
    banco = EJES.get(ctx["familia"], EJES["general"])
    fisico = _elegir(aleatorio, banco["fisico"])
    carga = _elegir(aleatorio, banco["carga"])
    tecnico = _elegir(aleatorio, banco["tecnico"])
    recurso = _elegir(aleatorio, RECURSOS)
    indicador = _elegir(aleatorio, INDICADORES)
    nota_cat = CATEGORIA_NOTA.get(ctx["categoria"], CATEGORIA_NOTA["MAY"])
    mes_label = ctx.get("mes_label", ctx["periodo"])

    parrafos = (
        f"Para {mes_label}, la planificación del deportista {ctx['nombre']} ({ctx['deporte']}, "
        f"categoría {ctx['categoria']}) prioriza el {fisico}, {nota_cat}. ",
        f"La organización de la carga contempla {carga}, con {tecnico} como eje de las sesiones "
        f"principales. ",
        f"De manera complementaria se incorpora {recurso}, monitoreando {indicador} para ajustar "
        f"la progresión semana a semana.",
    )
    return "".join(parrafos)


def redactar_resultados_f3(ctx: dict) -> str:
    """Narrativa de resultados: historial competitivo del periodo/mes + SISDENA."""
    aleatorio = _semilla("f3-resultados", ctx["nombre"], ctx["periodo"], ctx["deporte"])
    filas: list = ctx.get("resultados", [])
    periodo = ctx["periodo"]
    filas_periodo = [f for f in filas if str(f["fecha"]).startswith(periodo)]
    filas_recientes = filas_periodo or filas[:4]

    lineas: list[str] = []
    if filas_recientes:
        conectores = ["Obtuvo", "Registró", "Sumó", "Consignó"]
        for fila in filas_recientes:
            fecha = str(fila["fecha"])
            mes_label = f"{MESES.get(fecha[5:7], fecha[5:7])} {fecha[:4]}" if len(fecha) >= 7 else fecha
            posicion = fila["posicion"]
            puesto = f"{posicion}.° puesto" if posicion else "participación"
            medalla = f" — medalla de {str(fila['medalla']).lower()}" if fila["medalla"] else ""
            marca = f", con marca de {fila['marca']}" if fila["marca"] else ""
            prueba = f" en {fila['prueba']}" if fila["prueba"] else ""
            lugar = f" ({fila['lugar']})" if fila["lugar"] else ""
            verbo = _elegir(aleatorio, conectores)
            lineas.append(
                f"{verbo} {puesto} en {fila['competencia']}{lugar}{prueba} "
                f"({mes_label}{marca}){medalla}."
            )
    else:
        lineas.append(
            "En el periodo no se registraron competencias oficiales; el foco se mantuvo en la "
            "preparación general y específica según el plan del mesociclo."
        )

    sisdena = ctx.get("sisdena", [])
    if sisdena:
        lineas.append("Participaciones registradas en SISDENA:")
        for p in sisdena:
            lineas.append(
                f"• {p.get('fecha', '')} — {p.get('competencia', '')} · {p.get('prueba', '')} · "
                f"{p.get('resultado', '')} · puesto {p.get('puesto', '')}".strip(" ·")
            )

    if ctx.get("pct_asistencia") is not None:
        adjetivo, _ = _frase_pct(ctx.get("pct_asistencia"))
        lineas.append(
            f"La asistencia del mes fue {_pct_texto(ctx.get('pct_asistencia'))} "
            f"(adherencia {adjetivo}), marco de referencia para interpretar los resultados."
        )
    return "\n".join(lineas)


def redactar_evaluacion_f3(ctx: dict) -> str:
    """Evaluación técnica del mes: lectura de cifras y recomendaciones."""
    aleatorio = _semilla("f3-evaluacion", ctx["nombre"], ctx["periodo"], ctx["deporte"])
    asist = ctx.get("pct_asistencia")
    cump = ctx.get("pct_cumplimiento")
    adj_asist, rec_asist = _frase_pct(asist)
    adj_cump, rec_cump = _frase_pct(cump)
    indicador = _elegir(aleatorio, INDICADORES)
    banco = EJES.get(ctx["familia"], EJES["general"])
    foco = _elegir(aleatorio, banco["fisico"])

    texto = (
        f"La asistencia del periodo se evalúa como {adj_asist} ({_pct_texto(asist)}) y el "
        f"cumplimiento de la planificación como {adj_cump} ({_pct_texto(cump)}). "
        f"{rec_asist[0].upper()}{rec_asist[1:]}. "
        f"{rec_cump[0].upper()}{rec_cump[1:]}. "
        f"Desde la lectura de las ciencias del deporte, el eje {foco} se mantiene como prioridad "
        f"del siguiente mesociclo, apoyado en {indicador} para validar la adaptación y prevenir "
        f"sobreentrenamiento."
    )
    return texto


def redactar_f1(ctx: dict) -> dict[str, str]:
    """Consolidado del CAR: evaluación CAR + observaciones generales."""
    aleatorio = _semilla("f1", ctx.get("car", ""), ctx["periodo"])
    registros = ctx.get("registros", [])
    n = len(registros)
    asistencias = [r["pct_asistencia"] for r in registros if r["pct_asistencia"] is not None]
    cumplimientos = [r["pct_cumplimiento"] for r in registros if r["pct_cumplimiento"] is not None]
    prom_asist = sum(asistencias) / len(asistencias) if asistencias else None
    prom_cump = sum(cumplimientos) / len(cumplimientos) if cumplimientos else None
    adj_asist, _ = _frase_pct(prom_asist)
    adj_cump, _ = _frase_pct(prom_cump)
    matriculas = ctx.get("matriculas", {})
    altas = sum(int(v or 0) for v in (matriculas.get("altas") or {}).values())
    bajas = sum(int(v or 0) for v in (matriculas.get("bajas") or {}).values())
    comida = _elegir(aleatorio, ("consistente", "estable", "ordenada", "en consolidación"))

    eval_car = (
        f"El CAR {ctx.get('car', '') or 'evaluado'} cierra el periodo con {n} informes AT-F3 "
        f"consolidados; la asistencia promedio es {adj_asist} ({_pct_texto(prom_asist)}) y el "
        f"cumplimiento promedio {adj_cump} ({_pct_texto(prom_cump)}). El movimiento de matrícula "
        f"del mes es {comida}: {altas} altas y {bajas} bajas."
    )
    observaciones = (
        f"Se recomienda a los entrenadores priorizar la individualización de las cargas para el "
        f"próximo mesociclo y enviar los AT-F3 dentro de los primeros cinco días hábiles. "
        f"El equipo técnico multidisciplinario (medicina, nutrición y psicología) mantendrá el "
        f"seguimiento de los casos señalados en las evaluaciones del mes."
    )
    if ctx.get("resumen_nutricion"):
        eval_car += " " + ctx["resumen_nutricion"]
    return {"eval_car": eval_car, "observaciones": observaciones}


def redactar_f8(ctx: dict) -> dict[str, str]:
    """Criterio técnico del plan mensual del JUT."""
    aleatorio = _semilla("f8", ctx.get("jut_nombre", ""), ctx["periodo"])
    banco = EJES.get(ctx.get("familia", "general"), EJES["general"])
    carga = _elegir(aleatorio, banco["carga"])
    fisico = _elegir(aleatorio, banco["fisico"])
    indicador = _elegir(aleatorio, INDICADORES)
    criterio = (
        f"El plan de {ctx.get('mes_label', ctx['periodo'])} se organiza bajo el criterio de "
        f"{carga}, con énfasis en el {fisico}. Las actividades programadas responden al calendario "
        f"competitivo del CAR y a los objetivos del mesociclo; el seguimiento se apoyará en "
        f"{indicador}. Cualquier reprogramación deberá registrar el ajuste de carga asociado."
    )
    return {"criterio_plan": criterio}


def redactar_f9(ctx: dict) -> dict[str, str]:
    """Observaciones de la visita y opinión presidencial del AT-F9."""
    aleatorio = _semilla("f9", ctx.get("jut_nombre", ""), ctx["periodo"])
    asist = ctx.get("pct_asistencia_prom")
    cump = ctx.get("pct_cumplimiento_prom")
    pct_tareas = ctx.get("pct_tareas")
    prog = int(ctx.get("tareas_programadas") or 0)
    cumpl = int(ctx.get("tareas_cumplidas") or 0)
    adj_asist, _ = _frase_pct(asist)
    adj_cump, _ = _frase_pct(cump)
    hallazgo = _elegir(aleatorio, (
        "se verificó en campo la coherencia entre lo planificado y lo ejecutado",
        "se constató el registro ordenado de la asistencia y de las cargas",
        "se observó adecuada comunicación del cuerpo técnico con los deportistas",
    ))

    obs = (
        f"Durante la visita de supervisión {hallazgo}. La asistencia promedio del periodo es "
        f"{adj_asist} ({_pct_texto(asist)}) y el cumplimiento promedio {adj_cump} "
        f"({_pct_texto(cump)}); se cumplieron {cumpl} de {prog} actividades programadas"
        + (f" ({_pct_texto(pct_tareas)})." if pct_tareas is not None else ".")
        + " Se recomienda mantener la trazabilidad documental de los ajustes de carga."
    )
    opinion = (
        f"La evaluación del periodo refleja una gestión {adj_cump} del plan técnico. Se felicita "
        f"el trabajo registrado y se recomienda continuar con el esquema de monitoreo adoptado, "
        f"asegurando la atención oportuna de los casos de menor adherencia detectados."
    )
    return {"obs_visita": obs, "opinion_presidente": opinion}


def redactar_alimentacion(ctx: dict) -> dict[str, str]:
    """Plan alimenticio técnico según objetivo, peso, kcal e IMC."""
    aleatorio = _semilla("alim", ctx["nombre"], ctx["periodo"], ctx.get("objetivo", ""))
    objetivo = ctx.get("objetivo") or "RENDIMIENTO"
    banco = OBJETIVOS_NUTRICION_FRASES.get(objetivo, OBJETIVOS_NUTRICION_FRASES["RENDIMIENTO"])
    linea1 = _elegir(aleatorio, banco)
    linea2 = _elegir(aleatorio, [f for f in banco if f != linea1] or banco)

    peso = ctx.get("peso_kg")
    estatura = ctx.get("estatura_m")
    imc = ctx.get("imc")
    kcal = ctx.get("kcal_dia")
    grasa = ctx.get("pct_grasa_corporal")

    lectura = []
    if peso and estatura:
        lectura.append(f"peso {peso:g} kg para {estatura:g} m (IMC {imc:.1f})" if imc
                       else f"peso {peso:g} kg para {estatura:g} m")
    elif imc:
        lectura.append(f"IMC {imc:.1f}")
    if grasa:
        lectura.append(f"grasa corporal estimada {grasa:g} %")
    if kcal:
        lectura.append(f"distribución objetivo de {kcal:g} kcal/día")
    base = "Perfil antropométrico del periodo: " + "; ".join(lectura) + "." if lectura else ""

    plan = (
        f"Objetivo nutricional del periodo: {objetivo.replace('_', ' ').lower()}. {base} "
        f"La estrategia prioriza {linea1}; de forma complementaria, {linea2}. "
        f"Se recomienda seguimiento antropométrico cada 4 semanas, control de la hidratación "
        f"(350–600 ml/h de ejercicio) y educación alimentaria para los días de competencia "
        f"(carga de carbohidratos y ensayo del menú pre-competitivo)."
    )
    observaciones = (
        "El plan debe ajustarse por el nutricionista del CAR según la evolución de la "
        "composición corporal y la tolerancia gastrointestinal del deportista."
    )
    return {"plan_alimenticio": plan, "observaciones": observaciones}


# ======================================================================
# Contextos desde la base de datos
# ======================================================================
def contexto_at_f3(registro_id: int) -> tuple[dict, str | None]:
    """Arma el contexto de redacción del AT-F3. Devuelve (ctx, error)."""
    registro = db.obtener_registro(registro_id)
    if registro is None:
        return {}, f"No existe el registro AT-F3 id={registro_id}."
    deportista = db.obtener_deportista(int(registro["deportista_id"]))
    deporte = (registro["deporte"] or (deportista["deporte"] if deportista else "")) if deportista else registro["deporte"]
    anio, mes_num = registro["periodo"].split("-")
    ctx = {
        "nombre": registro["nombre"],
        "deporte": registro["deporte"],
        "categoria": registro["categoria"],
        "periodo": registro["periodo"],
        "mes_label": f"{MESES.get(mes_num, mes_num)} {anio}",
        "familia": familia_de_deporte(str(deporte or "")),
        "pct_asistencia": registro["pct_asistencia"],
        "pct_cumplimiento": registro["pct_cumplimiento"],
        "resultados": db.resultados_de(int(registro["deportista_id"])),
        "sisdena": _desde_json(registro["pruebas_sisdena_json"], []),
    }
    return ctx, None


def contexto_at_f1(consolidado_id: int) -> tuple[dict, str | None]:
    consolidado = db.obtener_consolidado(consolidado_id)
    if consolidado is None:
        return {}, f"No existe el consolidado AT-F1 id={consolidado_id}."
    registros = db.registros_para_consolidado(consolidado["car"], consolidado["periodo"])
    nutricion = db.listar_alimentacion(consolidado["periodo"])
    resumen = ""
    if nutricion:
        resumen = (
            f"El módulo de alimentación registra {len(nutricion)} evaluaciones nutricionales del "
            f"periodo, integradas a la vigilancia del estado de salud."
        )
    return {
        "car": consolidado["car"],
        "periodo": consolidado["periodo"],
        "registros": registros,
        "matriculas": _desde_json(consolidado["matriculas_json"], {"altas": {}, "bajas": {}}),
        "resumen_nutricion": resumen,
    }, None


def contexto_at_f8(plan_id: int) -> tuple[dict, str | None]:
    plan = db.obtener_plan(plan_id)
    if plan is None:
        return {}, f"No existe el plan AT-F8 id={plan_id}."
    anio, mes_num = plan["periodo"].split("-")
    return {
        "jut_nombre": plan["jut_nombre"],
        "car": plan["car"],
        "periodo": plan["periodo"],
        "mes_label": f"{MESES.get(mes_num, mes_num)} {anio}",
        "familia": "general",
    }, None


def contexto_at_f9(evaluacion_id: int) -> tuple[dict, str | None]:
    evaluacion = db.obtener_evaluacion(evaluacion_id)
    if evaluacion is None:
        return {}, f"No existe la evaluación AT-F9 id={evaluacion_id}."
    return {
        "jut_nombre": evaluacion["jut_nombre"] if "jut_nombre" in evaluacion.keys() else "",
        "periodo": evaluacion["periodo_evaluado"],
        "pct_asistencia_prom": evaluacion["pct_asistencia_prom"],
        "pct_cumplimiento_prom": evaluacion["pct_cumplimiento_prom"],
        "tareas_programadas": evaluacion["tareas_programadas"],
        "tareas_cumplidas": evaluacion["tareas_cumplidas"],
        "pct_tareas": evaluacion["pct_tareas"],
    }, None


def contexto_alimentacion(registro_id: int) -> tuple[dict, str | None]:
    fila = db.obtener_alimentacion(registro_id)
    if fila is None:
        return {}, f"No existe la evaluación nutricional id={registro_id}."
    anio, mes_num = fila["periodo"].split("-")
    return {
        "nombre": fila["nombre"],
        "deporte": fila["deporte"],
        "categoria": fila["categoria"],
        "periodo": fila["periodo"],
        "mes_label": f"{MESES.get(mes_num, mes_num)} {anio}",
        "objetivo": fila["objetivo"],
        "peso_kg": fila["peso_kg"],
        "estatura_m": fila["estatura_m"],
        "imc": fila["imc"],
        "pct_grasa_corporal": fila["pct_grasa_corporal"],
        "kcal_dia": fila["kcal_dia"],
    }, None


# ======================================================================
# API opcional (compatible con OpenAI) — desactivada por defecto
# ======================================================================
def _config_api() -> dict | None:
    """Lee Data/config_ia.json si existe y está completo."""
    try:
        datos = json.loads(CONFIG_IA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not all(datos.get(k) for k in ("base_url", "api_key", "modelo")):
        return None
    return datos


def redactar_con_api(instrucciones: str) -> str | None:
    """Envía el prompt al endpoint configurado. Devuelve None si no está configurado/falla."""
    config = _config_api()
    if config is None:
        return None
    url = config["base_url"].rstrip("/") + "/chat/completions"
    cuerpo = json.dumps({
        "model": config["modelo"],
        "messages": [
            {"role": "system", "content": (
                "Eres un especialista peruano en ciencias del deporte (DINADAF - IPD). "
                "Redactas textos técnicos, sobrios y verificables para formatos oficiales. "
                "Responde ÚNICAMENTE con el texto solicitado, en español, sin preámbulos."
            )},
            {"role": "user", "content": instrucciones},
        ],
        "temperature": float(config.get("temperatura", 0.7)),
    }).encode("utf-8")
    peticion = urllib.request.Request(url, data=cuerpo, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    })
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
            return (datos["choices"][0]["message"]["content"] or "").strip() or None
    except Exception as exc:  # noqa: BLE001 - la API nunca debe tumbar el flujo
        log.warning("API de IA no disponible (%s); se usa el motor local.", exc)
        return None


# ======================================================================
# Punto de entrada unificado
# ======================================================================
def redactar(formato: str, registro_id: int) -> dict[str, str]:
    """Redacta los campos narrativos del formato pedido.

    formato: 'AT-F3' | 'AT-F1' | 'AT-F8' | 'AT-F9' | 'ALIMENTACION'
    Devuelve {campo: texto}. Si hay API configurada se usa y, ante cualquier
    fallo, se recurre al motor local (nunca se interrumpe el flujo).
    """
    constructores = {
        "AT-F3": contexto_at_f3,
        "AT-F1": contexto_at_f1,
        "AT-F8": contexto_at_f8,
        "AT-F9": contexto_at_f9,
        "ALIMENTACION": contexto_alimentacion,
    }
    if formato not in constructores:
        raise ValueError(f"Formato no soportado por el asistente: {formato}")
    ctx, error = constructores[formato](registro_id)
    if error:
        raise ValueError(error)

    if formato == "AT-F3":
        local = {
            "objetivos": redactar_objetivos_f3(ctx),
            "resultados": redactar_resultados_f3(ctx),
            "evaluacion": redactar_evaluacion_f3(ctx),
        }
    elif formato == "AT-F1":
        local = redactar_f1(ctx)
    elif formato == "AT-F8":
        local = redactar_f8(ctx)
    elif formato == "AT-F9":
        local = redactar_f9(ctx)
    else:
        local = redactar_alimentacion(ctx)

    if _config_api() is None:
        return local

    # Modo API: pedimos cada campo y validamos; el local es la red de seguridad.
    resultado: dict[str, str] = {}
    for campo, texto_local in local.items():
        instruccion = (
            f"Formato {formato} del Sistema AT (IPD - DINADAF). Redacta el campo '{campo}' "
            f"con lenguaje técnico de las ciencias del deporte. Contexto verificado:\n"
            f"{json.dumps(ctx, ensure_ascii=False, default=str)}\n"
            f"Borrador de referencia (puedes mejorarlo, no inventes datos numéricos nuevos):\n"
            f"{texto_local}"
        )
        texto_api = redactar_con_api(instruccion)
        resultado[campo] = texto_api or texto_local
    return resultado
