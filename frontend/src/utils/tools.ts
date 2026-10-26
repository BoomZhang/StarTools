import SparkMD5 from 'spark-md5'
import QRCode from 'qrcode'

/* ---------------- 文本统计 ---------------- */

export interface TextStats {
  charsWithSpace: number
  charsNoSpace: number
  hanzi: number
  englishWords: number
  lines: number
  paragraphs: number
  readingMinutes: number
}

export function textStats(text: string): TextStats {
  if (!text) {
    return {
      charsWithSpace: 0,
      charsNoSpace: 0,
      hanzi: 0,
      englishWords: 0,
      lines: 0,
      paragraphs: 0,
      readingMinutes: 0,
    }
  }
  const chars = Array.from(text)
  const charsNoSpace = chars.filter((char) => !/\s/.test(char)).length
  const hanzi = (text.match(/[\u3400-\u4dbf\u4e00-\u9fff]/g) ?? []).length
  const englishWords = (text.match(/[A-Za-z][A-Za-z'-]*/g) ?? []).length
  const lines = text.split(/\r\n|\r|\n/).length
  const paragraphs = text
    .split(/\r?\n\s*\r?\n/)
    .map((part) => part.trim())
    .filter(Boolean).length
  const readingMinutes = Number((hanzi / 300 + englishWords / 200).toFixed(1))
  return {
    charsWithSpace: chars.length,
    charsNoSpace,
    hanzi,
    englishWords,
    lines,
    paragraphs,
    readingMinutes,
  }
}

/* ---------------- JSON ---------------- */

export interface JsonResult {
  output: string
  error?: { message: string; line?: number; column?: number; hint?: string }
  nodes?: number
}

function lineColumnAt(text: string, position: number): { line: number; column: number } {
  const head = text.slice(0, position)
  const lines = head.split('\n')
  return { line: lines.length, column: lines[lines.length - 1].length + 1 }
}

function countNodes(value: unknown): number {
  if (value === null || typeof value !== 'object') return 1
  if (Array.isArray(value)) return 1 + value.reduce<number>((total, item) => total + countNodes(item), 0)
  return 1 + Object.values(value as Record<string, unknown>).reduce<number>((total, item) => total + countNodes(item), 0)
}

function jsonHints(text: string): string | null {
  const hints: string[] = []
  let inString = false
  let escape = false
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    const next = text[index + 1]
    if (inString) {
      if (escape) escape = false
      else if (char === '\\') escape = true
      else if (char === '"') inString = false
      continue
    }
    if (char === '"') {
      inString = true
      continue
    }
    if (char === '/' && (next === '/' || next === '*')) {
      hints.push('检测到注释。JSON 不支持注释，请先移除。')
      break
    }
    if (char === ',') {
      let look = index + 1
      while (look < text.length && /\s/.test(text[look])) look += 1
      if (text[look] === '}' || text[look] === ']') {
        hints.push('检测到对象或数组末尾的多余逗号，请移除后再试。')
        break
      }
    }
  }
  return hints[0] ?? null
}

export function transformJson(
  text: string,
  mode: 'pretty' | 'minify' | 'validate' | 'escape' | 'unescape',
  indent: 2 | 4 | 'tab',
): JsonResult {
  if (!text.trim()) return { output: '', error: { message: '请输入 JSON 文本' } }

  if (mode === 'escape' || mode === 'unescape') {
    try {
      if (mode === 'escape') {
        return { output: JSON.stringify(text).slice(1, -1) }
      }
      const raw = text.trim()
      const value = raw.startsWith('"') ? JSON.parse(raw) : JSON.parse(`"${raw}"`)
      return { output: String(value) }
    } catch {
      return { output: '', error: { message: '转义序列不合法，无法去转义' } }
    }
  }

  try {
    const parsed = JSON.parse(text)
    const nodes = countNodes(parsed)
    if (mode === 'validate') {
      return { output: 'JSON 校验通过。', nodes }
    }
    const space = mode === 'minify' ? undefined : indent === 'tab' ? '\t' : indent
    return { output: JSON.stringify(parsed, null, space), nodes }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    const positionMatch = /position (\d+)/i.exec(message)
    const lineMatch = /line (\d+)/i.exec(message)
    const columnMatch = /column (\d+)/i.exec(message)
    let line: number | undefined
    let column: number | undefined
    if (lineMatch) line = Number(lineMatch[1])
    if (columnMatch) column = Number(columnMatch[1])
    if (!line && positionMatch) {
      const located = lineColumnAt(text, Number(positionMatch[1]))
      line = located.line
      column = located.column
    }
    const hint = jsonHints(text) ?? undefined
    return {
      output: '',
      error: {
        message: hint || 'JSON 语法错误，请检查引号、括号与逗号。',
        line,
        column,
        hint: hint ? '修正后可再次校验，不会自动改写原文。' : undefined,
      },
    }
  }
}

/* ---------------- Base64 ---------------- */

function bytesToBase64(bytes: Uint8Array): string {
  let binary = ''
  const chunk = 0x8000
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunk))
  }
  return btoa(binary)
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  return bytes
}

