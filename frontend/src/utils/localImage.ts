import { downloadBlob } from './files'

export type LocalFormat = 'jpg' | 'png' | 'webp' | 'avif'

export interface LocalImageResult {
  blob: Blob
  filename: string
  originalSize: number
  size: number
  width: number
  height: number
  originalWidth: number
  originalHeight: number
  meta: Record<string, unknown>
}

interface DecodedImage {
  source: CanvasImageSource
  width: number
  height: number
  close: () => void
}

const MIME: Record<LocalFormat, string> = {
  jpg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
  avif: 'image/avif',
}

const EXTENSION: Record<LocalFormat, string> = {
  jpg: '.jpg',
  png: '.png',
  webp: '.webp',
  avif: '.avif',
}

export function stem(name: string): string {
  const index = name.lastIndexOf('.')
  return index > 0 ? name.slice(0, index) : name
}

export async function imageDimensions(file: File): Promise<{ width: number; height: number }> {
  const image = await decode(file)
  const size = { width: image.width, height: image.height }
  image.close()
  return size
}

async function decode(file: File): Promise<DecodedImage> {
  if (file.type === 'image/heic' || file.type === 'image/heif' || /\.hei[cf]$/i.test(file.name)) {
    if ('createImageBitmap' in window) {
      try {
        const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
        return {
          source: bitmap,
          width: bitmap.width,
          height: bitmap.height,
          close: () => bitmap.close(),
        }
      } catch {
        throw new Error('当前浏览器无法解码 HEIC，请改用服务端处理或先转换为 JPG')
      }
    }
    throw new Error('当前浏览器无法解码 HEIC，请改用服务端处理或先转换为 JPG')
  }

  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
    return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close() }
  } catch {
    // 回退到 <img>，兼容不支持 createImageBitmap 选项的浏览器
  }

  const url = URL.createObjectURL(file)
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image()
      element.onload = () => resolve(element)
      element.onerror = () => reject(new Error('图片无法解码，文件可能已损坏'))
      element.src = url
    })
    return {
      source: image,
      width: image.naturalWidth,
      height: image.naturalHeight,
      close: () => URL.revokeObjectURL(url),
    }
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('当前浏览器无法编码该格式，请选择 JPG、PNG 或 WebP'))
      },
      type,
      quality,
    )
  })
}

function createCanvas(width: number, height: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('浏览器画布不可用')
  return [canvas, context]
}

function fillBackground(context: CanvasRenderingContext2D, width: number, height: number, color: string) {
  context.fillStyle = color || '#ffffff'
  context.fillRect(0, 0, width, height)
}

async function encode(
  image: DecodedImage,
  format: LocalFormat,
  quality: number,
  width: number,
  height: number,
  background = '#ffffff',
): Promise<Blob> {
  const [canvas, context] = createCanvas(width, height)
  if (format === 'jpg') {
    fillBackground(context, width, height, background)
  }
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(image.source, 0, 0, width, height)
  return canvasToBlob(canvas, MIME[format], quality / 100)
}

export async function convertImageLocal(
  file: File,
  options: { format: LocalFormat; quality: number; background: string },
): Promise<LocalImageResult> {
  const image = await decode(file)
  try {
    const blob = await encode(image, options.format, options.quality, image.width, image.height, options.background)
    return {
      blob,
      filename: `${stem(file.name)}${EXTENSION[options.format]}`,
      originalSize: file.size,
      size: blob.size,
      width: image.width,
      height: image.height,
      originalWidth: image.width,
      originalHeight: image.height,
      meta: { format: options.format, exif_removed: true },
    }
  } finally {
    image.close()
  }
}

export async function compressImageLocal(
  file: File,
  options: { mode: 'quality' | 'target'; quality: number; targetKB: number; allowWebp: boolean },
): Promise<LocalImageResult> {
  const image = await decode(file)
  const originalFormat = file.type === 'image/png' ? 'png' : file.type === 'image/webp' ? 'webp' : 'jpg'
  try {
    if (options.mode === 'quality') {
      const blob = await encode(image, originalFormat, options.quality, image.width, image.height)
      if (blob.size >= file.size) {
        return {
          blob: file,
          filename: file.name,
          originalSize: file.size,
          size: file.size,
          width: image.width,
          height: image.height,
          originalWidth: image.width,
          originalHeight: image.height,
          meta: { mode: 'quality', ratio: 0, note: '已是最优，保留原文件。' },
        }
      }
      return {
        blob,
        filename: `${stem(file.name)}${EXTENSION[originalFormat]}`,
        originalSize: file.size,
        size: blob.size,
        width: image.width,
        height: image.height,
        originalWidth: image.width,
        originalHeight: image.height,
        meta: { mode: 'quality', ratio: Number(((1 - blob.size / file.size) * 100).toFixed(1)) },
      }
    }

    const target = Math.max(10, options.targetKB) * 1024
    const format: LocalFormat = originalFormat === 'png' && options.allowWebp ? 'webp' : originalFormat
    let best: { blob: Blob; quality: number; size: number } | null = null
    let chosen: { blob: Blob; quality: number; size: number } | null = null
    for (let quality = 90; quality >= 40; quality -= 5) {
      const blob = await encode(image, format, quality, image.width, image.height)
      if (!best || blob.size < best.size) best = { blob, quality, size: blob.size }
      if (blob.size <= target) {
        chosen = { blob, quality, size: blob.size }
        break
      }
    }
    const result = chosen ?? best
    if (!result) throw new Error('压缩失败')
    const note = chosen ? (format === 'webp' && originalFormat === 'png' ? '已转为 WebP。' : null) : '已接近极限，未能完全达到目标大小。'
    return {
      blob: result.blob,
      filename: `${stem(file.name)}${EXTENSION[format]}`,
      originalSize: file.size,
      size: result.size,
      width: image.width,
      height: image.height,
      originalWidth: image.width,
      originalHeight: image.height,
      meta: {
        mode: 'target',
        quality: result.quality,
        ratio: Number(((1 - result.size / file.size) * 100).toFixed(1)),
        note,
      },
    }
  } finally {
    image.close()
  }
}

