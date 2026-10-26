<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { useCopy } from '@/composables/useCopy'
import { useServerTask } from '@/composables/useServerTask'
import { useSite } from '@/composables/useSite'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'
import { formatDuration } from '@/utils/format'
import { downloadText } from '@/utils/files'
import { errorFeedbackPrefill, setFeedbackPrefill } from '@/utils/feedbackPrefill'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()
const { payload } = useSite()
const { copied, copy } = useCopy()
const router = useRouter()

const files = ref<File[]>([])
const language = ref('mixed')
const autoRotate = ref(true)
const outputMode = ref<'text' | 'markdown'>('text')
const preserveParagraphs = ref(true)
const edits = ref<Record<string, string>>({})
const activeIndex = ref(0)

const isServer = computed(() => props.tool.engine === 'server')
const task = computed(() => server.task.value)
const results = computed(() => task.value?.results ?? [])
const activeResult = computed(() => results.value[activeIndex.value] ?? null)

const canRun = computed(
  () => files.value.length > 0 && props.tool.available && accepted.value && !server.busy.value && isServer.value,
)
const hint = computed(() => {
  if (!files.value.length) return '请先添加至少 1 张图片'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!accepted.value) return '请先确认上传说明'
  return ''
})

const params = computed(() => ({
  language: language.value,
  auto_rotate: autoRotate.value,
  output: outputMode.value,
  preserve_paragraphs: preserveParagraphs.value,
}))

const combinedText = computed(() =>
  results.value.map((result) => `【${result.filename}】\n${edits.value[result.id] ?? result.text ?? ''}`).join('\n\n'),
)

const combinedMarkdown = computed(() =>
  results.value
    .map((result) => `## ${result.filename}\n\n${edits.value[result.id] ?? result.text ?? ''}`)
    .join('\n\n'),
)

watch(
  results,
  (value) => {
    const next: Record<string, string> = {}
    value.forEach((result) => {
      next[result.id] = result.text ?? ''
    })
    edits.value = next
    activeIndex.value = 0
  },
  { immediate: true },
)

onMounted(() => {
  if (isServer.value) void server.restore()
})

async function run() {
  if (!canRun.value) return
  await server.run(files.value, params.value, { isRetry: server.state.value === 'failed' })
}

async function copyCurrent() {
  if (activeResult.value) await copy(edits.value[activeResult.value.id] ?? activeResult.value.text ?? '')
}

async function copyAll() {
  await copy(combinedText.value)
}

function downloadTxt() {
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
  downloadText(`识别结果_${stamp}.txt`, combinedText.value)
}

function downloadMarkdown() {
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
  downloadText(`识别结果_${stamp}.md`, combinedMarkdown.value, 'text/markdown;charset=utf-8')
}

function goFeedback() {
  setFeedbackPrefill(
    errorFeedbackPrefill(
      props.tool.code,
      server.error.value ?? {
        status: null,
        message: '',
        code: task.value?.failures[0]?.code,
        taskId: task.value?.task_id,
      },
      `/t/${props.tool.slug}`,
    ),
  )
  void router.push('/feedback')
}

