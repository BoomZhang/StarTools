import type { Component } from 'vue'

import Base64Tool from '@/components/tools/Base64Tool.vue'
import FileToolsPlaceholder from '@/components/tools/FileToolsPlaceholder.vue'
import HashTool from '@/components/tools/HashTool.vue'
import ImageColorTool from '@/components/tools/ImageColorTool.vue'
import ImageCompressTool from '@/components/tools/ImageCompressTool.vue'
import ImageConvertTool from '@/components/tools/ImageConvertTool.vue'
import ImageExtraTool from '@/components/tools/ImageExtraTool.vue'
import ImageResizeTool from '@/components/tools/ImageResizeTool.vue'
import ImagesToPdfTool from '@/components/tools/ImagesToPdfTool.vue'
import JsonFormatTool from '@/components/tools/JsonFormatTool.vue'
import MarkdownTool from '@/components/tools/MarkdownTool.vue'
import MediaExtraTool from '@/components/tools/MediaExtraTool.vue'
import OcrExtraTool from '@/components/tools/OcrExtraTool.vue'
import OcrTool from '@/components/tools/OcrTool.vue'
import PdfExtraTool from '@/components/tools/PdfExtraTool.vue'
import PdfMergeTool from '@/components/tools/PdfMergeTool.vue'
import PdfSplitTool from '@/components/tools/PdfSplitTool.vue'
import PdfToImagesTool from '@/components/tools/PdfToImagesTool.vue'
import QrBatchTool from '@/components/tools/QrBatchTool.vue'
import QrGenerateTool from '@/components/tools/QrGenerateTool.vue'
import QrScanTool from '@/components/tools/QrScanTool.vue'
import QrStyleTool from '@/components/tools/QrStyleTool.vue'
import RandomTool from '@/components/tools/RandomTool.vue'
import RegexTool from '@/components/tools/RegexTool.vue'
import TextCountTool from '@/components/tools/TextCountTool.vue'
import TimestampTool from '@/components/tools/TimestampTool.vue'
import UrlCodecTool from '@/components/tools/UrlCodecTool.vue'

export const TOOL_COMPONENTS: Record<string, Component> = {
  'IMG-01': ImageConvertTool,
  'IMG-02': ImageCompressTool,
  'IMG-03': ImageResizeTool,
  'IMG-04': ImageExtraTool,
  'IMG-05': ImageExtraTool,
  'IMG-06': ImageColorTool,
  'IMG-07': ImageExtraTool,
  'DOC-01': ImagesToPdfTool,
  'DOC-02': PdfMergeTool,
  'DOC-03': PdfSplitTool,
  'DOC-04': PdfToImagesTool,
  'DOC-05': PdfExtraTool,
  'DOC-06': PdfExtraTool,
  'DOC-07': PdfExtraTool,
  'DOC-08': PdfExtraTool,
  'DOC-09': PdfExtraTool,
  'TXT-01': TextCountTool,
  'TXT-03': JsonFormatTool,
  'TXT-06': MarkdownTool,
  'TXT-07': RegexTool,
  'ENC-01': Base64Tool,
  'ENC-02': UrlCodecTool,
  'ENC-03': HashTool,
  'ENC-04': TimestampTool,
  'ENC-05': RandomTool,
  'QR-01': QrGenerateTool,
  'QR-02': QrScanTool,
  'QR-03': QrBatchTool,
  'QR-04': QrStyleTool,
  'OCR-01': OcrTool,
  'OCR-02': OcrExtraTool,
  'OCR-03': OcrExtraTool,
  'AV-01': MediaExtraTool,
  'AV-02': MediaExtraTool,
  'AV-03': MediaExtraTool,
  'AV-04': MediaExtraTool,
  'AV-05': MediaExtraTool,
  'AV-06': MediaExtraTool,
  'AV-07': MediaExtraTool,
}

/** 双端工具中已实现浏览器前端处理的编号；其余在管理台切为前端时明确提示不可用。 */
export const LOCAL_SUPPORTED = new Set([
  'IMG-01',
  'IMG-02',
  'IMG-03',
  'IMG-06',
  'TXT-01',
  'TXT-03',
  'TXT-06',
  'TXT-07',
  'ENC-01',
  'ENC-02',
  'ENC-03',
  'ENC-04',
  'ENC-05',
  'QR-01',
  'QR-02',
  'QR-03',
  'QR-04',
])

export function componentFor(code: string): Component {
  return TOOL_COMPONENTS[code] ?? FileToolsPlaceholder
}
