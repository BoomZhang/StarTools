<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { formatBytes } from '@/utils/format'
import { textStats } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const text = ref('')
const startedAt = ref(0)
const picked = ref<File[]>([])
const fileLoaded = ref('')
const fileError = ref('')
const readingFile = ref(false)

const stats = computed(() => textStats(text.value))
const bytes = computed(() => new TextEncoder().encode(text.value).length)
const overLimit = computed(() => bytes.value > 2 * 1024 * 1024)
const hasContent = computed(() => text.value.length > 0)

const readingText = computed(() => {
  if (!hasContent.value) return '0'
  return stats.value.readingMinutes < 0.1 ? '< 0.1' : stats.value.readingMinutes.toFixed(1)
})

const statItems = computed(() => [
  { label: '字符数（含空格）', value: stats.value.charsWithSpace },
  { label: '字符数（不含空格）', value: stats.value.charsNoSpace },
  { label: '汉字数', value: stats.value.hanzi },
  { label: '英文单词数', value: stats.value.englishWords },
  { label: '行数', value: stats.value.lines },
  { label: '段落数', value: stats.value.paragraphs },
])

const summary = computed(() =>
  [
    `字符（含空格）：${stats.value.charsWithSpace}`,
    `字符（不含空格）：${stats.value.charsNoSpace}`,
    `汉字：${stats.value.hanzi}`,
    `英文单词：${stats.value.englishWords}`,
    `行：${stats.value.lines}`,
    `段落：${stats.value.paragraphs}`,
    `阅读时长：${readingText.value} 分钟`,
  ].join('\n'),
)

function decodeText(buffer: ArrayBuffer): string {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buffer)
  } catch {
    return new TextDecoder('gb18030').decode(buffer)
  }
}

watch(picked, async (list) => {
  const file = list[0]
  fileError.value = ''
  fileLoaded.value = ''
  if (!file) return
  if (file.size > (props.tool.max_file_mb ?? 10) * 1024 * 1024) {
    fileError.value = `文件超过 ${props.tool.max_file_mb ?? 10}MB 上限`
    return
  }
  readingFile.value = true
  try {
    const buffer = await file.arrayBuffer()
    text.value = decodeText(buffer)
    startedAt.value = performance.now()
    fileLoaded.value = `${file.name} · ${formatBytes(file.size)}`
  } catch {
    fileError.value = '文件读取失败，请确认是纯文本文件后重试'
  } finally {
    readingFile.value = false
  }
})

function onInput() {
  if (!startedAt.value) startedAt.value = performance.now()
}

async function copySummary() {
  const ok = await copy(summary.value)
  if (ok && hasContent.value) {
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - (startedAt.value || performance.now())),
    })
  }
}

function fillExample() {
  text.value =
    '把一件小事交给工具，几分钟就能完成。\n\nThis is a sample paragraph for counting English words and reading time.\n\n不需要登录，也不需要先找网站。'
  startedAt.value = performance.now()
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>输入文本</h2>
          </div>
          <span class="section-aside">{{ (bytes / 1024).toFixed(1) }} KB / 2048 KB</span>
        </div>
        <div class="file-import">
          <FilePicker
            v-model="picked"
            :max-count="1"
            :max-file-mb="tool.max_file_mb"
            accept=".txt,.md,.markdown,.csv,.json,.log,.srt,.xml,.yaml,.yml,text/plain,text/markdown,text/csv,application/json"
            title="上传文本文件统计（也可直接在下方粘贴）"
            hint="TXT · MD · CSV · JSON · LOG · SRT · XML · YAML，文件只在浏览器本地读取"
          />
          <p v-if="readingFile" class="file-status">正在读取文件…</p>
          <p v-else-if="fileLoaded" class="file-status">已载入 {{ fileLoaded }}，文本已填充到下方。</p>
          <p v-if="fileError" class="file-status is-error">{{ fileError }}</p>
        </div>
        <div class="field">
          <textarea
            v-model="text"
            class="textarea textarea-tall"
            placeholder="直接粘贴或输入文本，统计会立即更新…"
            aria-label="待统计文本"
            @input="onInput"
          ></textarea>
          <div class="tool-text-meta">
            <span class="tool-tip">按 Unicode 码点统计，换行计为 1 个字符；组合 emoji 可能计为多个。</span>
            <button class="text-button" type="button" @click="fillExample">填入示例</button>
          </div>
          <div v-if="overLimit" class="mini-alert danger">
            <AppIcon name="alert" :size="13" />
            <span>文本超过 2MB 上限（当前 {{ (bytes / 1024 / 1024).toFixed(2) }}MB），请缩短后再统计。</span>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 实时统计</span>
          <span v-if="hasContent" class="badge badge-local">前端</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="!hasContent" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="chart" :size="21" /></span>
            <strong>等待输入</strong>
            <p>输入或粘贴文本后，这里会实时显示统计结果。内容不会离开浏览器。</p>
          </div>
          <template v-else>
            <div class="stat-grid">
              <div v-for="item in statItems" :key="item.label" class="stat-item">
                <span>{{ item.label }}</span>
                <strong>{{ item.value.toLocaleString('zh-CN') }}</strong>
              </div>
            </div>
            <div class="reading-line">
              <span>阅读时长</span>
              <strong class="serif">{{ readingText }} <em>分钟</em></strong>
            </div>
            <p class="tool-tip reading-note">按 汉字数 ÷ 300 + 英文单词数 ÷ 200 估算，仅作参考。</p>
            <div class="run-actions" style="margin-top: 14px">
              <button class="button button-ghost button-sm" type="button" @click="copySummary">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : '复制统计摘要' }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.tool-text-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.file-import {
  margin-bottom: 16px;
}

.file-status {
  margin-top: 7px;
  color: var(--faint);
  font-size: 10.5px;
}

.file-status.is-error {
  color: var(--danger);
}

.reading-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 11px 13px;
  border-radius: 9px;
  background: var(--surface-2);
  color: var(--muted);
  font-size: 11.5px;
}

.reading-line strong {
  color: var(--ink);
  font-size: 21px;
  font-weight: 600;
}

.reading-line em {
  font-family: var(--font-ui);
  font-size: 10px;
  font-style: normal;
  font-weight: 400;
  color: var(--faint);
}

.reading-note {
  margin-top: 6px;
}
</style>
