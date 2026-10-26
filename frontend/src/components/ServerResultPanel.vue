<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolBadge from '@/components/ToolBadge.vue'
import type { ApiErrorInfo } from '@/api/client'
import type { TaskState } from '@/composables/useServerTask'
import { useSite } from '@/composables/useSite'
import type { ServerTask, Tool } from '@/types'
import { formatBytes, formatDuration } from '@/utils/format'
import { errorFeedbackPrefill, setFeedbackPrefill } from '@/utils/feedbackPrefill'

const props = defineProps<{
  tool: Tool
  task: ServerTask | null
  state: TaskState
  progress: number
  error: ApiErrorInfo | null
  restoring: boolean
}>()

const emit = defineEmits<{
  (event: 'retry'): void
  (event: 'delete'): void
}>()

const router = useRouter()
const { payload } = useSite()

const statusText = computed(() => {
  if (props.state === 'uploading') return '上传中'
  if (props.state === 'processing') return '处理中'
  if (props.state === 'succeeded') return '处理完成'
  if (props.state === 'partial') return '部分成功'
  if (props.state === 'failed') return '处理失败'
  if (props.state === 'canceled') return '已取消'
  if (props.state === 'expired') return '结果已过期'
  return null
})

const statusClass = computed(() => {
  if (props.state === 'succeeded') return 'badge-success'
  if (props.state === 'partial') return 'badge-warn'
  if (props.state === 'failed' || props.state === 'expired') return 'badge-danger'
  return 'badge-neutral'
})

const showActions = computed(() => Boolean(props.task && props.task.results.length))

function metaSummary(meta: Record<string, unknown>, size: number): string {
  const parts: string[] = []
  if (meta.new_size && meta.original_size) {
    parts.push(`${formatBytes(Number(meta.original_size))} → ${formatBytes(Number(meta.new_size))}`)
  } else {
    parts.push(formatBytes(size))
  }
  const ratio = meta.ratio
  if (typeof ratio === 'number') {
    parts.push(ratio >= 0 ? `压缩 ${ratio}%` : `体积增加 ${Math.abs(ratio)}%`)
  }
  if (meta.width && meta.height) parts.push(`${meta.width}×${meta.height}`)
  else if (meta.original_width && meta.original_height) parts.push(`原 ${meta.original_width}×${meta.original_height}`)
  if (meta.pages) parts.push(`${meta.pages} 页`)
  if (meta.page) parts.push(`第 ${meta.page} 页`)
  if (meta.format) parts.push(String(meta.format).toUpperCase())
  if (meta.dpi) parts.push(`${meta.dpi} DPI`)
  if (meta.note) parts.push(String(meta.note))
  return parts.join(' · ')
}

function isImage(contentType: string): boolean {
  return contentType.startsWith('image/')
}

function isAudio(contentType: string): boolean {
  return contentType.startsWith('audio/')
}

function isVideo(contentType: string): boolean {
  return contentType.startsWith('video/')
}

function goFeedback() {
  const code = props.error?.code || props.task?.failures[0]?.code
  setFeedbackPrefill(
    errorFeedbackPrefill(
      props.tool.code,
      {
        status: null,
        message: '',
        code,
        taskId: props.task?.task_id || props.error?.taskId,
      },
      `/t/${props.tool.slug}`,
    ),
  )
  void router.push('/feedback')
}

function askDelete() {
  if (window.confirm('删除结果后不可恢复。确定删除？')) emit('delete')
}

function askRetry() {
  emit('retry')
}
</script>

