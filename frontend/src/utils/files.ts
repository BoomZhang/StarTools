export function fileExtension(name: string): string {
  const index = name.lastIndexOf('.')
  return index >= 0 ? name.slice(index).toLowerCase() : ''
}

export function fileNameStem(name: string): string {
  const index = name.lastIndexOf('.')
  return index > 0 ? name.slice(0, index) : name
}

export function acceptsFile(file: File, accept: string): boolean {
  if (!accept || accept.trim() === '') return true
  const rules = accept
    .split(',')
    .map((rule) => rule.trim().toLowerCase())
    .filter(Boolean)
  const extension = fileExtension(file.name)
  const type = (file.type || '').toLowerCase()
  return rules.some((rule) => {
    if (rule.startsWith('.')) return extension === rule
    if (rule.endsWith('/*')) return type.startsWith(rule.slice(0, -1))
    return type === rule
  })
}

export interface FileValidationOptions {
  accept?: string
  maxFileMB?: number | null
  maxCount?: number
}

export interface FileValidationResult {
  accepted: File[]
  errors: string[]
}

export function validateFiles(
  incoming: File[],
  existing: File[],
  options: FileValidationOptions,
): FileValidationResult {
  const errors: string[] = []
  const accepted: File[] = []
  const maxCount = options.maxCount ?? 1
  const maxBytes = options.maxFileMB ? options.maxFileMB * 1024 * 1024 : null
  const seen = new Set(existing.map((file) => `${file.name}:${file.size}`))

  for (const file of incoming) {
    const key = `${file.name}:${file.size}`
    if (seen.has(key)) {
      errors.push(`${file.name} 与已添加文件重复，已跳过`)
      continue
    }
    if (options.accept && !acceptsFile(file, options.accept)) {
      errors.push(`${file.name} 格式不支持`)
      continue
    }
    if (maxBytes && file.size > maxBytes) {
      errors.push(`${file.name} 为 ${(file.size / 1024 / 1024).toFixed(1)}MB，上限 ${options.maxFileMB}MB`)
      continue
    }
    if (file.size === 0) {
      errors.push(`${file.name} 是空文件`)
      continue
    }
    if (existing.length + accepted.length >= maxCount) {
      errors.push(`单次最多 ${maxCount} 个文件，多余文件未加入`)
      break
    }
    seen.add(key)
    accepted.push(file)
  }
  return { accepted, errors }
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

export function downloadText(filename: string, text: string, mime = 'text/plain;charset=utf-8'): void {
  downloadBlob(new Blob([text], { type: mime }), filename)
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const area = document.createElement('textarea')
      area.value = text
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      area.remove()
      return ok
    } catch {
      return false
    }
  }
}

export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file)
  })
}

export function imageFileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })
}

export function triggerHrefDownload(href: string): void {
  const anchor = document.createElement('a')
  anchor.href = href
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
