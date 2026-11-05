'use client'

// MÓDULO DE FORMATOS — pestañas internas
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import FormatoAlimentacion from './formato-alimentacion'
import FormatoSeguro from './formato-seguro'
import FormatoF3 from './formato-f3'
import FormatoF1 from './formato-f1'
import FormatoF8 from './formato-f8'
import FormatoF9 from './formato-f9'

export default function Formatos() {
  return (
    <Tabs defaultValue="alimentacion">
      <TabsList className="mb-4 flex h-auto flex-wrap justify-start gap-1 bg-white p-1 shadow-sm">
        <TabsTrigger value="alimentacion" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">🍽️ Alimentación</TabsTrigger>
        <TabsTrigger value="seguro" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">🛡️ Seguro</TabsTrigger>
        <TabsTrigger value="f3" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">AT-F3 · Deportista</TabsTrigger>
        <TabsTrigger value="f1" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">AT-F1 · Consolidado</TabsTrigger>
        <TabsTrigger value="f8" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">AT-F8 · Plan JUT</TabsTrigger>
        <TabsTrigger value="f9" className="data-[state=active]:bg-red-800 data-[state=active]:text-white">AT-F9 · Evaluación</TabsTrigger>
      </TabsList>
      <TabsContent value="alimentacion"><FormatoAlimentacion /></TabsContent>
      <TabsContent value="seguro"><FormatoSeguro /></TabsContent>
      <TabsContent value="f3"><FormatoF3 /></TabsContent>
      <TabsContent value="f1"><FormatoF1 /></TabsContent>
      <TabsContent value="f8"><FormatoF8 /></TabsContent>
      <TabsContent value="f9"><FormatoF9 /></TabsContent>
    </Tabs>
  )
}
