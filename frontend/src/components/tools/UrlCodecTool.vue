<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { formatBytes } from '@/utils/format'
import { decodeUrlText, encodeUrlText } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const mode = ref<'component' | 'form' | 'decode'>('component')
const keepReserved = ref(false)
const text = ref('')
const output = ref('')
const error = ref('')
const ran = ref(false)
const startedAt = ref(0)

const bytes = computed(() => new TextEncoder().encode(text.value).length)
const overLimit = computed(() => bytes.value > 2 * 1024 * 1024)
const isDecode = computed(() => mode.value === 'decode')
const buttonLabel = computed(() => (isDecode.value ? '开始解码' : '开始编码'))

watch(mode, () => {
  ran.value = false
  output.value = ''
  error.value = ''
})

function run() {
  error.value = ''
  output.value = ''
  ran.value = true
  try {
    if (!text.value.trim()) throw new Error('请输入要处理的内容')
    if (overLimit.value) throw new Error('文本超过 2MB 上限，请缩短后再处理')
    output.value = isDecode.value
      ? decodeUrlText(text.value, 'component')
      : mode.value === 'form'
        ? encodeUrlText(text.value, 'form', keepReserved.value)
        : encodeUrlText(text.value, 'component', keepReserved.value)
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

async function copyOutput() {
  await copy(output.value)
}

function fillExample() {
  text.value = isDecode.value
    ? 'https%3A%2F%2Fexample.com%2Fsearch%3Fq%3D%E5%B7%A5%E5%85%B7%E7%AE%B1%26from%3Dhome'
    : 'https://example.com/search?q=工具箱&from=home'
  ran.value = false
  output.value = ''
  error.value = ''
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>内容</h2>
          </div>
          <span class="section-aside">{{ formatBytes(bytes) }} / 2 MB</span>
        </div>
        <div class="field">
          <textarea
            v-model="text"
            class="textarea textarea-tall"
            :placeholder="isDecode ? '粘贴 URL 编码内容…' : '输入要编码的文本或 URL…'"
            aria-label="URL 编解码输入"
            spellcheck="false"
          ></textarea>
          <div class="tool-text-meta">
            <span class="tool-tip">不自动判断文本是否像 URL，模式由你选择。</span>
            <button class="text-button" type="button" @click="fillExample">填入示例</button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>模式</h2>
          </div>
        </div>
        <div class="segmented" role="group" aria-label="URL 编码模式">
          <button type="button" :class="{ 'is-active': mode === 'component' }" @click="mode = 'component'">组件编码</button>
          <button type="button" :class="{ 'is-active': mode === 'form' }" @click="mode = 'form'">表单编码</button>
          <button type="button" :class="{ 'is-active': mode === 'decode' }" @click="mode = 'decode'">解码</button>
        </div>
        <div v-if="!isDecode" class="inline-options option-gap">
          <label class="checkbox">
            <input v-model="keepReserved" type="checkbox" />
            保留 :/?#[]@!$&’()*+,;= 等保留字符（适合整段 URL）
          </label>
        </div>
        <p class="tool-tip option-gap">
          {{ isDecode ? '遇到不完整的百分号序列会拒绝，并指出错误位置。' : mode === 'form' ? '表单编码会将空格转换为 +，适合查询参数。' : '组件编码等同 encodeURIComponent，适合参数片段。' }}
        </p>
        <div class="run-bar">
          <p class="run-note">结果可复制，不会自动打开任何链接。</p>
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
          <span v-if="error" class="badge badge-danger">失败</span>
          <span v-else-if="output" class="badge badge-local">完成</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="!ran" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="file" :size="21" /></span>
            <strong>等待输入</strong>
            <p>输入内容并选择模式后，编码或解码结果会显示在这里。</p>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else>
            <textarea class="text-output" readonly :value="output" aria-label="URL 编解码结果" spellcheck="false"></textarea>
            <div class="result-toolbar" style="margin-top: 12px">
              <button class="button button-ghost button-sm" type="button" @click="copyOutput">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : '复制结果' }}
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

.option-gap {
  margin-top: 14px;
}
</style>
