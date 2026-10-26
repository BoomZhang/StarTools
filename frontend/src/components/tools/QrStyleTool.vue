<script setup lang="ts">
import jsQR from 'jsqr'
import QRCode from 'qrcode'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import type { Tool } from '@/types'
import { imageFileToDataUrl } from '@/utils/files'
import { byteLength } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()

const content = ref('')
const size = ref(512)
const level = ref<'Q' | 'H'>('Q')
const dotStyle = ref<'square' | 'round'>('round')
const dark = ref('#14241D')
const light = ref('#FCFBF7')
const logoFiles = ref<File[]>([])
const canvas = ref<HTMLCanvasElement | null>(null)
const scanOk = ref(false)
const scanMessage = ref('')
const notice = ref('')
const rendered = ref(false)
let timer: number | undefined

const bytes = computed(() => byteLength(content.value))
const canRender = computed(() => Boolean(content.value.trim()) && bytes.value <= 1200)

watch(
  [content, size, level, dotStyle, dark, light, logoFiles],
  () => {
    window.clearTimeout(timer)
    timer = window.setTimeout(() => {
      void render()
    }, 240)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.clearTimeout(timer)
})

async function loadLogo(file: File | null): Promise<HTMLImageElement | null> {
  if (!file) return null
  const dataUrl = await imageFileToDataUrl(file)
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Logo 无法读取'))
    image.src = dataUrl
  })
}

async function render() {
  const target = canvas.value
  if (!target) return
  rendered.value = true
  scanOk.value = false
  scanMessage.value = ''
  let logoImage: HTMLImageElement | null = null
  if (!canRender.value) {
    const context = target.getContext('2d')
    if (context) {
      target.width = 512
      target.height = 512
      context.fillStyle = '#F4F1E8'
      context.fillRect(0, 0, 512, 512)
    }
    return
  }
  try {
    if (logoFiles.value[0]) logoImage = await loadLogo(logoFiles.value[0])
    let qr
    try {
      qr = QRCode.create(content.value, { errorCorrectionLevel: level.value })
    } catch {
      throw new Error('内容超出当前容错等级可编码的范围，请缩短内容或降低容错等级')
    }
    const modules = qr.modules
    const count = modules.size
    const margin = 4
    const total = count + margin * 2
    const cell = Math.floor(size.value / total)
    const actual = cell * total
    target.width = actual
    target.height = actual
    const context = target.getContext('2d')
    if (!context) throw new Error('画布不可用')
    context.fillStyle = light.value
    context.fillRect(0, 0, actual, actual)
    context.fillStyle = dark.value
    for (let row = 0; row < count; row += 1) {
      for (let column = 0; column < count; column += 1) {
        if (!modules.data[row * count + column]) continue
        const x = (column + margin) * cell
        const y = (row + margin) * cell
        const inFinder =
          (row < 7 && column < 7) ||
          (row < 7 && column >= count - 7) ||
          (row >= count - 7 && column < 7)
        if (dotStyle.value === 'round' && !inFinder) {
          context.beginPath()
          context.arc(x + cell / 2, y + cell / 2, cell * 0.46, 0, Math.PI * 2)
          context.fill()
        } else {
          context.fillRect(x, y, cell, cell)
        }
      }
    }
    if (logoImage) {
      const maxLogo = actual * 0.2
      const ratio = Math.min(maxLogo / logoImage.width, maxLogo / logoImage.height)
      const width = logoImage.width * ratio
      const height = logoImage.height * ratio
      const x = (actual - width) / 2
      const y = (actual - height) / 2
      const padding = actual * 0.015
      context.fillStyle = light.value
      context.beginPath()
      context.roundRect(x - padding, y - padding, width + padding * 2, height + padding * 2, actual * 0.02)
      context.fill()
      context.drawImage(logoImage, x, y, width, height)
    }

    const imageData = context.getImageData(0, 0, actual, actual)
    const decoded = jsQR(imageData.data, actual, actual)
    scanOk.value = Boolean(decoded?.data)
    scanMessage.value = scanOk.value
      ? '自检通过：当前图形可被识别。'
      : '自检未通过：颜色对比、圆点样式或 Logo 可能影响扫描，请调整后重试。'
  } catch (error) {
    scanMessage.value = error instanceof Error ? error.message : '二维码生成失败'
  }
}

