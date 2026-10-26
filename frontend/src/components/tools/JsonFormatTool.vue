<script setup lang="ts">
import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { formatBytes } from '@/utils/format'
import { downloadText } from '@/utils/files'
import { transformJson } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const text = ref('')
const mode = ref<'pretty' | 'minify' | 'validate' | 'escape' | 'unescape'>('pretty')
const indent = ref<2 | 4 | 'tab'>(2)
const output = ref('')
const error = ref<{ message: string; line?: number; column?: number; hint?: string } | null>(null)
const nodes = ref<number | null>(null)
const ran = ref(false)
const startedAt = ref(0)

const modes = [
  { key: 'pretty', label: '美化' },
  { key: 'minify', label: '压缩' },
  { key: 'validate', label: '校验' },
  { key: 'escape', label: '转义' },
  { key: 'unescape', label: '去转义' },
] as const

const bytes = computed(() => new TextEncoder().encode(text.value).length)
const overLimit = computed(() => bytes.value > 2 * 1024 * 1024)

const buttonLabel = computed(() => {
  const labels: Record<string, string> = {
    pretty: '开始美化',
    minify: '开始压缩',
    validate: '开始校验',
    escape: '开始转义',
    unescape: '开始去转义',
  }
  return labels[mode.value]
})

const errorLocation = computed(() => {
  if (!error.value?.line) return ''
  return `第 ${error.value.line} 行${error.value.column ? `，第 ${error.value.column} 列` : ''}`
})

function run() {
  error.value = null
  nodes.value = null
  output.value = ''
  ran.value = true
  if (overLimit.value) {
    error.value = { message: 'JSON 文本超过 2MB 上限，请缩短后再处理。' }
    return
  }
  const result = transformJson(text.value, mode.value, indent.value)
  if (result.error) {
    error.value = result.error
    return
  }
  output.value = result.output
  nodes.value = result.nodes ?? null
  if (!startedAt.value) startedAt.value = performance.now()
  if (mode.value !== 'validate') {
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - startedAt.value),
    })
  }
}

async function copyOutput() {
  await copy(output.value)
}

function download() {
  downloadText('formatted.json', output.value, 'application/json;charset=utf-8')
}

function fillExample() {
  text.value = '{"name":"随手工具箱","tools":39,"public":true,"tags":["图片","PDF","二维码"],"owner":{"role":"visitor","login":false}}'
  mode.value = 'pretty'
  ran.value = false
  output.value = ''
  error.value = null
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>JSON 文本</h2>
          </div>
          <span class="section-aside">{{ formatBytes(bytes) }} / 2 MB</span>
        </div>
        <div class="field">
          <textarea
            v-model="text"
            class="textarea textarea-tall"
            placeholder='粘贴 JSON，例如 {"name":"工具箱"}'
            aria-label="JSON 输入"
            spellcheck="false"
          ></textarea>
          <div class="tool-text-meta">
            <span class="tool-tip">不支持注释与尾随逗号；格式化与压缩必须点击按钮执行。</span>
            <button class="text-button" type="button" @click="fillExample">填入示例</button>
          </div>
          <div v-if="overLimit" class="mini-alert danger">
            <AppIcon name="alert" :size="13" />
            <span>超过 2MB 上限（当前 {{ formatBytes(bytes) }}），请缩短后再处理。</span>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / ACTIONS</span>
            <h2>处理方式</h2>
          </div>
        </div>
        <div class="segmented" role="group" aria-label="处理方式">
          <button
            v-for="item in modes"
            :key="item.key"
            type="button"
            :class="{ 'is-active': mode === item.key }"
            @click="mode = item.key"
          >
            {{ item.label }}
          </button>
        </div>
        <div v-if="mode === 'pretty'" class="field indent-field">
          <span class="field-label"><strong>缩进</strong></span>
          <div class="segmented">
            <button type="button" :class="{ 'is-active': indent === 2 }" @click="indent = 2">2 空格</button>
            <button type="button" :class="{ 'is-active': indent === 4 }" @click="indent = 4">4 空格</button>
            <button type="button" :class="{ 'is-active': indent === 'tab' }" @click="indent = 'tab'">Tab</button>
          </div>
        </div>
        <div class="run-bar">
          <p class="run-note">
            <template v-if="mode === 'validate'">校验只读取内容，不会改写原文。</template>
            <template v-else-if="mode === 'escape' || mode === 'unescape'">转义作用于整段输入文本，不递归处理对象内部。</template>
            <template v-else>输出在右侧只读展示，可复制或下载 .json。</template>
          </p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!text.trim() || overLimit" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ buttonLabel }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 输出</span>
          <span v-if="error" class="badge badge-danger">校验失败</span>
          <span v-else-if="output" class="badge badge-success">完成</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="!ran" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="file" :size="21" /></span>
            <strong>等待输入</strong>
            <p>输入 JSON 并点击处理按钮，结果、节点数与错误位置会显示在这里。</p>
          </div>

          <div v-else-if="error" class="json-error" role="alert">
            <div class="error-title">
              <AppIcon name="alert" :size="15" />
              <strong>无法处理这段 JSON</strong>
            </div>
            <p>{{ error.message }}</p>
            <p v-if="errorLocation" class="mono error-location">{{ errorLocation }}</p>
            <p v-if="error.hint" class="tool-tip">{{ error.hint }}</p>
          </div>

          <template v-else>
            <div v-if="nodes !== null" class="metric-line">
              <span>JSON 节点数</span>
              <span>{{ nodes }}</span>
            </div>
            <textarea
              v-if="mode !== 'validate'"
              class="text-output json-output"
              readonly
              :value="output"
              aria-label="处理结果"
              spellcheck="false"
            ></textarea>
            <div v-else class="mini-alert info">
              <AppIcon name="check-circle" :size="14" />
              <span>校验通过，共 {{ nodes }} 个节点。</span>
            </div>
            <div v-if="mode !== 'validate'" class="result-toolbar" style="margin-top: 12px">
              <button class="button button-ghost button-sm" type="button" @click="copyOutput">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : '复制结果' }}
              </button>
              <button v-if="mode === 'pretty' || mode === 'minify'" class="button button-soft button-sm" type="button" @click="download">
                <AppIcon name="download" :size="13" />
                下载 .json
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

.indent-field {
  margin-top: 14px;
}

.json-error {
  padding: 13px;
  border-radius: 9px;
  background: var(--danger-soft);
  color: var(--danger);
}

.error-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
}

.json-error p {
  margin-top: 8px;
  font-size: 11.5px;
  line-height: 1.65;
}

.error-location {
  font-size: 10px;
  opacity: 0.85;
}

.json-output {
  min-height: 240px;
  max-height: 380px;
  background: var(--surface-2);
}
</style>
