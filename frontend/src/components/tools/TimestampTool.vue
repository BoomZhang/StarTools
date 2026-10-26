<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { convertTimestamp, type TimeResult } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const unit = ref<'auto' | 's' | 'ms'>('auto')
const input = ref('')
const result = ref<TimeResult | null>(null)
const error = ref('')
const ran = ref(false)
const now = ref(new Date())
const startedAt = ref(0)
let timer: number | undefined

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
})

const currentSeconds = computed(() => Math.floor(now.value.getTime() / 1000))
const currentMs = computed(() => now.value.getTime())
const currentLocal = computed(() =>
  now.value.toLocaleString('zh-CN', { hour12: false }),
)
const timezone = computed(() => Intl.DateTimeFormat().resolvedOptions().timeZone || '本地时区')

const fields = computed(() => {
  if (!result.value) return []
  return [
    { label: '本地时间', value: result.value.local },
    { label: 'UTC 时间', value: result.value.utc },
    { label: 'ISO 8601', value: result.value.iso },
    { label: '秒级时间戳', value: String(result.value.timestampSeconds) },
    { label: '毫秒级时间戳', value: String(result.value.timestampMs) },
    { label: '浏览器时区', value: result.value.timezone },
  ]
})

function useCurrent() {
  input.value = unit.value === 'ms' ? String(currentMs.value) : String(currentSeconds.value)
  if (unit.value === 'auto') input.value = String(currentSeconds.value)
}

function run() {
  error.value = ''
  result.value = null
  ran.value = true
  try {
    result.value = convertTimestamp(input.value, unit.value)
    if (!startedAt.value) startedAt.value = performance.now()
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - startedAt.value),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    void reportUsage({
      tool_code: props.tool.code,
      result: 'failed',
      duration_ms: Math.round(performance.now() - (startedAt.value || performance.now())),
      error_code: 'E1-400',
    })
  }
}

function fillExample() {
  input.value = '1717171717'
  unit.value = 'auto'
  ran.value = false
  result.value = null
  error.value = ''
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / NOW</span>
            <h2>当前时间</h2>
          </div>
          <span class="section-aside">{{ timezone }}</span>
        </div>
        <div class="now-card">
          <div>
            <span class="mono-label">LOCAL</span>
            <strong class="mono">{{ currentLocal }}</strong>
          </div>
          <div class="now-stamps">
            <span>秒 <code>{{ currentSeconds }}</code></span>
            <span>毫秒 <code>{{ currentMs }}</code></span>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / INPUT</span>
            <h2>时间戳或日期</h2>
          </div>
        </div>
        <div class="field">
          <div class="input-row">
            <input v-model="input" class="input input-mono" placeholder="例如 1717171717 或 2026-10-23 17:42:00" aria-label="时间戳或日期" />
            <button class="button button-soft" type="button" @click="useCurrent">使用当前时间</button>
          </div>
          <div class="inline-options">
            <span class="field-label"><strong>单位</strong></span>
            <div class="segmented">
              <button type="button" :class="{ 'is-active': unit === 'auto' }" @click="unit = 'auto'">自动</button>
              <button type="button" :class="{ 'is-active': unit === 's' }" @click="unit = 's'">秒</button>
              <button type="button" :class="{ 'is-active': unit === 'ms' }" @click="unit = 'ms'">毫秒</button>
            </div>
            <button class="text-button" type="button" @click="fillExample">填入示例</button>
          </div>
        </div>
        <div class="run-bar">
          <p class="run-note">有效范围 1970-01-01 至 2100-12-31；非法日期会就地提示，不自动纠正。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!input.trim()" @click="run">
              <AppIcon name="clock" :size="15" />
              开始转换
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 时间</span>
          <span v-if="error" class="badge badge-danger">失败</span>
          <span v-else-if="result" class="badge badge-local">完成</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="!ran" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="clock" :size="21" /></span>
            <strong>等待输入</strong>
            <p>输入时间戳或日期，转换成可复制的本地时间、UTC 与 ISO 8601。</p>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else-if="result">
            <div v-for="field in fields" :key="field.label" class="time-row">
              <span>{{ field.label }}</span>
              <code>{{ field.value }}</code>
              <button type="button" class="mini-copy" aria-label="复制" @click="copy(field.value)">
                <AppIcon name="copy" :size="12" />
              </button>
            </div>
            <p v-if="copied" class="tool-tip copy-note">已复制到剪贴板</p>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.now-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 15px 16px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
  flex-wrap: wrap;
}

.now-card > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.now-card .mono-label {
  color: var(--faint);
  font-size: 8.5px;
}

.now-card strong {
  font-size: 15px;
  font-weight: 500;
}

.now-stamps {
  gap: 6px !important;
  color: var(--faint);
  font-size: 10.5px;
}

.now-stamps code {
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: 10px;
}

.field > .inline-options {
  margin-top: 12px;
}

.time-row {
  display: grid;
  grid-template-columns: 90px 1fr 24px;
  align-items: center;
  gap: 9px;
  padding: 9px 0;
  border-bottom: 1px dashed rgba(217, 211, 196, 0.7);
}

.time-row:last-of-type {
  border-bottom: 0;
}

.time-row > span {
  color: var(--faint);
  font-size: 10.5px;
}

.time-row code {
  overflow-wrap: anywhere;
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 1.5;
}

.mini-copy {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--surface);
  color: var(--faint);
}

.mini-copy:hover {
  color: var(--ink);
  border-color: var(--ink-2);
}

.copy-note {
  margin-top: 8px;
}
</style>
