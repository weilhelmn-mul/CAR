// Conversión XLSX → PDF con LibreOffice (soffice) — preserva el formato oficial de la plantilla.
// Las conversiones se serializan para evitar conflictos de perfil de soffice.
import { execFile } from 'child_process'
import fs from 'fs'
import path from 'path'
import os from 'os'

let cadena: Promise<unknown> = Promise.resolve()

export async function xlsxAPdf(xlsx: Buffer, nombreBase: string): Promise<Buffer> {
  const tarea = cadena.then(() => convertir(xlsx, nombreBase))
  cadena = tarea.catch(() => null)
  return tarea
}

async function convertir(xlsx: Buffer, nombreBase: string): Promise<Buffer> {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'at-'))
  const base = nombreBase.replace(/[^\w\-. ]+/g, '_')
  const entrada = path.join(dir, `${base}.xlsx`)
  fs.writeFileSync(entrada, xlsx)
  try {
    await new Promise<void>((res, rej) => {
      execFile('soffice', ['--headless', '--norestore', '--convert-to', 'pdf', '--outdir', dir, entrada], { timeout: 120000 }, (err) => (err ? rej(err) : res()))
    })
    return fs.readFileSync(path.join(dir, `${base}.pdf`))
  } finally {
    try { fs.rmSync(dir, { recursive: true, force: true }) } catch { /* noop */ }
  }
}