function askDelete() {
  if (window.confirm('删除识别结果后不可恢复。确定删除？')) {
    void server.removeResults()
  }
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>上传图片</h2>
          </div>
          <span class="section-aside">{{ files.length }} / {{ tool.max_count }} 张</span>
        </div>
        <FilePicker
          v-model="files"
          multiple
          :max-count="tool.max_count"
          :max-file-mb="tool.max_file_mb"
          accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/heic,image/heif,image/*"
          title="拖拽图片到这里，或点击选择"
          :hint="`JPG · PNG · WebP · BMP · TIFF · HEIC · 单张上限 ${tool.max_file_mb}MB · 最多 ${tool.max_count} 张`"
          :disabled="!tool.available"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>识别参数</h2>
          </div>
        </div>
        <div class="param-grid">
          <div class="field">
            <span class="field-label"><strong>语言</strong></span>
            <select v-model="language" class="select">
              <option value="mixed">中英混排（默认）</option>
              <option value="zh-CN">简体中文</option>
              <option value="zh-TW">繁体中文</option>
              <option value="en">英文</option>
            </select>
          </div>
          <div class="field">
            <span class="field-label"><strong>输出</strong></span>
            <select v-model="outputMode" class="select">
              <option value="text">纯文本</option>
              <option value="markdown">Markdown</option>
            </select>
          </div>
          <div class="field">
            <span class="field-label"><strong>处理选项</strong></span>
            <label class="checkbox"><input v-model="autoRotate" type="checkbox" /> 自动旋转</label>
          </div>
          <div class="field">
            <span class="field-label"><strong>段落</strong></span>
            <label class="checkbox"><input v-model="preserveParagraphs" type="checkbox" /> 保留段落换行</label>
          </div>
        </div>

        <div class="mini-alert option-gap">
          <AppIcon name="alert" :size="14" />
          <span>识别结果需人工校对，不承诺准确率。</span>
        </div>

        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>

        <div class="run-bar">
          <p class="run-note">上传完成后进入处理，开始识别后显示已处理张数。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="scan" :size="15" />
              {{ server.busy.value ? '识别中…' : '开始识别' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 识别文本</span>
          <span v-if="server.error.value" class="badge badge-danger">失败</span>
          <span v-else-if="server.state.value === 'partial'" class="badge badge-warn">部分成功</span>
          <span v-else-if="task && results.length" class="badge badge-success">完成</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body">
          <div v-if="server.restoring.value" class="local-processing">
            <AppIcon name="refresh" :size="18" class="spin" />
            <span>正在恢复上次任务…</span>
          </div>

          <div v-else-if="server.state.value === 'uploading'" class="local-processing">
            <AppIcon name="upload" :size="18" />
            <span>正在上传 {{ server.progress.value }}%…</span>
          </div>

          <div v-else-if="server.state.value === 'processing'" class="local-processing">
            <AppIcon name="refresh" :size="18" class="spin" />
            <span>服务端正在识别…</span>
          </div>

          <div v-else-if="server.error.value" class="ocr-error" role="alert">
            <div class="error-title">
              <AppIcon name="alert" :size="15" />
              <strong>{{ server.error.value.code ? `识别失败（${server.error.value.code}）` : '识别失败' }}</strong>
            </div>
            <p>{{ server.error.value.message }}</p>
            <div class="error-actions">
              <button class="button button-ghost button-sm" type="button" @click="run">重试</button>
              <button v-if="payload?.site.feedback_enabled !== false" class="text-button" type="button" @click="goFeedback">反馈此问题</button>
            </div>
          </div>

          <div v-else-if="!task" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="scan" :size="21" /></span>
            <strong>等待输入</strong>
            <p>上传图片并开始识别后，按图片分标签展示可编辑文本。</p>
          </div>

          <template v-else>
            <div class="ocr-summary">
              <strong>
                {{ task.status === 'succeeded' ? '识别完成' : task.status === 'partial' ? '部分图片未成功' : task.status === 'expired' ? '结果已过期' : '识别结束' }}
              </strong>
              <span class="mono">{{ task.file_count }} 张 · 用时 {{ formatDuration(task.duration_ms) }}</span>
            </div>

            <ul v-if="task.failures.length" class="ocr-failures" role="alert">
              <li v-for="(failure, index) in task.failures" :key="index">
                <span class="mono">{{ failure.code }}</span> {{ failure.message }}
              </li>
            </ul>

            <template v-if="results.length">
              <div class="ocr-tabs">
                <button
                  v-for="(result, index) in results"
                  :key="result.id"
                  type="button"
                  :class="{ 'is-active': activeIndex === index }"
                  @click="activeIndex = index"
                >
                  {{ result.filename }}
                </button>
              </div>
              <textarea
                v-if="activeResult"
                v-model="edits[activeResult.id]"
                class="text-output ocr-textarea"
                aria-label="识别文本"
                spellcheck="false"
              ></textarea>
              <div class="result-toolbar" style="margin-top: 10px">
                <button class="button button-ghost button-sm" type="button" @click="copyCurrent">
                  <AppIcon name="copy" :size="13" />
                  {{ copied ? '已复制' : '复制当前' }}
                </button>
                <button class="button button-ghost button-sm" type="button" @click="copyAll">
                  <AppIcon name="copy" :size="13" />
                  复制全部
                </button>
                <button class="button button-soft button-sm" type="button" @click="downloadTxt">
                  <AppIcon name="download" :size="13" />
                  TXT
                </button>
                <button class="button button-soft button-sm" type="button" @click="downloadMarkdown">
                  <AppIcon name="download" :size="13" />
                  Markdown
                </button>
              </div>
              <div class="ocr-footer">
                <button class="text-button" type="button" @click="askDelete">删除结果</button>
              </div>
            </template>

            <div v-else-if="task.status === 'expired'" class="mini-alert danger" style="margin-top: 10px">
              <AppIcon name="clock" :size="14" />
              <span>结果已过期或不可用，请重新识别。</span>
            </div>

            <div class="failure-actions">
              <button class="button button-ghost button-sm" type="button" @click="run">
                <AppIcon name="refresh" :size="13" />
                重新识别
              </button>
              <button v-if="payload?.site.feedback_enabled !== false" class="text-button" type="button" @click="goFeedback">反馈此问题</button>
            </div>
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

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}

.local-processing {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 20px 4px;
  color: var(--muted);
  font-size: 12px;
}

.ocr-error {
  padding: 6px 2px;
}

.error-title {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--danger);
  font-size: 12px;
}

.ocr-error p {
  margin-top: 8px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.error-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.ocr-summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
}

.ocr-summary strong {
  font-size: 12.5px;
}

.ocr-summary span {
  color: var(--faint);
  font-size: 9px;
}

.ocr-failures {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 10px;
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 10.5px;
  line-height: 1.55;
}

.ocr-tabs {
  display: flex;
  gap: 4px;
  margin: 10px 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.ocr-tabs::-webkit-scrollbar {
  display: none;
}

.ocr-tabs button {
  flex: none;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 5px 9px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--muted);
  font-size: 10.5px;
}

.ocr-tabs button.is-active {
  border-color: var(--ink-2);
  background: var(--surface);
  color: var(--ink);
}

.ocr-textarea {
  min-height: 240px;
  max-height: 380px;
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.75;
}

.ocr-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 11px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}

.expiry-note {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--faint);
  font-size: 9.5px;
}

.failure-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
</style>
