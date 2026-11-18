// Autocuración de la base de datos CAR Cusco.
// El entorno de desarrollo se restaura desde GitHub y db/custom.db no se
// versiona en el repositorio (contiene datos personales de deportistas).
// Al arrancar el servidor (runtime Node.js):
//   1. Si la base de datos está ausente o vacía y existe respaldo → la restaura.
//   2. Si la base de datos tiene datos y difiere del respaldo → actualiza el respaldo.
//   3. Si no hay datos ni respaldo (primer arranque) → crea el esquema.
// El respaldo vive en upload/ (montura que sobrevive a los reciclados del entorno).
export async function register() {
  if (process.env.NEXT_RUNTIME !== 'nodejs') return
  const { autocuracion } = await import('./autocuracion-node')
  await autocuracion()
}