function wrapBase64(value: string, wrap: boolean): string {
  if (!wrap) return value
  return value.replace(/(.{76})/g, '$1\n').trimEnd()
}

export function encodeBase64Text(text: string, urlSafe: boolean, wrap = false): string {
  const bytes = new TextEncoder().encode(text)
  let value = bytesToBase64(bytes)
  if (urlSafe) value = value.replace(/\+/g, '-').replace(/\//g, '_')
  return wrapBase64(value, wrap)
}

export function decodeBase64Text(value: string, urlSafe: boolean): string {
  const cleaned = value.replace(/\s+/g, '')
  const normalized = urlSafe || /[-_]/.test(cleaned) ? cleaned.replace(/-/g, '+').replace(/_/g, '/') : cleaned
  const invalid = normalized.search(/[^A-Za-z0-9+/=]/)
  if (invalid >= 0) {
    throw new Error(`第 ${invalid + 1} 个字符不合法：${normalized[invalid]}`)
  }
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
  let bytes: Uint8Array
  try {
    bytes = base64ToBytes(padded)
  } catch {
    throw new Error('Base64 内容不完整或包含非法填充，无法解码')
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    throw new Error('解码结果不是有效的 UTF-8 文本')
  }
}

export async function fileToBase64(file: File, urlSafe: boolean, dataUri: boolean): Promise<string> {
  const buffer = await file.arrayBuffer()
  let value = bytesToBase64(new Uint8Array(buffer))
  if (urlSafe) value = value.replace(/\+/g, '-').replace(/\//g, '_')
  value = wrapBase64(value, true)
  if (dataUri) {
    return `data:${file.type || 'application/octet-stream'};base64,${value.replace(/\n/g, '')}`
  }
  return value
}

/* ---------------- URL ---------------- */

export function encodeUrlText(value: string, mode: 'component' | 'form', keepReserved: boolean): string {
  if (mode === 'component') {
    return keepReserved ? encodeURI(value) : encodeURIComponent(value)
  }
  const encoded = encodeURIComponent(value).replace(/%20/g, '+')
  if (!keepReserved) return encoded
  return encoded
    .replace(/%3A/gi, ':')
    .replace(/%2F/gi, '/')
    .replace(/%3F/gi, '?')
    .replace(/%23/gi, '#')
    .replace(/%5B/g, '[')
    .replace(/%5D/g, ']')
    .replace(/%40/g, '@')
    .replace(/%21/g, '!')
    .replace(/%24/g, '$')
    .replace(/%26/g, '&')
    .replace(/%27/g, "'")
    .replace(/%28/g, '(')
    .replace(/%29/g, ')')
    .replace(/%2A/gi, '*')
    .replace(/%2B/g, '+')
    .replace(/%2C/g, ',')
    .replace(/%3B/g, ';')
    .replace(/%3D/g, '=')
}

export function decodeUrlText(value: string, mode: 'component' | 'form'): string {
  const invalid = /%(?![0-9A-Fa-f]{2})/.exec(value)
  if (invalid) {
    const position = (invalid.index ?? 0) + 1
    throw new Error(`第 ${position} 个字符处存在不完整的百分号编码：${value.slice(Math.max(0, position - 8), position + 8)}`)
  }
  const prepared = mode === 'form' ? value.replace(/\+/g, ' ') : value
  try {
    return decodeURIComponent(prepared)
  } catch {
    throw new Error('内容不是有效的 URL 编码，请检查百分号序列')
  }
}

/* ---------------- 哈希 ---------------- */

export type HashAlgorithm = 'MD5' | 'SHA-1' | 'SHA-256' | 'SHA-512'

function bufferToHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

export async function hashText(algorithm: HashAlgorithm, text: string, upper: boolean): Promise<string> {
  let hash: string
  if (algorithm === 'MD5') {
    hash = SparkMD5.hash(text)
  } else {
    const buffer = await crypto.subtle.digest(algorithm, new TextEncoder().encode(text))
    hash = bufferToHex(buffer)
  }
  return upper ? hash.toUpperCase() : hash
}

export async function hashFile(
  algorithm: HashAlgorithm,
  file: File,
  upper: boolean,
  onProgress?: (percent: number) => void,
): Promise<string> {
  let hash: string
  if (algorithm === 'MD5') {
    hash = await new Promise<string>((resolve, reject) => {
      const spark = new SparkMD5.ArrayBuffer()
      const chunkSize = 2 * 1024 * 1024
      let offset = 0
      const reader = new FileReader()
      reader.onload = (event) => {
        if (!(event.target?.result instanceof ArrayBuffer)) {
          reject(new Error('文件读取失败'))
          return
        }
        spark.append(event.target.result)
        offset += chunkSize
        onProgress?.(Math.min(99, Math.round((offset / file.size) * 100)))
        if (offset < file.size) readNext()
        else {
          onProgress?.(100)
          resolve(spark.end())
        }
      }
      reader.onerror = () => reject(new Error('文件读取失败'))
      function readNext() {
        reader.readAsArrayBuffer(file.slice(offset, offset + chunkSize))
      }
      readNext()
    })
  } else {
    const buffer = await file.arrayBuffer()
    onProgress?.(90)
    hash = bufferToHex(await crypto.subtle.digest(algorithm, buffer))
    onProgress?.(100)
  }
  return upper ? hash.toUpperCase() : hash
}

/* ---------------- 时间戳 ---------------- */

export interface TimeResult {
  local: string
  utc: string
  iso: string
  timestampSeconds: number
  timestampMs: number
  timezone: string
}

export function convertTimestamp(input: string, unit: 's' | 'ms' | 'auto'): TimeResult {
  const trimmed = input.trim()
  if (!trimmed) throw new Error('请输入时间戳或日期')
  let date: Date
  if (/^\d{10}$/.test(trimmed) && unit !== 'ms') {
    date = new Date(Number(trimmed) * 1000)
  } else if (/^\d{13}$/.test(trimmed) && unit !== 's') {
    date = new Date(Number(trimmed))
  } else if (/^\d+$/.test(trimmed)) {
    if (unit === 'ms') date = new Date(Number(trimmed))
    else if (unit === 's') date = new Date(Number(trimmed) * 1000)
    else date = new Date(trimmed.length === 13 ? Number(trimmed) : Number(trimmed) * 1000)
  } else {
    const normalized = trimmed.replace(/\//g, '-')
    date = new Date(normalized.replace(' ', 'T'))
    if (Number.isNaN(date.getTime())) date = new Date(normalized)
  }
  if (Number.isNaN(date.getTime())) throw new Error('日期无法解析，请使用 YYYY-MM-DD HH:mm:ss 形式')
  const year = date.getUTCFullYear()
  if (year < 1970 || year > 2100) throw new Error('仅支持 1970-01-01 至 2100-12-31 之间的时间')
  return {
    local: date.toLocaleString('zh-CN', { hour12: false }),
    utc: date.toUTCString(),
    iso: date.toISOString(),
    timestampSeconds: Math.floor(date.getTime() / 1000),
    timestampMs: date.getTime(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '本地时区',
  }
}

/* ---------------- 随机与密码 ---------------- */

const LOWER = 'abcdefghijkmnopqrstuvwxyz'
const LOWER_AMBIGUOUS = 'l'
const UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
const UPPER_AMBIGUOUS = 'I'
const DIGITS = '23456789'
const DIGITS_AMBIGUOUS = '01'
const SYMBOLS = '!@#$%^&*()-_=+[]{};:,.?'

function randomInt(max: number): number {
  if (max <= 0) return 0
  const limit = Math.floor(0xffffffff / max) * max
  const buffer = new Uint32Array(1)
  do {
    crypto.getRandomValues(buffer)
  } while (buffer[0] >= limit)
  return buffer[0] % max
}

function pick(characters: string, length: number): string {
  let result = ''
  for (let index = 0; index < length; index += 1) result += characters[randomInt(characters.length)]
  return result
}

export function randomUuid(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function randomString(length: number, options: { upper: boolean; lower: boolean; digits: boolean; symbols: boolean; excludeAmbiguous: boolean }): string {
  let pool = ''
  const required: string[] = []
  if (options.lower) {
    const set = options.excludeAmbiguous ? LOWER : LOWER + LOWER_AMBIGUOUS
    pool += set
    required.push(pick(set, 1))
  }
  if (options.upper) {
    const set = options.excludeAmbiguous ? UPPER : UPPER + UPPER_AMBIGUOUS
    pool += set
    required.push(pick(set, 1))
  }
  if (options.digits) {
    const set = options.excludeAmbiguous ? DIGITS : DIGITS + DIGITS_AMBIGUOUS
    pool += set
    required.push(pick(set, 1))
  }
  if (options.symbols) {
    pool += SYMBOLS
    required.push(pick(SYMBOLS, 1))
  }
  if (!pool) throw new Error('请至少选择一种字符类型')
  const target = Math.max(length, required.length)
  const remaining = pick(pool, target - required.length)
  const merged = (required.join('') + remaining).split('')
  for (let index = merged.length - 1; index > 0; index -= 1) {
    const swap = randomInt(index + 1)
    ;[merged[index], merged[swap]] = [merged[swap], merged[index]]
  }
  return merged.join('').slice(0, length)
}

export function passwordStrength(password: string): { label: string; score: number } {
  let score = 0
  if (password.length >= 8) score += 1
  if (password.length >= 12) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1
  if (score <= 2) return { label: '弱', score }
  if (score <= 4) return { label: '中', score }
  return { label: '强', score }
}

/* ---------------- 二维码 ---------------- */

export type QrType = 'text' | 'url' | 'wifi' | 'vcard' | 'sms' | 'email' | 'tel'

export interface QrFields {
  text: string
  url: string
  wifiSsid: string
  wifiPassword: string
  wifiEncryption: 'WPA' | 'WEP' | 'nopass'
  wifiHidden: boolean
  name: string
  company: string
  title: string
  mobile: string
  phone: string
  email: string
  website: string
  address: string
  smsNumber: string
  smsMessage: string
  emailTo: string
  emailSubject: string
  emailBody: string
  telNumber: string
}

export function qrEscape(value: string): string {
  return value.replace(/([\\;,:"])/g, '\\$1').replace(/\n/g, '\\n')
}

export function buildQrContent(type: QrType, fields: QrFields): string {
  switch (type) {
    case 'url': {
      const value = fields.url.trim()
      if (!value) return ''
      return /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//.test(value) ? value : `https://${value}`
    }
    case 'wifi': {
      if (!fields.wifiSsid.trim()) return ''
      const encryption = fields.wifiEncryption === 'nopass' ? 'nopass' : fields.wifiEncryption
      return `WIFI:T:${encryption};S:${qrEscape(fields.wifiSsid)};P:${qrEscape(fields.wifiPassword)};${fields.wifiHidden ? 'H:true;' : ''};`
    }
    case 'vcard': {
      if (!fields.name.trim()) return ''
      const lines = [
        'BEGIN:VCARD',
        'VERSION:3.0',
        `FN:${qrEscape(fields.name)}`,
        `N:${qrEscape(fields.name)};;;;`,
        fields.company ? `ORG:${qrEscape(fields.company)}` : '',
        fields.title ? `TITLE:${qrEscape(fields.title)}` : '',
        fields.mobile ? `TEL;TYPE=CELL:${qrEscape(fields.mobile)}` : '',
        fields.phone ? `TEL;TYPE=WORK:${qrEscape(fields.phone)}` : '',
        fields.email ? `EMAIL:${qrEscape(fields.email)}` : '',
        fields.website ? `URL:${qrEscape(fields.website)}` : '',
        fields.address ? `ADR:;;${qrEscape(fields.address)};;;;` : '',
        'END:VCARD',
      ]
      return lines.filter(Boolean).join('\n')
    }
    case 'sms': {
      if (!fields.smsNumber.trim()) return ''
      return `SMSTO:${fields.smsNumber.trim()}:${fields.smsMessage}`
    }
    case 'email': {
      if (!fields.emailTo.trim()) return ''
      const params = new URLSearchParams()
      if (fields.emailSubject) params.set('subject', fields.emailSubject)
      if (fields.emailBody) params.set('body', fields.emailBody)
      const suffix = params.toString() ? `?${params.toString()}` : ''
      return `mailto:${fields.emailTo.trim()}${suffix}`
    }
    case 'tel':
      return fields.telNumber.trim() ? `tel:${fields.telNumber.trim()}` : ''
    default:
      return fields.text
  }
}

export function byteLength(value: string): number {
  return new TextEncoder().encode(value).length
}

function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace('#', '')
  const normalized = value.length === 3 ? value.split('').map((char) => char + char).join('') : value
  const number = Number.parseInt(normalized, 16)
  return [(number >> 16) & 255, (number >> 8) & 255, number & 255]
}

export function contrastRatio(foreground: string, background: string): number {
  function luminance(hex: string): number {
    const [r, g, b] = hexToRgb(hex).map((channel) => {
      const value = channel / 255
      return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  const l1 = luminance(foreground)
  const l2 = luminance(background)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(2))
}

export async function generateQrDataUrl(
  content: string,
  options: { size: number; level: 'L' | 'M' | 'Q' | 'H'; margin: number; dark: string; light: string },
): Promise<string> {
  return QRCode.toDataURL(content, {
    width: options.size,
    errorCorrectionLevel: options.level,
    margin: options.margin,
    color: { dark: options.dark, light: options.light },
  })
}

/* ---------------- 二维码识别 ---------------- */

export function qrResultType(content: string): string {
  if (/^https?:\/\//i.test(content)) return '网址'
  if (/^WIFI:/i.test(content)) return 'WiFi'
  if (/^BEGIN:VCARD/i.test(content)) return '名片'
  if (/^SMSTO:/i.test(content)) return '短信'
  if (/^mailto:/i.test(content)) return '邮件'
  if (/^tel:/i.test(content)) return '电话'
  return '文本'
}

export function qrDomain(content: string): string | null {
  try {
    return new URL(content).hostname
  } catch {
    return null
  }
}

export function readableFileSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
