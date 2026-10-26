<script setup lang="ts">
import { ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { imageFileToDataUrl } from '@/utils/files'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const files = ref<File[]>([])
const canvas = ref<HTMLCanvasElement | null>(null)
const imageSize = ref<{ width: number; height: number } | null>(null)
const current = ref<{ hex: string; rgb: string; hsl: string; x: number; y: number } | null>(null)
const palette = ref<string[]>([])
const error = ref('')
const startedAt = ref(0)

watch(
  files,
  async (value) => {
    current.value = null
    palette.value = []
    error.value = ''
    const file = value[0]
    if (!file) return
    try {
      const dataUrl = await imageFileToDataUrl(file)
      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const element = new Image()
        element.onload = () => resolve(element)
        element.onerror = () => reject(new Error('图片无法解码'))
        element.src = dataUrl
      })
      const target = canvas.value
      if (!target) return
      const scale = Math.min(1, 1100 / Math.max(image.width, image.height))
      target.width = Math.max(1, Math.round(image.width * scale))
      target.height = Math.max(1, Math.round(image.height * scale))
      const context = target.getContext('2d')
      if (!context) throw new Error('画布不可用')
      context.drawImage(image, 0, 0, target.width, target.height)
      imageSize.value = { width: image.width, height: image.height }
      palette.value = buildPalette(context, target.width, target.height)
      if (!startedAt.value) startedAt.value = performance.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    }
  },
  { deep: false },
)

