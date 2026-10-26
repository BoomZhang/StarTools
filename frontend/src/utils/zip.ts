import { downloadBlob } from './files'

export async function downloadZip(items: { filename: string; blob: Blob }[], zipName: string): Promise<void> {
  const { default: JSZip } = await import('jszip')
  const zip = new JSZip()
  for (const item of items) zip.file(item.filename, item.blob)
  const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' })
  downloadBlob(blob, zipName)
}