<template>
  <div class="result-panel">
    <div class="result-head">
      <span class="result-head-left">
        <span class="mono-label">RESULT / 结果</span>
        <ToolBadge v-if="payload?.site.show_engine_badge !== false" :engine="tool.engine" />
      </span>
      <span v-if="statusText" class="badge" :class="statusClass">{{ statusText }}</span>
    </div>

    <div class="result-body" aria-live="polite">
      <div v-if="restoring" class="result-loading">
        <AppIcon name="refresh" :size="18" class="spin" />
        <span>正在恢复上次任务…</span>
      </div>

      <div v-else-if="state === 'idle'" class="result-empty">
        <span class="empty-mark"><AppIcon name="file" :size="22" /></span>
        <strong class="serif">等待输入</strong>
        <p>添加文件并确认参数后，结果会出现在这里。</p>
        <p v-if="tool.engine === 'server'" class="empty-note">文件会上传到服务器处理，仅维护者可访问。</p>
        <p v-else class="empty-note">文件只在浏览器内处理，刷新页面即丢失。</p>
      </div>

      <div v-else-if="state === 'uploading'" class="result-progress">
        <div class="progress-head">
          <AppIcon name="upload" :size="17" />
          <span>正在上传文件</span>
          <span class="mono">{{ progress }}%</span>
        </div>
        <div class="progress-track">
          <span :style="{ width: `${progress}%` }"></span>
        </div>
        <p>{{ tool.max_count > 1 ? `共 ${task?.file_count ?? ''} 个文件，` : '' }}上传完成后自动开始处理。</p>
      </div>

      <div v-else-if="state === 'processing'" class="result-loading is-processing">
        <AppIcon name="refresh" :size="18" class="spin" />
        <div>
          <strong>服务端正在处理</strong>
          <p>处理完成后结果会自动出现在这里，请不要关闭页面。</p>
        </div>
      </div>

      <div v-else-if="error && state === 'failed'" class="result-error">
        <div class="error-head">
          <AppIcon name="alert" :size="17" />
          <strong>{{ error.code ? `处理失败（${error.code}）` : '处理失败' }}</strong>
        </div>
        <p>{{ error.message }}</p>
        <p v-if="error.retryAt" class="mono">预计恢复：{{ error.retryAt }}</p>
        <div class="error-actions">
          <button class="button button-ghost button-sm" type="button" @click="askRetry">
            <AppIcon name="refresh" :size="13" />
            重试
          </button>
          <button v-if="payload?.site.feedback_enabled !== false" class="text-button" type="button" @click="goFeedback">
            反馈此问题
            <AppIcon name="arrow-up-right" :size="11" />
          </button>
        </div>
      </div>

      <template v-else-if="task">
        <div class="task-summary">
          <div class="summary-status">
            <span class="status-dot" :class="{ partial: task.status === 'partial' }"></span>
            <strong>
              {{
                task.status === 'succeeded'
                  ? '任务完成'
                  : task.status === 'partial'
                    ? '部分文件未成功'
                    : task.status === 'expired'
                      ? '结果已过期'
                      : task.status === 'canceled'
                        ? '任务已取消'
                        : '任务失败'
              }}
            </strong>
          </div>
          <span class="summary-meta mono">
            {{ task.file_count ? `${task.file_count} 个文件 · ${formatBytes(task.total_size)}` : '文本任务' }} ·
            {{ formatDuration(task.duration_ms) }}
          </span>
        </div>

        <div v-for="note in task.notes" :key="note" class="alert alert-info result-note">
          <AppIcon name="info" :size="14" />
          <span>{{ note }}</span>
        </div>

        <ul v-if="task.failures.length" class="failure-list" role="alert">
          <li v-for="(failure, index) in task.failures" :key="index">
            <span class="failure-code mono">{{ failure.code }}</span>
            <span>{{ failure.message }}</span>
          </li>
        </ul>

        <ul v-if="task.results.length" class="result-list">
          <li v-for="result in task.results" :key="result.id" class="result-row">
            <span class="result-thumb">
              <img v-if="isImage(result.content_type)" :src="result.preview_url ?? result.download_url" alt="" loading="lazy" />
              <AppIcon v-else :name="result.kind === 'text' ? 'file' : 'file'" :size="18" />
            </span>
            <span class="result-info">
              <span class="result-name">{{ result.filename }}</span>
              <span class="result-meta mono">
                {{ metaSummary(result.meta, result.size) }}
              </span>
              <audio
                v-if="isAudio(result.content_type)"
                class="result-audio"
                controls
                preload="none"
                :src="result.download_url"
              ></audio>
              <video
                v-if="isVideo(result.content_type)"
                class="result-video"
                controls
                preload="none"
                :src="result.download_url"
              ></video>
            </span>
            <span class="result-actions">
              <a class="button button-soft button-sm" :href="result.download_url" download>
                <AppIcon name="download" :size="13" />
                下载
              </a>
            </span>
          </li>
        </ul>

        <p v-else-if="task.status === 'expired'" class="empty-line">
          结果已过期或不可用，请重新处理。
        </p>

        <div v-if="showActions" class="result-actions-bar">
          <a
            v-if="task.results.length > 1"
            class="button button-ink button-sm"
            :href="`/api/tasks/${task.task_id}/archive`"
          >
            <AppIcon name="download" :size="13" />
            打包下载 ZIP
          </a>
          <button class="text-button" type="button" @click="askDelete">删除结果</button>
        </div>

        <div v-if="state === 'partial' || state === 'failed' || state === 'expired'" class="failure-actions">
          <button class="button button-ghost button-sm" type="button" @click="askRetry">
            <AppIcon name="refresh" :size="13" />
            重新处理
          </button>
          <button v-if="payload?.site.feedback_enabled !== false" class="text-button" type="button" @click="goFeedback">
            反馈此问题
            <AppIcon name="arrow-up-right" :size="11" />
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.result-panel {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-2);
}

