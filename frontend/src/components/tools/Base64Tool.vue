<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { formatBytes } from '@/utils/format'
import { downloadText } from '@/utils/files'
import { decodeBase64Text, encodeBase64Text, fileToBase64 } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const source = ref<'text' | 'file'>('text')
const direction = ref<'encode' | 'decode'>('encode')
const urlSafe = ref(false)
const dataUri = ref(false)
const text = ref('')
const files = ref<File[]>([])
const output = ref('')
const error = ref('')
const ran = ref(false)
const processing = ref(false)
const startedAt = ref(0)

const textBytes = computed(() => new TextEncoder().encode(text.value).length)
const overLimit = computed(() => textBytes.value > 2 * 1024 * 1024)
const canRun = computed(() => {
  if (source.value === 'file') {
    if (direction.value === 'decode') return false
    return files.value.length === 1
  }
  return Boolean(text.value.trim())
})

watch(source, () => {
  if (source.value === 'file') direction.value = 'encode'
  ran.value = false
  output.value = ''
  error.value = ''
})

watch(direction, () => {
  ran.value = false
  output.value = ''
  error.value = ''
})

async function run() {
  if (!canRun.value || processing.value) return
  processing.value = true
  error.value = ''
  output.value = ''
  ran.value = true
  if (!startedAt.value) startedAt.value = performance.now()
  try {
    if (source.value === 'file') {
      const file = files.value[0]
      if (file.size > props.tool.max_file_mb! * 1024 * 1024) {
        throw new Error(`文件超过 ${props.tool.max_file_mb}MB 上限`)
      }
      output.value = await fileToBase64(file, urlSafe.value, dataUri.value)
    } else if (direction.value === 'encode') {
      if (overLimit.value) throw new Error('文本超过 2MB 上限，请缩短后再编码')
      output.value = encodeBase64Text(text.value, urlSafe.value)
    } else {
      output.value = decodeBase64Text(text.value, urlSafe.value)
    }
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - startedAt.value),
      file_count: source.value === 'file' ? 1 : 0,
      total_size: source.value === 'file' ? files.value[0]?.size ?? 0 : 0,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    void reportUsage({
      tool_code: props.tool.code,
      result: 'failed',
      duration_ms: Math.round(performance.now() - startedAt.value),
      error_code: 'E1-400',
    })
  } finally {
    processing.value = false
  }
}

async function copyOutput() {
  await copy(output.value)
}

function download() {
  downloadText('base64.txt', output.value)
}

function fillExample() {
  if (direction.value === 'encode') {
    text.value = '随手工具箱 · Base64 编解码'
  } else {
    text.value = '5L6/5omL5bel5YW3566xIMK3IEJhc2U2NCDnvJbor5HnoIEx'
  }
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
          <span class="section-aside">文本上限 2MB · 文件上限 {{ tool.max_file_mb }}MB</span>
        </div>

        <div class="segmented mode-row" role="group" aria-label="输入来源">
          <button type="button" :class="{ 'is-active': source === 'text' }" @click="source = 'text'">文本</button>
          <button type="button" :class="{ 'is-active': source === 'file' }" :disabled="direction === 'decode'" @click="source = 'file'">
            文件
          </button>
        </div>

        <template v-if="source === 'text'">
          <div class="field">
            <textarea
              v-model="text"
              class="textarea textarea-tall"
              :placeholder="direction === 'encode' ? '输入要编码的文本…' : '粘贴 Base64 字符串…'"
              aria-label="Base64 输入"
              spellcheck="false"
            ></textarea>
            <div class="tool-text-meta">
              <span class="tool-tip">当前 {{ formatBytes(textBytes) }}；解码自动补齐填充符，不做部分解码。</span>
              <button class="text-button" type="button" @click="fillExample">填入示例</button>
            </div>
          </div>
        </template>
        <FilePicker
          v-else
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          accept=""
          title="选择要转换为 Base64 的文件"
          hint="文件只在浏览器内读取，不上传；结果可下载为 TXT"
          :disabled="direction === 'decode'"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>选项</h2>
          </div>
        </div>
        <div class="field">
          <span class="field-label"><strong>方向</strong></span>
          <div class="segmented">
            <button type="button" :class="{ 'is-active': direction === 'encode' }" @click="direction = 'encode'">编码</button>
            <button type="button" :class="{ 'is-active': direction === 'decode' }" @click="direction = 'decode'">解码</button>
          </div>
        </div>
        <div class="inline-options option-gap">
          <label class="checkbox">
            <input v-model="urlSafe" type="checkbox" />
            URL-safe（+ / 替换为 - _）
          </label>
          <label v-if="source === 'file' && direction === 'encode'" class="checkbox">
            <input v-model="dataUri" type="checkbox" />
            输出 data URI 前缀
          </label>
        </div>
        <div class="run-bar">
          <p class="run-note">
            <template v-if="source === 'file'">文件按每 76 字符换行输出，便于粘贴到邮件或配置中。</template>
            <template v-else>文本按 UTF-8 编解码，结果只存在当前页面内存。</template>
          </p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!canRun || processing || overLimit" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ processing ? '处理中…' : direction === 'encode' ? '开始编码' : '开始解码' }}
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
            <p>选择文本或文件并开始处理后，结果会显示在这里。</p>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else>
            <div class="metric-line">
              <span>输出长度</span>
              <span>{{ output.length.toLocaleString('zh-CN') }} 字符</span>
            </div>
            <textarea class="text-output" readonly :value="output" aria-label="Base64 结果" spellcheck="false"></textarea>
            <div class="result-toolbar" style="margin-top: 12px">
              <button class="button button-ghost button-sm" type="button" @click="copyOutput">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : '复制结果' }}
              </button>
              <button class="button button-soft button-sm" type="button" @click="download">
                <AppIcon name="download" :size="13" />
                下载 TXT
              </button>
            </div>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.mode-row {
  margin-bottom: 15px;
}

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
