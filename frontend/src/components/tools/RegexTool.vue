<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'

interface MatchItem {
  value: string
  index: number
  groups: string[]
}

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const pattern = ref('')
const text = ref('')
const replacement = ref('')
const flags = ref<Record<string, boolean>>({ g: true, i: false, m: false, s: false, u: false, y: false })
const matches = ref<MatchItem[] | null>(null)
const replaced = ref('')
const error = ref('')
const timedOut = ref(false)
const running = ref(false)
const startedAt = ref(0)
let worker: Worker | null = null
let timer: number | undefined

const flagString = computed(
  () =>
    Object.entries(flags.value)
      .filter(([, enabled]) => enabled)
      .map(([flag]) => flag)
      .join(''),
)
const canRun = computed(() => pattern.value.length > 0 && !running.value)

onBeforeUnmount(() => {
  worker?.terminate()
  window.clearTimeout(timer)
})

function run() {
  if (!canRun.value) return
  error.value = ''
  timedOut.value = false
  matches.value = null
  replaced.value = ''
  running.value = true
  if (!startedAt.value) startedAt.value = performance.now()

  worker?.terminate()
  worker = new Worker(new URL('../../workers/regex.worker.ts', import.meta.url), { type: 'module' })
  const current = worker
  timer = window.setTimeout(() => {
    current.terminate()
    running.value = false
    timedOut.value = true
    error.value = '执行超过 1 秒，已自动中止。请检查是否存在灾难性回溯。'
  }, 1000)

  current.onmessage = (event: MessageEvent) => {
    window.clearTimeout(timer)
    running.value = false
    const payload = event.data as {
      ok: boolean
      matches?: MatchItem[]
      replaced?: string
      error?: string
    }
    if (!payload.ok) {
      error.value = payload.error || '正则表达式不合法'
      return
    }
    matches.value = payload.matches ?? []
    replaced.value = payload.replaced ?? ''
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - startedAt.value),
    })
  }
  current.onerror = () => {
    window.clearTimeout(timer)
    running.value = false
    error.value = '正则执行失败，请检查表达式'
  }

  current.postMessage({
    pattern: pattern.value,
    flags: flagString.value,
    text: text.value,
    replacement: replacement.value,
  })
}

async function copyReplaced() {
  await copy(replaced.value)
}

function fillExample() {
  pattern.value = '(\\w+)@(\\w+\\.\\w+)'
  flags.value = { g: true, i: false, m: false, s: false, u: false, y: false }
  text.value = '联系我们：hello@example.com 或 support@startools.dev'
  replacement.value = '$1 [at] $2'
  matches.value = null
  replaced.value = ''
  error.value = ''
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / PATTERN</span>
            <h2>正则表达式</h2>
          </div>
        </div>
        <div class="regex-pattern">
          <span class="regex-slash">/</span>
          <input v-model="pattern" class="input input-mono regex-input" placeholder="例如 (\w+)@(\w+\.\w+)" spellcheck="false" />
          <span class="regex-slash">/</span>
          <span class="regex-flags mono">{{ flagString || '—' }}</span>
        </div>
        <div class="flag-row">
          <label v-for="key in Object.keys(flags)" :key="key" class="checkbox">
            <input v-model="flags[key]" type="checkbox" />
            {{ key }}
          </label>
          <button class="text-button" type="button" @click="fillExample">填入示例</button>
        </div>

        <div class="field option-gap">
          <span class="field-label"><strong>测试文本</strong></span>
          <textarea v-model="text" class="textarea" rows="6" placeholder="粘贴要匹配的文本…" spellcheck="false"></textarea>
        </div>
        <div class="field">
          <span class="field-label"><strong>替换为</strong><span>支持 $1、$&amp;</span></span>
          <input v-model="replacement" class="input input-mono" placeholder="留空则不生成替换预览" />
        </div>
        <div class="run-bar">
          <p class="run-note">单次执行超过 1 秒会自动中止，避免灾难性回溯卡住页面。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="search" :size="15" />
              {{ running ? '匹配中…' : '执行匹配' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 匹配结果</span>
          <span v-if="error" class="badge badge-danger">失败</span>
          <span v-else-if="matches" class="badge badge-local">{{ matches.length }} 处</span>
          <span v-else class="badge badge-neutral">等待执行</span>
        </div>
        <div class="local-result-body">
          <div v-if="!matches && !error" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="search" :size="21" /></span>
            <strong>等待执行</strong>
            <p>填写表达式与文本后点击执行，匹配项、分组与替换预览会显示在这里。</p>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else>
            <div class="match-summary">
              <strong>{{ matches?.length ?? 0 }} 处匹配</strong>
              <span class="mono">{{ flagString }}</span>
            </div>
            <ul v-if="matches?.length" class="match-list">
              <li v-for="(match, index) in matches.slice(0, 200)" :key="index">
                <span class="match-index mono">#{{ index + 1 }} @{{ match.index }}</span>
                <code class="match-value">{{ match.value }}</code>
                <span v-if="match.groups.length" class="match-groups">
                  分组：{{ match.groups.map((group, groupIndex) => `${groupIndex + 1}=${group || '∅'}`).join(' · ') }}
                </span>
              </li>
            </ul>
            <p v-else class="tool-tip">没有匹配到内容。</p>
            <template v-if="replacement">
              <div class="replacement-head">
                <span class="mono-label">REPLACEMENT</span>
                <button class="button button-ghost button-sm" type="button" @click="copyReplaced">
                  <AppIcon name="copy" :size="13" />
                  {{ copied ? '已复制' : '复制替换结果' }}
                </button>
              </div>
              <textarea class="text-output" readonly :value="replaced" spellcheck="false"></textarea>
            </template>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.regex-pattern {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-2);
}

.regex-pattern:focus-within {
  border-color: var(--ink-2);
  background: var(--surface);
}

.regex-slash {
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 15px;
}

.regex-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 4px;
  font-size: 12.5px;
}

.regex-input:focus {
  box-shadow: none;
  background: transparent;
}

.regex-flags {
  color: var(--accent-deep);
  font-size: 10px;
}

.flag-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 9px;
}

.flag-row .text-button {
  margin-left: auto;
}

.option-gap {
  margin-top: 14px;
}

.match-summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 9px;
  border-bottom: 1px dashed var(--line);
}

.match-summary strong {
  font-size: 12px;
}

.match-summary span {
  color: var(--faint);
  font-size: 9px;
}

.match-list {
  display: flex;
  flex-direction: column;
  max-height: 260px;
  overflow-y: auto;
}

.match-list li {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(217, 211, 196, 0.55);
}

.match-index {
  color: var(--faint);
  font-size: 8px;
}

.match-value {
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--ink-2);
}

.match-groups {
  color: var(--faint);
  font-size: 9px;
  line-height: 1.5;
}

.replacement-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 14px 0 7px;
}

.replacement-head .mono-label {
  color: var(--faint);
  font-size: 8px;
}
</style>