function buildPalette(context: CanvasRenderingContext2D, width: number, height: number): string[] {
  const step = Math.max(2, Math.floor(Math.max(width, height) / 120))
  const counts = new Map<number, number>()
  const pixels = context.getImageData(0, 0, width, height).data
  for (let y = 0; y < height; y += step) {
    for (let x = 0; x < width; x += step) {
      const offset = (y * width + x) * 4
      const key = ((pixels[offset] >> 5) << 10) | ((pixels[offset + 1] >> 5) << 5) | (pixels[offset + 2] >> 5)
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([key]) => {
      const r = ((key >> 10) & 31) * 8 + 4
      const g = ((key >> 5) & 31) * 8 + 4
      const b = (key & 31) * 8 + 4
      return rgbToHex(r, g, b)
    })
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((value) => value.toString(16).padStart(2, '0')).join('').toUpperCase()}`
}

function rgbToHsl(r: number, g: number, b: number): string {
  const rr = r / 255
  const gg = g / 255
  const bb = b / 255
  const max = Math.max(rr, gg, bb)
  const min = Math.min(rr, gg, bb)
  const lightness = (max + min) / 2
  let hue = 0
  let saturation = 0
  if (max !== min) {
    const delta = max - min
    saturation = lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min)
    if (max === rr) hue = ((gg - bb) / delta + (gg < bb ? 6 : 0)) / 6
    else if (max === gg) hue = ((bb - rr) / delta + 2) / 6
    else hue = ((rr - gg) / delta + 4) / 6
  }
  return `hsl(${Math.round(hue * 360)}, ${Math.round(saturation * 100)}%, ${Math.round(lightness * 100)}%)`
}

function pickColor(event: MouseEvent) {
  const target = canvas.value
  if (!target) return
  const rect = target.getBoundingClientRect()
  const x = Math.floor((event.clientX - rect.left) * (target.width / rect.width))
  const y = Math.floor((event.clientY - rect.top) * (target.height / rect.height))
  const context = target.getContext('2d')
  if (!context) return
  const data = context.getImageData(x, y, 1, 1).data
  const hex = rgbToHex(data[0], data[1], data[2])
  current.value = {
    hex,
    rgb: `rgb(${data[0]}, ${data[1]}, ${data[2]})`,
    hsl: rgbToHsl(data[0], data[1], data[2]),
    x,
    y,
  }
  void reportUsage({
    tool_code: props.tool.code,
    result: 'succeeded',
    duration_ms: Math.round(performance.now() - (startedAt.value || performance.now())),
    file_count: 1,
    total_size: files.value[0]?.size ?? 0,
  })
}

async function copyValue(value: string) {
  await copy(value)
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / IMAGE</span>
            <h2>选择图片</h2>
          </div>
          <span class="section-aside">{{ imageSize ? `${imageSize.width} × ${imageSize.height} px` : '上限 ' + tool.max_file_mb + 'MB' }}</span>
        </div>
        <FilePicker
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          accept="image/jpeg,image/png,image/webp,image/bmp,image/gif,image/*"
          title="拖拽图片到这里，或点击选择"
          hint="图片只在浏览器内读取，不上传；点击预览任意位置取色"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / PALETTE</span>
            <h2>主色板</h2>
          </div>
        </div>
        <div v-if="palette.length" class="palette">
          <button
            v-for="color in palette"
            :key="color"
            type="button"
            class="swatch"
            :style="{ background: color }"
            :title="color"
            @click="copyValue(color)"
          >
            <span>{{ color }}</span>
          </button>
        </div>
        <div v-else class="empty-state"><strong>等待图片</strong><span>加载图片后会生成 6 色主色板。</span></div>
        <p class="tool-tip option-gap">色板按颜色分布粗略聚类，仅作参考；点击色块可复制 HEX。</p>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 取色</span>
          <span v-if="current" class="badge badge-local">已取色</span>
          <span v-else class="badge badge-neutral">等待点击</span>
        </div>
        <div class="local-result-body">
          <div v-if="error" class="mini-alert danger">{{ error }}</div>
          <div v-else-if="!files.length" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="image" :size="21" /></span>
            <strong>等待图片</strong>
            <p>选择一张图片后，点击任意位置即可取色。</p>
          </div>
          <template v-else>
            <div class="color-canvas-wrap">
              <canvas ref="canvas" class="color-canvas" @click="pickColor"></canvas>
            </div>
            <div v-if="current" class="color-readout">
              <span class="color-chip" :style="{ background: current.hex }"></span>
              <div class="color-values">
                <button type="button" class="color-line" @click="copyValue(current.hex)">
                  <span>HEX</span><code>{{ current.hex }}</code>
                </button>
                <button type="button" class="color-line" @click="copyValue(current.rgb)">
                  <span>RGB</span><code>{{ current.rgb }}</code>
                </button>
                <button type="button" class="color-line" @click="copyValue(current.hsl)">
                  <span>HSL</span><code>{{ current.hsl }}</code>
                </button>
              </div>
            </div>
            <p class="pixel-note mono">坐标 {{ current ? `${current.x}, ${current.y}` : '点击图片取色' }}</p>
            <p v-if="copied" class="tool-tip">已复制</p>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.option-gap {
  margin-top: 14px;
}

.palette {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.swatch {
  position: relative;
  height: 54px;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

.swatch span {
  position: absolute;
  left: 6px;
  bottom: 5px;
  padding: 2px 5px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.8);
  color: #191c17;
  font-family: var(--font-mono);
  font-size: 8px;
}

.color-canvas-wrap {
  border: 1px solid var(--line);
  border-radius: 9px;
  overflow: hidden;
  background: var(--surface-2);
}

.color-canvas {
  display: block;
  width: 100%;
  height: auto;
  cursor: crosshair;
  image-rendering: auto;
}

.color-readout {
  display: flex;
  gap: 10px;
  margin-top: 11px;
}

.color-chip {
  width: 52px;
  height: 52px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.color-values {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.color-line {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 0;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 10px;
  text-align: left;
}

.color-line:hover {
  color: var(--ink);
}

.color-line code {
  font-family: var(--font-mono);
  font-size: 10px;
}

.pixel-note {
  margin-top: 9px;
  color: var(--faint);
  font-size: 8.5px;
}
</style>