.result-head .mono-label {
  color: var(--faint);
  font-size: 8.5px;
}

.result-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-body {
  padding: 18px 16px;
}

.result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 26px 8px;
  text-align: center;
}

.empty-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin-bottom: 13px;
  border: 1px dashed var(--line-strong);
  border-radius: 50%;
  color: var(--faint);
}

.result-empty strong {
  font-size: 19px;
  font-weight: 500;
  color: var(--ink-2);
}

.result-empty p {
  max-width: 230px;
  margin-top: 7px;
  color: var(--faint);
  font-size: 11.5px;
  line-height: 1.65;
}

.empty-note {
  color: var(--muted) !important;
}

.result-loading {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 18px 6px;
  color: var(--muted);
  font-size: 12px;
}

.result-loading.is-processing strong {
  display: block;
  color: var(--ink-2);
  font-size: 12.5px;
}

.result-loading p {
  margin-top: 4px;
  color: var(--faint);
  font-size: 11px;
  line-height: 1.6;
}

.result-progress {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 8px 2px;
}

.progress-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ink-2);
  font-size: 12px;
}

.progress-head span:last-child {
  margin-left: auto;
  color: var(--faint);
  font-size: 11px;
}

.progress-track {
  height: 5px;
  border-radius: 999px;
  background: var(--paper-deep);
  overflow: hidden;
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
  transition: width 0.2s;
}

.result-progress p {
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.6;
}

.result-error {
  padding: 6px 2px;
}

.error-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--danger);
  font-size: 12.5px;
}

.result-error > p {
  margin-top: 9px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.error-actions,
.failure-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 14px;
}

.task-summary {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-bottom: 13px;
  border-bottom: 1px dashed var(--line);
}

.summary-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success);
}

.status-dot.partial {
  background: var(--warn);
}

.summary-meta {
  color: var(--faint);
  font-size: 9.5px;
}

.result-note {
  margin-top: 10px;
  padding: 9px 11px;
  font-size: 11px;
}

.failure-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--danger-soft);
}

.failure-list li {
  display: flex;
  gap: 7px;
  color: var(--danger);
  font-size: 11px;
  line-height: 1.55;
}

.failure-code {
  flex: none;
  font-size: 9px;
  padding-top: 2px;
}

.result-list {
  display: flex;
  flex-direction: column;
  margin-top: 6px;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(217, 211, 196, 0.55);
}

.result-row:last-child {
  border-bottom: 0;
}

.result-thumb {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--surface-2);
  color: var(--faint);
  overflow: hidden;
}

.result-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.result-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11.5px;
  color: var(--ink-2);
}

.result-meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--faint);
  font-size: 9px;
}

.result-audio {
  width: 100%;
  height: 34px;
  margin-top: 5px;
}

.result-video {
  width: 100%;
  max-height: 220px;
  margin-top: 5px;
  border-radius: 6px;
  background: #101613;
}

.result-actions {
  flex: none;
}

.result-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}

.expiry-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 12px;
  color: var(--faint);
  font-size: 10px;
  line-height: 1.6;
}

.empty-line {
  padding: 14px 2px;
  color: var(--faint);
  font-size: 11.5px;
  line-height: 1.65;
}

.failure-actions {
  margin-top: 12px;
}

@media (max-width: 420px) {
  .result-row {
    align-items: flex-start;
  }

  .result-actions .button {
    padding: 0 10px;
  }
}
</style>
