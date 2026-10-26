<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import type { ApiErrorInfo } from '@/api/client'
import type { TaskState } from '@/composables/useServerTask'
import { useCopy } from '@/composables/useCopy'
import { useSite } from '@/composables/useSite'
import type { ServerTask, Tool } from '@/types'
import { formatDuration } from '@/utils/format'
import { downloadText } from '@/utils/files'
import { errorFeedbackPrefill, setFeedbackPrefill } from '@/utils/feedbackPrefill'

const props = defineProps<{
  tool: Tool
  task: ServerTask | null
  state: TaskState
  error: ApiErrorInfo | null
  restoring: boolean
}>()

const emit = defineEmits<{
  (event: 'retry'): void
  (event: 'delete'): void
}>()

const router = useRouter()
const { copied, copy } = useCopy()
const { payload } = useSite()
const edits = ref<Record<string, string>>({})
const activeIndex = ref(0)

const results = computed(() => props.task?.results ?? [])
const activeResult = computed(() => results.value[activeIndex.value] ?? null)
const combinedText = computed(() =>
  results.value.map((result) => `【${result.filename}】\n${edits.value[result.id] ?? result.text ?? ''}`).join('\n\n'),
)
const combinedMarkdown = computed(() =>
  results.value.map((result) => `## ${result.filename}\n\n${edits.value[result.id] ?? result.text ?? ''}`).join('\n\n'),
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

function isSrt(filename: string): boolean {
  return filename.toLowerCase().endsWith('.srt')
}

async function copyCurrent() {
  if (activeResult.value) await copy(edits.value[activeResult.value.id] ?? activeResult.value.text ?? '')
}

async function copyAll() {
  await copy(combinedText.value)
}

function downloadCurrent() {
  if (!activeResult.value) return
  const text = edits.value[activeResult.value.id] ?? activeResult.value.text ?? ''
  const mime = isSrt(activeResult.value.filename) ? 'application/x-subrip;charset=utf-8' : 'text/plain;charset=utf-8'
  downloadText(activeResult.value.filename, text, mime)
}

function downloadAllTxt() {
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
  downloadText(`${props.tool.name}_${stamp}.txt`, combinedText.value)
}

function downloadAllMarkdown() {
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
  downloadText(`${props.tool.name}_${stamp}.md`, combinedMarkdown.value, 'text/markdown;charset=utf-8')
}

function goFeedback() {
  setFeedbackPrefill(
    errorFeedbackPrefill(
      props.tool.code,
      props.error ?? {
        status: null,
        message: '',
        code: props.task?.failures[0]?.code,
        taskId: props.task?.task_id,
      },
      window.location.pathname,
    ),
  )
  void router.push('/feedback')
}

function askDelete() {
  if (window.confirm('删除结果后不可恢复。确定删除？')) emit('delete')
}
</script>

<template>
  <div class="local-result">
    <div class="local-result-head">
      <span class="mono-label">RESULT / 文本结果</span>
      <span v-if="error" class="badge badge-danger">失败</span>
      <span v-else-if="state === 'partial'" class="badge badge-warn">部分成功</span>
      <span v-else-if="task && results.length" class="badge badge-success">完成</span>
      <span v-else class="badge badge-neutral">等待输入</span>
    </div>
    <div class="local-result-body" aria-live="polite">
      <div v-if="restoring" class="local-processing">
        <AppIcon name="refresh" :size="18" class="spin" />
        <span>正在恢复上次任务…</span>
      </div>
      <div v-else-if="state === 'uploading'" class="local-processing">
        <AppIcon name="upload" :size="18" />
        <span>正在上传文件…</span>
      </div>
      <div v-else-if="state === 'processing'" class="local-processing">
        <AppIcon name="refresh" :size="18" class="spin" />
        <span>服务端正在处理…</span>
      </div>

      <div v-else-if="error" class="text-error" role="alert">
        <div class="error-title">
          <AppIcon name="alert" :size="15" />
          <strong>{{ error.code ? `处理失败（${error.code}）` : '处理失败' }}</strong>
        </div>
        <p>{{ error.message }}</p>
        <div class="error-actions">
          <button class="button button-ghost button-sm" type="button" @click="emit('retry')">重试</button>
          <button v-if="payload?.site.feedback_enabled !== false" class="text-button" type="button" @click="goFeedback">反馈此问题</button>
        </div>
      </div>

      <div v-else-if="!task" class="local-empty">
        <span class="local-empty-mark"><AppIcon name="file" :size="21" /></span>
        <strong>等待输入</strong>
        <p>开始处理后，可编辑的文本结果会显示在这里。</p>
      </div>

      <template v-else>
        <div class="text-summary">
          <strong>{{ task.status === 'succeeded' ? '处理完成' : task.status === 'partial' ? '部分完成' : '处理结束' }}</strong>
          <span class="mono">{{ task.file_count }} 个文件 · {{ formatDuration(task.duration_ms) }}</span>
        </div>

        <ul v-if="task.failures.length" class="text-failures">
          <li v-for="(failure, index) in task.failures" :key="index">
            <span class="mono">{{ failure.code }}</span> {{ failure.message }}
          </li>
        </ul>

        <template v-if="results.length">
          <div class="text-tabs">
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
            class="text-output text-editable"
            aria-label="文本结果"
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
            <button class="button button-soft button-sm" type="button" @click="downloadCurrent">
              <AppIcon name="download" :size="13" />
              下载当前
            </button>
            <button class="button button-soft button-sm" type="button" @click="downloadAllTxt">
              <AppIcon name="download" :size="13" />
              TXT
            </button>
            <button class="button button-soft button-sm" type="button" @click="downloadAllMarkdown">
              <AppIcon name="download" :size="13" />
              Markdown
            </button>
          </div>
          <div class="text-footer">
            <button class="text-button" type="button" @click="askDelete">删除结果</button>
          </div>
        </template>

        <div v-else class="mini-alert danger" style="margin-top: 10px">
          <AppIcon name="clock" :size="14" />
          <span>结果已过期或不可用，请重新处理。</span>
        </div>

        <p class="text-note">识别或转写结果需人工校对。</p>
        <div class="text-actions">
          <button class="button button-ghost button-sm" type="button" @click="emit('retry')">
            <AppIcon name="refresh" :size="13" />
            重新处理
          </button>
          <button v-if="payload?.site.feedback_enabled !== false" class="text-button" type="button" @click="goFeedback">反馈此问题</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.local-processing {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 20px 4px;
  color: var(--muted);
  font-size: 12px;
}

.text-error {
  padding: 6px 2px;
}

.error-title {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--danger);
  font-size: 12px;
}

.text-error p {
  margin-top: 8px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.error-actions,
.text-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.text-summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
}

.text-summary strong {
  font-size: 12.5px;
}

.text-summary span {
  color: var(--faint);
  font-size: 9px;
}

.text-failures {
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

.text-tabs {
  display: flex;
  gap: 4px;
  margin: 10px 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.text-tabs::-webkit-scrollbar {
  display: none;
}

.text-tabs button {
  flex: none;
  max-width: 190px;
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

.text-tabs button.is-active {
  border-color: var(--ink-2);
  background: var(--surface);
  color: var(--ink);
}

.text-editable {
  min-height: 240px;
  max-height: 380px;
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.75;
}

.text-footer {
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

.text-note {
  margin-top: 10px;
  color: var(--faint);
  font-size: 9.5px;
  line-height: 1.6;
}
</style>
