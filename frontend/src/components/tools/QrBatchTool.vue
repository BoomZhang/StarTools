<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import type { Tool } from '@/types'
import { byteLength, generateQrDataUrl } from '@/utils/tools'
import { downloadZip } from '@/utils/zip'

const props = defineProps<{ tool: Tool }>()

const text = ref('')
const size = ref(512)
const level = ref<'M' | 'Q' | 'H'>('M')
const previews = ref<{ content: string; url: string }[]>([])
const errors = ref<string[]>([])
const generating = ref(false)
const zipping = ref(false)
const notice = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const entries = computed(() =>
  text.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 200),
)

const overLimit = computed(() => text.value.split(/\r?\n/).filter((line) => line.trim()).length > 200)

const invalidLines = computed(() =>
  entries.value
    .map((content, index) => ({ content, index, bytes: byteLength(content) }))
    .filter((item) => item.bytes > 1200)
    .map((item) => `第 ${item.index + 1} 条：编码后 ${item.bytes} 字节，超过 1200 字节`),
)

let timer: number | undefined
watch(
  [entries, size, level],
  () => {
    window.clearTimeout(timer)
    timer = window.setTimeout(() => {
      void buildPreviews()
    }, 260)
  },
  { immediate: true },
)

async function buildPreviews() {
  previews.value = []
  errors.value = [...invalidLines.value]
  generating.value = true
  try {
    for (const [index, content] of entries.value.slice(0, 5).entries()) {
      if (byteLength(content) > 1200) continue
      try {
        const url = await generateQrDataUrl(content, {
          size: 256,
          level: level.value,
          margin: 4,
          dark: '#191c17',
          light: '#FFFFFF',
        })
        previews.value.push({ content, url })
      } catch {
        errors.value.push(`第 ${index + 1} 条生成失败`)
      }
    }
  } finally {
    generating.value = false
  }
}

async function downloadAll() {
  if (!entries.value.length || zipping.value) return
  const valid = entries.value.filter((content) => byteLength(content) <= 1200)
  if (!valid.length) {
    errors.value = ['没有可生成的有效内容']
    return
  }
  zipping.value = true
  notice.value = ''
  try {
    const items: { filename: string; blob: Blob }[] = []
    const failed: string[] = []
    for (const [index, content] of valid.entries()) {
      try {
        const url = await generateQrDataUrl(content, {
          size: size.value,
          level: level.value,
          margin: 4,
          dark: '#191c17',
          light: '#FFFFFF',
        })
        const blob = await (await fetch(url)).blob()
        items.push({ filename: `QR_${String(index + 1).padStart(4, '0')}.png`, blob })
      } catch {
        failed.push(`第 ${index + 1} 条：生成失败`)
      }
    }
    if (!items.length) throw new Error('没有成功生成任何二维码')
    const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
    await downloadZip(items, `批量二维码_${stamp}.zip`)
    errors.value = [...invalidLines.value, ...failed]
    notice.value = `已生成 ${items.length} 张二维码并开始下载 ZIP。`
    void reportUsage({
      tool_code: props.tool.code,
      result: failed.length ? 'partial' : 'succeeded',
      duration_ms: 0,
      file_count: items.length,
      total_size: 0,
    })
  } catch (error) {
    errors.value = [error instanceof Error ? error.message : '打包失败']
  } finally {
    zipping.value = false
  }
}

function importCsv(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const lines = String(reader.result ?? '')
      .split(/\r?\n/)
      .map((line) => {
        const match = /^"([^"]*)"/.exec(line)
        if (match) return match[1]
        return line.split(',')[0] ?? ''
      })
      .map((value) => value.trim())
      .filter(Boolean)
      .slice(0, 200)
    text.value = lines.join('\n')
    notice.value = `已从 CSV 读取 ${lines.length} 条内容。`
    target.value = ''
  }
  reader.readAsText(file)
}

function clearAll() {
  text.value = ''
  previews.value = []
  errors.value = []
  notice.value = ''
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / CONTENT</span>
            <h2>批量内容</h2>
          </div>
          <span class="section-aside">{{ entries.length }} / 200 条</span>
        </div>
        <textarea
          v-model="text"
          class="textarea textarea-tall"
          placeholder="每行一条内容，最多 200 条。空行会被忽略。"
          spellcheck="false"
        ></textarea>
        <div class="batch-actions">
          <div class="batch-links">
            <button class="text-button" type="button" @click="fileInput?.click()">
              <AppIcon name="file" :size="13" />
              导入 CSV（取第一列）
            </button>
            <button class="text-button" type="button" @click="clearAll">清空</button>
            <input ref="fileInput" class="sr-only" type="file" accept=".csv,text/csv" @change="importCsv" />
          </div>
          <span v-if="overLimit" class="limit-warning">超过 200 条，超出部分不会生成</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>二维码参数</h2>
          </div>
        </div>
        <div class="param-grid">
          <div class="field">
            <span class="field-label"><strong>尺寸</strong></span>
            <div class="segmented">
              <button v-for="value in [256, 512, 1024]" :key="value" type="button" :class="{ 'is-active': size === value }" @click="size = value">
                {{ value }}
              </button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>容错等级</strong></span>
            <div class="segmented">
              <button v-for="value in ['M', 'Q', 'H']" :key="value" type="button" :class="{ 'is-active': level === value }" @click="level = value as 'M' | 'Q' | 'H'">
                {{ value }}
              </button>
            </div>
          </div>
        </div>
        <div class="run-bar">
          <p class="run-note">预览展示前 5 条；下载 ZIP 内含全部有效二维码，失败行单独列出。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!entries.length || zipping" @click="downloadAll">
              <AppIcon name="download" :size="15" />
              {{ zipping ? '打包中…' : '生成并下载 ZIP' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">PREVIEW / 预览</span>
          <span v-if="entries.length" class="badge badge-local">{{ entries.length }} 条</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="!entries.length" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="qr" :size="21" /></span>
            <strong>等待内容</strong>
            <p>输入多行内容后，这里会预览前 5 张二维码。</p>
          </div>
          <template v-else>
            <div class="batch-preview">
              <figure v-for="(item, index) in previews" :key="index">
                <img :src="item.url" :alt="`二维码 ${index + 1}`" />
                <figcaption class="mono">#{{ index + 1 }} · {{ item.content.slice(0, 18) }}</figcaption>
              </figure>
            </div>
            <p v-if="generating" class="tool-tip">正在更新预览…</p>
            <ul v-if="errors.length" class="batch-errors" role="alert">
              <li v-for="(message, index) in errors" :key="index">{{ message }}</li>
            </ul>
            <p v-if="notice" class="notice-line">{{ notice }}</p>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.batch-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 9px;
  flex-wrap: wrap;
}

.batch-links {
  display: flex;
  align-items: center;
  gap: 14px;
}

.limit-warning {
  color: var(--danger);
  font-size: 10px;
}

.batch-preview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.batch-preview figure {
  margin: 0;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  text-align: center;
}

.batch-preview img {
  width: 100%;
  max-width: 140px;
  height: auto;
  margin: 0 auto 6px;
}

.batch-preview figcaption {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--faint);
  font-size: 8px;
}

.batch-errors {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 7px;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 10px;
  line-height: 1.55;
}

.notice-line {
  margin-top: 9px;
  color: var(--muted);
  font-size: 10px;
}
</style>
