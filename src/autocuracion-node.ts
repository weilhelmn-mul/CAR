// Lógica de autocuración de la base de datos (solo runtime Node.js).
// Ver src/instrumentation.ts para la explicación completa.
import path from 'path'
import fs from 'fs'

const DB = () => path.join(process.cwd(), 'db', 'custom.db')
const RESPALDO = () => path.join(process.cwd(), 'upload', 'backup-car-custom.db')

function mismosArchivos(a: string, b: string): boolean {
  try {
    return fs.readFileSync(a).equals(fs.readFileSync(b))
  } catch {
    return false
  }
}

export async function autocuracion() {
  try {
    fs.mkdirSync(path.join(process.cwd(), 'db'), { recursive: true })
    fs.mkdirSync(path.join(process.cwd(), 'upload'), { recursive: true })

    // Solo actúa cuando la base es el archivo local del proyecto
    const url = process.env.DATABASE_URL
    if (!url || !url.endsWith('db/custom.db')) return

    let total = -1
    try {
      const { PrismaClient } = await import('@prisma/client')
      const p = new PrismaClient()
      total = await p.deportista.count()
      await p.$disconnect()
    } catch {
      total = -1 // la base aún no existe
    }

    const hayRespaldo = fs.existsSync(RESPALDO())
    if (total <= 0 && hayRespaldo) {
      fs.copyFileSync(RESPALDO(), DB())
      console.log('[autocuración] Base de datos restaurada desde upload/backup-car-custom.db')
    } else if (total > 0 && (!hayRespaldo || !mismosArchivos(DB(), RESPALDO()))) {
      fs.copyFileSync(DB(), RESPALDO())
      console.log('[autocuración] Respaldo actualizado: upload/backup-car-custom.db')
    } else if (total <= 0 && !hayRespaldo) {
      const { execSync } = await import('child_process')
      try {
        execSync('npx prisma db push', { stdio: 'ignore' })
        console.log('[autocuración] Esquema creado (primer arranque, sin datos)')
      } catch {}
    }
  } catch (e) {
    console.error('[autocuración] Error:', e)
  }
}