function download() {
  if (!canvas.value || !scanOk.value) return
  const anchor = document.createElement('a')
  anchor.href = canvas.value.toDataURL('image/png')
  anchor.download = `二维码_${new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')}.png`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  notice.value = '已开始下载 PNG。'
  void reportUsage({
    tool_code: props.tool.code,
    result: 'succeeded',
    duration_ms: 0,
  })
  window.setTimeout(() => {
    notice.value = ''
  }, 1800)
}

function fillExample() {
  content.value = 'https://example.com/startools'
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / CONTENT</span>
            <h2>二维码内容</h2>
          </div>
          <span class="section-aside">{{ bytes }} / 1200 字节</span>
        </div>
        <textarea
          v-model="content"
          class="textarea"
          rows="4"
          placeholder="输入网址或文本…"
          spellcheck="false"
        ></textarea>
        <div class="content-actions">
          <button class="text-button" type="button" @click="fillExample">填入示例</button>
          <span class="tool-tip">内容直接编码进图形，不使用短链或跳转页。</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / STYLE</span>
            <h2>外观</h2>
          </div>
        </div>
        <div class="param-grid">
          <div class="field">
            <span class="field-label"><strong>尺寸</strong></span>
            <div class="segmented">
              <button type="button" :class="{ 'is-active': size === 512 }" @click="size = 512">512</button>
              <button type="button" :class="{ 'is-active': size === 1024 }" @click="size = 1024">1024</button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>容错等级</strong></span>
            <div class="segmented">
              <button type="button" :class="{ 'is-active': level === 'Q' }" @click="level = 'Q'">Q（推荐）</button>
              <button type="button" :class="{ 'is-active': level === 'H' }" @click="level = 'H'">H</button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>点样式</strong></span>
            <div class="segmented">
              <button type="button" :class="{ 'is-active': dotStyle === 'square' }" @click="dotStyle = 'square'">方形</button>
              <button type="button" :class="{ 'is-active': dotStyle === 'round' }" @click="dotStyle = 'round'">圆点</button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>颜色</strong></span>
            <div class="color-pair">
              <div class="color-field">
                <input v-model="dark" type="color" aria-label="前景色" />
                <input v-model="dark" class="input" aria-label="前景色值" />
              </div>
              <div class="color-field">
                <input v-model="light" type="color" aria-label="背景色" />
                <input v-model="light" class="input" aria-label="背景色值" />
              </div>
            </div>
          </div>
        </div>

        <div class="option-gap">
          <FilePicker
            v-model="logoFiles"
            :max-file-mb="2"
            accept="image/png,image/jpeg,image/webp"
            title="可选：添加中心 Logo（≤2MB）"
            hint="Logo 面积不超过 20%，建议容错 Q 或 H；生成前会自动自检"
          />
        </div>
        <div class="run-bar">
          <p class="run-note">生成前会用内置解码器自检；自检失败时必须调整参数后才能下载。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!scanOk" @click="download">
              <AppIcon name="download" :size="15" />
              下载 PNG
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">PREVIEW / 自检</span>
          <span v-if="scanOk" class="badge badge-success">可扫描</span>
          <span v-else-if="rendered" class="badge badge-warn">待调整</span>
          <span v-else class="badge badge-neutral">等待内容</span>
        </div>
        <div class="local-result-body">
          <div class="styled-canvas-wrap">
            <canvas ref="canvas" class="styled-canvas"></canvas>
          </div>
          <p v-if="scanMessage" class="scan-message" :class="{ ok: scanOk }">{{ scanMessage }}</p>
          <p v-if="notice" class="tool-tip">{{ notice }}</p>
          <div v-if="logoFiles.length" class="metric-line">
            <span>Logo</span>
            <span>{{ logoFiles[0].name }}</span>
          </div>
          <div class="metric-line">
            <span>编码字节</span>
            <span>{{ bytes }} / 1200</span>
          </div>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.content-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 9px;
}

.option-gap {
  margin-top: 14px;
}

.color-pair {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.styled-canvas-wrap {
  display: grid;
  place-items: center;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
}

.styled-canvas {
  width: 100%;
  max-width: 280px;
  height: auto;
  border-radius: 4px;
}

.scan-message {
  margin-top: 10px;
  color: var(--warn);
  font-size: 10.5px;
  line-height: 1.6;
}

.scan-message.ok {
  color: var(--success);
}
</style>
