'use client'

// GRÁFICOS COMPARTIDOS DEL SISTEMA AT — estilo unificado, legible en PC y celular.
// Principios de diseño aplicados a todos los gráficos:
//  · Ejes limpios (sin líneas de tick), cuadrícula solo horizontal y muy tenue
//  · Valores visibles sobre las barras (útil en táctil, donde el tooltip es incómodo)
//  · Tooltip estilizado compacto (borde, sombra, tipografía 12 px)
//  · Leyendas propias tipo "chips" (nunca la leyenda nativa de recharts, que se desborda)
//  · Estados vacíos explícitos en lugar de ejes vacíos

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie,
  CartesianGrid, LabelList, type TooltipProps,
} from 'recharts'
import { Chips } from './ui-at'

const GRIS_TEXTO = '#64748b'   // slate-500
const GRIS_GRID = '#eef2f7'    // casi slate-100

// ===== Tooltip estilizado (compacto, con borde y sombra) =====
const estiloTooltip = {
  contentStyle: {
    borderRadius: 10, border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(15,23,42,.10)',
    fontSize: 12, padding: '6px 10px', background: '#ffffff',
  },
  labelStyle: { fontWeight: 700, color: '#0f172a', marginBottom: 2 },
  itemStyle: { color: '#334155', fontSize: 12 },
} as const

export function TooltipEst(props: Omit<TooltipProps<number, string>, 'cursor'> & { cursor?: object | boolean }) {
  const { cursor, ...resto } = props
  return <Tooltip cursor={cursor ?? { fill: 'rgba(148,163,184,0.12)' }} {...estiloTooltip} {...resto} />
}

// ===== Eje Y compartido (enteros, sin línea) =====
const EjeY = ({ ancho = 26 }: { ancho?: number }) => (
  <YAxis allowDecimals={false} axisLine={false} tickLine={false} width={ancho} tick={{ fontSize: 10, fill: GRIS_TEXTO }} />
)

// ===== Gráfico de barras verticales (1 serie) =====
export function GraficoBarras({
  data, colores, color = '#b91c1c', alto = 'h-44 sm:h-52', mostrarValores = true, formatoX, mensajeVacio = 'Sin datos para mostrar', ocultarCeros = false,
}: {
  data: { clave: string; total: number }[]
  colores?: string[]            // color por barra (paleta categorizada)
  color?: string                // color único para toda la serie
  alto?: string                 // clases tailwind de altura del contenedor
  mostrarValores?: boolean
  formatoX?: (v: string) => string
  mensajeVacio?: string
  ocultarCeros?: boolean        // no dibuja el "0" sobre barras vacías (series largas, ej. 12 meses)
}) {
  if (!data.length) return <div className={`${alto} flex items-center justify-center rounded-lg bg-slate-50 text-xs text-slate-400`}>{mensajeVacio}</div>
  const rotar = data.length > 6 && !!formatoX // con muchas categorías inclina un poco las etiquetas
  const muchas = data.length > 8 // series largas: margen lateral para que la 1ª/última etiqueta no se recorte
  return (
    <div className={alto}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 14, right: muchas ? 10 : 6, bottom: 0, left: muchas ? -4 : -14 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={GRIS_GRID} />
          <XAxis
            dataKey="clave" interval={0} axisLine={{ stroke: '#e2e8f0' }} tickLine={false}
            tick={{ fontSize: 10, fill: GRIS_TEXTO }} angle={rotar ? -28 : 0} textAnchor={rotar ? 'end' : 'middle'} height={rotar ? 34 : 26}
            tickFormatter={formatoX}
          />
          <EjeY />
          <TooltipEst />
          <Bar dataKey="total" name="Deportistas" radius={[4, 4, 0, 0]} maxBarSize={46}>
            {data.map((_, i) => <Cell key={i} fill={colores ? colores[i % colores.length] : color} />)}
            {mostrarValores && <LabelList dataKey="total" position="top" formatter={(v: number) => (ocultarCeros && v === 0 ? '' : v)} style={{ fontSize: 10, fontWeight: 700, fill: '#475569' }} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ===== Leyenda simple para series de líneas (sin total) =====
export const LeyendaLineas = ({ items }: { items: { clave: string; color: string }[] }) => (
  <div className="flex flex-wrap justify-center gap-1.5 pt-1">
    {items.map((x) => (
      <span key={x.clave} className="inline-flex max-w-full items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
        <span className="h-1.5 w-3 shrink-0 rounded-full" style={{ background: x.color }} /><span className="truncate">{x.clave}</span>
      </span>
    ))}
  </div>
)

// ===== Gráfico de dona (1 dimensión) con total al centro y chips de leyenda =====
export function GraficoDonut({
  data, alto = 'h-40 sm:h-48', leyenda = true, etiquetaCentro = 'total',
}: {
  data: { clave: string; total: number; color: string }[]
  alto?: string
  leyenda?: boolean
  etiquetaCentro?: string
}) {
  const total = data.reduce((a, x) => a + x.total, 0)
  if (!data.length || total === 0) {
    return (
      <div>
        <div className={`${alto} flex items-center justify-center rounded-lg bg-slate-50 text-xs text-slate-400`}>Sin datos</div>
        {leyenda && <Chips items={[]} />}
      </div>
    )
  }
  return (
    <div>
      <div className={`relative ${alto}`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data} dataKey="total" nameKey="clave" cx="50%" cy="50%"
              innerRadius="60%" outerRadius="88%" paddingAngle={data.length > 1 ? 2 : 0}
              stroke="#ffffff" strokeWidth={2}
            >
              {data.map((x) => <Cell key={x.clave} fill={x.color} />)}
            </Pie>
            <TooltipEst cursor={false} />
          </PieChart>
        </ResponsiveContainer>
        {/* total al centro de la dona */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-black leading-none text-slate-800">{total}</span>
          <span className="mt-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-400">{etiquetaCentro}</span>
        </div>
      </div>
      {leyenda && <Chips items={data} />}
    </div>
  )
}
