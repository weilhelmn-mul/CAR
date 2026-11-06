'use client'

// SISTEMA DE GESTIÓN DE FORMATOS AT · IPD DINADAF — CAR CUSCO
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LayoutDashboard, Users, FileText, BarChart3, Bot, FileSignature } from 'lucide-react'
import Inicio from './inicio'
import Deportistas from './deportistas'
import Formatos from './formatos'
import Analisis from './analisis'
import Asistente from './asistente'
import Firmas from './firmas'

export default function Principal() {
  const [tab, setTab] = useState('inicio')
  const [depIdFicha, setDepIdFicha] = useState<number | null>(null)

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <header className="bg-gradient-to-r from-red-950 via-red-900 to-red-800 text-white shadow-lg">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white font-black text-red-800">IPD</div>
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold leading-tight sm:text-lg">SISTEMA DE GESTIÓN DE FORMATOS AT</h1>
            <p className="text-[11px] uppercase tracking-wider text-red-200 sm:text-xs">Instituto Peruano del Deporte · DINADAF · CAR Cusco</p>
          </div>
          <span className="ml-auto rounded-full bg-white/10 px-3 py-1 text-xs font-semibold">v3.0 · con Asistente IA</span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-2 py-4 sm:px-4">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="mb-4 flex h-auto flex-wrap justify-start gap-1 bg-white p-1 shadow-sm">
            <TabsTrigger value="inicio" className="data-[state=active]:bg-red-800 data-[state=active]:text-white"><LayoutDashboard className="h-4 w-4" /> Inicio</TabsTrigger>
            <TabsTrigger value="deportistas" className="data-[state=active]:bg-red-800 data-[state=active]:text-white"><Users className="h-4 w-4" /> Deportistas</TabsTrigger>
            <TabsTrigger value="formatos" className="data-[state=active]:bg-red-800 data-[state=active]:text-white"><FileText className="h-4 w-4" /> Formatos</TabsTrigger>
            <TabsTrigger value="analisis" className="data-[state=active]:bg-red-800 data-[state=active]:text-white"><BarChart3 className="h-4 w-4" /> Análisis deportivo</TabsTrigger>
            <TabsTrigger value="firmas" className="data-[state=active]:bg-red-800 data-[state=active]:text-white"><FileSignature className="h-4 w-4" /> Firmas</TabsTrigger>
            <TabsTrigger value="asistente" className="data-[state=active]:bg-red-800 data-[state=active]:text-white"><Bot className="h-4 w-4" /> Asistente IA</TabsTrigger>
          </TabsList>
          <TabsContent value="inicio"><Inicio onAbrirFicha={(id) => { setDepIdFicha(id); setTab('deportistas') }} onIrA={setTab} /></TabsContent>
          <TabsContent value="deportistas"><Deportistas depIdFicha={depIdFicha} setDepIdFicha={setDepIdFicha} /></TabsContent>
          <TabsContent value="formatos"><Formatos /></TabsContent>
          <TabsContent value="analisis"><Analisis /></TabsContent>
          <TabsContent value="firmas"><Firmas /></TabsContent>
          <TabsContent value="asistente"><Asistente /></TabsContent>
        </Tabs>
      </main>

      <footer className="mt-auto bg-red-950 py-3 text-center text-xs text-red-200">
        Centro Alto Rendimiento CUSCO · Formatos AT-F1 · AT-F3 · AT-F8 · AT-F9 · Alimentación · Seguro — {new Date().getFullYear()}
      </footer>
    </div>
  )
}
