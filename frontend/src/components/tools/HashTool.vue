<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { formatBytes } from '@/utils/format'
import { hashFile, hashText, type HashAlgorithm } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const source = ref<'text' | 'file'>('text')
const algorithm = ref<HashAlgorithm>('SHA-256')
const upper = ref(false)
const text = ref('')
const files = ref<File[]>([])
const output = ref('')
const error = ref('')
const ran = ref(false)
const hashing = ref(false)
const progress = ref(0)
const inputLength = ref(0)
const startedAt = ref(0)

const algorithms: HashAlgorithm[] = ['MD5', 'SHA-1', 'SHA-256', 'SHA-512']
const canRun = computed(() =>
  source.value === 'file' ? files.value.length === 1 : Boolean(text.value.trim()),
)
const warning = computed(() => algorithm.value === 'MD5' || algorithm.value === 'SHA-1')

watch([source, algorithm, upper], () => {
  ran.value = false
  output.value = ''
  error.value = ''
})

async function run() {
  if (!canRun.value || hashing.value) return
  hashing.value = true
  error.value = ''
  output.value = ''
  ran.value = true
  progress.value = 0
  if (!startedAt.value) startedAt.value = performance.now()
  try {
    if (source.value === 'file') {
      const file = files.value[0]
      if (file.size > (props.tool.max_file_mb ?? 200) * 1024 * 1024) {
        throw new Error(`文件超过 ${props.tool.max_file_mb}MB 上限`)
      }
      inputLength.value = file.size
      output.value = await hashFile(algorithm.value, file, upper.value, (percent) => {
        progress.value = percent
      })
    } else {
      if (new TextEncoder().encode(text.value).length > 2 * 1024 * 1024) {
        throw new Error('文本超过 2MB 上限，请缩短后再计算')
      }
      inputLength.value = new TextEncoder().encode(text.value).length
      output.value = await hashText(algorithm.value, text.value, upper.value)
      progress.value = 100
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
    hashing.value = false
  }
}

async function copyOutput() {
  await copy(output.value)
}

function fillExample() {
  text.value = '随手工具箱 · hash'
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
            <h2>计算对象</h2>
          </div>
          <span class="section-aside">文件上限 {{ tool.max_file_mb }}MB</span>
        </div>
        <div class="segmented mode-row" role="group" aria-label="输入来源">
          <button type="button" :class="{ 'is-active': source === 'text' }" @click="source = 'text'">文本</button>
          <button type="button" :class="{ 'is-active': source === 'file' }" @click="source = 'file'">文件</button>
        </div>
        <div v-if="source === 'text'" class="field">
          <textarea
            v-model="text"
            class="textarea"
            placeholder="输入要计算哈希的文本…"
            aria-label="哈希输入文本"
            spellcheck="false"
          ></textarea>
          <div class="tool-text-meta">
            <span class="tool-tip">文本只在浏览器内计算，不会发送到服务器。</span>
            <button class="text-button" type="button" @click="fillExample">填入示例</button>
          </div>
        </div>
        <FilePicker
          v-else
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          title="选择要计算哈希的文件"
          hint="文件分块读取，不上传；MD5 会在浏览器内流式计算"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>算法与格式</h2>
          </div>
        </div>
        <div class="segmented" role="group" aria-label="哈希算法">
          <button
            v-for="item in algorithms"
            :key="item"
            type="button"
            :class="{ 'is-active': algorithm === item }"
            @click="algorithm = item"
          >
            {{ item }}
          </button>
        </div>
        <div class="inline-options option-gap">
          <label class="checkbox">
            <input v-model="upper" type="checkbox" />
            输出大写
          </label>
        </div>
        <div v-if="warning" class="mini-alert danger option-gap">
          <AppIcon name="alert" :size="14" />
          <span>{{ algorithm }} 仅适合用于文件完整性校验，不用于密码存储或数字签名。</span>
        </div>
        <div v-if="hashing" class="hash-progress">
          <div class="progress-track"><span :style="{ width: `${progress}%` }"></span></div>
          <span class="mono">{{ progress }}%</span>
        </div>
        <div class="run-bar">
          <p class="run-note">文件哈希同时显示文件名与大小；结果可复制。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!canRun || hashing" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ hashing ? '计算中…' : '开始计算' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / {{ algorithm }}</span>
          <span v-if="error" class="badge badge-danger">失败</span>
          <span v-else-if="output" class="badge badge-local">完成</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="!ran" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="shield" :size="21" /></span>
            <strong>等待输入</strong>
            <p>选择文本或文件并开始计算后，{{ algorithm }} 结果会显示在这里。</p>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else>
            <div class="metric-line">
              <span>算法</span>
              <span>{{ algorithm }}</span>
            </div>
            <div class="metric-line">
              <span>输入长度</span>
              <span>{{ source === 'file' ? `${files[0]?.name} · ${formatBytes(inputLength)}` : `${inputLength} 字节` }}</span>
            </div>
            <div class="hash-value mono">{{ output }}</div>
            <div class="result-toolbar" style="margin-top: 12px">
              <button class="button button-ghost button-sm" type="button" @click="copyOutput">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : '复制哈希' }}
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

.hash-value {
  margin-top: 12px;
  padding: 12px;
  border-radius: 9px;
  background: #101613;
  color: #d7ded4;
  font-size: 11.5px;
  line-height: 1.7;
  word-break: break-all;
}

.hash-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.hash-progress .progress-track {
  flex: 1;
  height: 5px;
  border-radius: 999px;
  background: var(--paper-deep);
  overflow: hidden;
}

.hash-progress .progress-track span {
  display: block;
  height: 100%;
  background: var(--accent);
  transition: width 0.2s;
}

.hash-progress > span {
  color: var(--faint);
  font-size: 10px;
}
</style>