export async function resizeImageLocal(
  file: File,
  options: {
    mode: 'pixel' | 'percent' | 'preset' | 'crop'
    width: number
    height: number
    percent: number
    preset: string
    fit: 'contain' | 'cover' | 'stretch'
    background: string
    format: 'auto' | LocalFormat
    quality: number
    crop?: { x: number; y: number; width: number; height: number }
  },
): Promise<LocalImageResult> {
  const presets: Record<string, [number, number]> = {
    '1080x1080': [1080, 1080],
    '1920x1080': [1920, 1080],
    '1280x720': [1280, 720],
    '750x1000': [750, 1000],
  }
  const image = await decode(file)
  try {
    let sourceX = 0
    let sourceY = 0
    let sourceWidth = image.width
    let sourceHeight = image.height
    if (options.crop) {
      const crop = options.crop
      sourceX = Math.max(0, Math.min(image.width - 1, Math.round(crop.x * image.width)))
      sourceY = Math.max(0, Math.min(image.height - 1, Math.round(crop.y * image.height)))
      sourceWidth = Math.max(1, Math.min(image.width - sourceX, Math.round(crop.width * image.width)))
      sourceHeight = Math.max(1, Math.min(image.height - sourceY, Math.round(crop.height * image.height)))
    }

    let targetWidth = options.width
    let targetHeight = options.height
    if (options.mode === 'crop') {
      targetWidth = sourceWidth
      targetHeight = sourceHeight
    } else if (options.mode === 'percent') {
      if (options.percent < 1 || options.percent > 400) throw new Error('缩放比例需在 1%–400% 之间')
      targetWidth = Math.round(sourceWidth * (options.percent / 100))
      targetHeight = Math.round(sourceHeight * (options.percent / 100))
    } else if (options.mode === 'preset') {
      const preset = presets[options.preset] ?? presets['1080x1080']
      ;[targetWidth, targetHeight] = preset
    }
    if (!targetWidth || !targetHeight || targetWidth < 1 || targetHeight < 1) {
      throw new Error('请填写有效的目标宽度与高度')
    }
    if (targetWidth > 10000 || targetHeight > 10000) {
      throw new Error('宽高需在 1–10000px 之间')
    }

    let sourceFormat: LocalFormat = 'jpg'
    if (file.type === 'image/png') sourceFormat = 'png'
    else if (file.type === 'image/webp') sourceFormat = 'webp'
    const format: LocalFormat =
      options.format === 'auto'
        ? sourceFormat
        : options.format

    const [canvas, context] = createCanvas(targetWidth, targetHeight)
    fillBackground(context, targetWidth, targetHeight, options.background)
    context.imageSmoothingEnabled = true
    context.imageSmoothingQuality = 'high'

    if (options.fit === 'cover') {
      const scale = Math.max(targetWidth / sourceWidth, targetHeight / sourceHeight)
      const drawWidth = sourceWidth * scale
      const drawHeight = sourceHeight * scale
      context.drawImage(
        image.source,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        (targetWidth - drawWidth) / 2,
        (targetHeight - drawHeight) / 2,
        drawWidth,
        drawHeight,
      )
    } else if (options.fit === 'stretch') {
      context.drawImage(
        image.source,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        0,
        0,
        targetWidth,
        targetHeight,
      )
    } else {
      const scale = Math.min(targetWidth / sourceWidth, targetHeight / sourceHeight)
      const drawWidth = sourceWidth * scale
      const drawHeight = sourceHeight * scale
      context.drawImage(
        image.source,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        (targetWidth - drawWidth) / 2,
        (targetHeight - drawHeight) / 2,
        drawWidth,
        drawHeight,
      )
    }

    const blob = await canvasToBlob(canvas, MIME[format], options.quality / 100)
    return {
      blob,
      filename: `${stem(file.name)}${EXTENSION[format]}`,
      originalSize: file.size,
      size: blob.size,
      width: targetWidth,
      height: targetHeight,
      originalWidth: image.width,
      originalHeight: image.height,
      meta: {
        format,
        original_width: image.width,
        original_height: image.height,
        note:
          targetWidth * targetHeight > sourceWidth * sourceHeight * 4
            ? '放大超过 200%，会明显损失清晰度。'
            : null,
      },
    }
  } finally {
    image.close()
  }
}

export function saveLocalResult(result: LocalImageResult): void {
  downloadBlob(result.blob, result.filename)
}
