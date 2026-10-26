<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import {
  addFeedbackNote,
  fetchAdminSettings,
  fetchAdminTools,
  fetchFeedbackDetail,
  fetchFeedbackList,
  toggleFeedback,
  updateFeedbackStatus,
  type AdminTool,
  type FeedbackDetail,
  type FeedbackListResponse,
} from '@/api/admin'
import { parseApiError } from '@/api/client'
import { FEEDBACK_STATUSES, FEEDBACK_TYPES } from '@/data/feedback'
import { formatDateTime } from '@/utils/format'

const data = ref<FeedbackListResponse | null>(null)
const tools = ref<AdminTool[]>([])
const loading = ref(true)
const error = ref('')
const feedbackEnabled = ref(true)
const toggling = ref(false)
const detail = ref<FeedbackDetail | null>(null)
const detailLoading = ref(false)
const actionLoading = ref(false)
const note = ref('')
const detailError = ref('')

const filters = reactive({
  status: '',
  type: '',
  tool: '',
  days: 30,
  q: '',
  page: 1,
})

const statusLabels: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略',
}

const transitions: Record<string, { status: string; label: string; kind: 'primary' | 'ghost' }[]> = {
  pending: [
    { status: 'processing', label: '标记处理中', kind: 'primary' },
    { status: 'ignored', label: '标记已忽略', kind: 'ghost' },
  ],
  processing: [
    { status: 'resolved', label: '标记已解决', kind: 'primary' },
    { status: 'ignored', label: '标记已忽略', kind: 'ghost' },
  ],
  resolved: [{ status: 'processing', label: '重新打开', kind: 'ghost' }],
  ignored: [{ status: 'processing', label: '重新打开', kind: 'ghost' }],
}

const totalCount = computed(() => {
  if (!data.value) return 0
  return Object.values(data.value.counts).reduce((sum, value) => sum + value, 0)
})

const contextLabels: Record<string, string> = {
  path: '页面地址',
  tool_code: '工具编号',
  task_id: '任务编号',
  error_code: '错误编号',
  browser: '浏览器',
  viewport: '视口',
  submitted_at: '提交时间',
  ip: 'IP',
}

onMounted(async () => {
  try {
    const settings = await fetchAdminSettings()
    feedbackEnabled.value = settings.feedback_enabled
  } catch {
    // 保持默认
  }
  try {
    const groups = await fetchAdminTools()
    tools.value = groups.flatMap((group) => group.tools)
  } catch {
    tools.value = []
  }
  await load()
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchFeedbackList({
      status: filters.status || undefined,
      type: filters.type || undefined,
      tool: filters.tool || undefined,
      days: filters.days,
      q: filters.q.trim() || undefined,
      page: filters.page,
    })
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  filters.page = 1
  void load()
}

function selectStatus(status: string) {
  filters.status = status
  filters.page = 1
  void load()
}

function changePage(page: number) {
  filters.page = page
  void load()
}

async function toggleEntry(event: Event) {
  const target = event.target as HTMLInputElement
  const next = target.checked
  const message = next
    ? '确认开放访客提交问题反馈？页脚与工具失败区将显示反馈入口。'
    : '确认关闭反馈入口？页脚入口会隐藏，工具页显示「反馈暂不可用」；已有反馈仍可查看。'
  if (!window.confirm(message)) {
    target.checked = feedbackEnabled.value
    return
  }
  toggling.value = true
  try {
    const result = await toggleFeedback(next)
    feedbackEnabled.value = result.feedback_enabled
    target.checked = feedbackEnabled.value
  } catch (err) {
    target.checked = feedbackEnabled.value
    error.value = parseApiError(err).message
  } finally {
    toggling.value = false
  }
}

async function openDetail(id: number) {
  detailLoading.value = true
  detailError.value = ''
  note.value = ''
  try {
    detail.value = await fetchFeedbackDetail(id)
  } catch (err) {
    detailError.value = parseApiError(err).message
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detail.value = null
  note.value = ''
  detailError.value = ''
}

async function changeStatus(status: string) {
  if (!detail.value || actionLoading.value) return
  actionLoading.value = true
  detailError.value = ''
  try {
    detail.value = await updateFeedbackStatus(detail.value.id, status)
    await load()
  } catch (err) {
    detailError.value = parseApiError(err).message
  } finally {
    actionLoading.value = false
  }
}

async function submitNote() {
  if (!detail.value || !note.value.trim() || actionLoading.value) return
  if (note.value.length > 1000) {
    detailError.value = '内部备注不能超过 1000 个字符'
    return
  }
  actionLoading.value = true
  detailError.value = ''
  try {
    detail.value = await addFeedbackNote(detail.value.id, note.value)
    note.value = ''
  } catch (err) {
    detailError.value = parseApiError(err).message
  } finally {
    actionLoading.value = false
  }
}

function statusClass(status: string): string {
  if (status === 'pending') return 'badge-warn'
  if (status === 'processing') return 'badge-accent'
  if (status === 'resolved') return 'badge-success'
  return 'badge-neutral'
}

function contextValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}
</script>

<template>
  <div class="feedback-admin">
    <div class="page-toolbar">
      <div>
        <p class="mono-label">FEEDBACK / 90 DAYS</p>
        <h2 class="serif">反馈只对维护者可见。</h2>
        <p class="toolbar-note">反馈不进入工具任务链路，不计入使用次数与工具排行；正文按纯文本展示。</p>
      </div>
      <div class="entry-toggle">
        <div>
          <span class="mono-label">ENTRY</span>
          <strong>{{ feedbackEnabled ? '允许访客提交反馈' : '反馈入口已关闭' }}</strong>
        </div>
        <label class="switch" :title="feedbackEnabled ? '关闭反馈入口' : '开放反馈入口'">
          <input type="checkbox" :checked="feedbackEnabled" :disabled="toggling" @change="toggleEntry($event)" />
          <span></span>
        </label>
      </div>
    </div>

    <div class="status-tabs">
      <button type="button" :class="{ 'is-active': filters.status === '' }" @click="selectStatus('')">
        全部 <span class="mono-label">{{ totalCount }}</span>
      </button>
      <button
        v-for="status in FEEDBACK_STATUSES"
        :key="status.key"
        type="button"
        :class="{ 'is-active': filters.status === status.key }"
        @click="selectStatus(status.key)"
      >
        {{ status.label }}
        <span class="mono-label">{{ data?.counts[status.key] ?? 0 }}</span>
      </button>
    </div>

    <div class="filter-bar panel">
      <div class="filter-field">
        <span class="mono-label">TYPE</span>
        <select v-model="filters.type" class="select filter-select">
          <option value="">全部类型</option>
          <option v-for="item in FEEDBACK_TYPES" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
      </div>
      <div class="filter-field">
        <span class="mono-label">TOOL</span>
        <select v-model="filters.tool" class="select filter-select">
          <option value="">全部工具</option>
          <option v-for="tool in tools" :key="tool.code" :value="tool.code">{{ tool.code }} · {{ tool.name }}</option>
        </select>
      </div>
      <div class="filter-field">
        <span class="mono-label">RANGE</span>
        <select v-model.number="filters.days" class="select filter-select">
          <option :value="7">7 天</option>
          <option :value="30">30 天</option>
          <option :value="90">90 天</option>
        </select>
      </div>
      <div class="filter-field keyword-field">
        <span class="mono-label">KEYWORD</span>
        <input v-model="filters.q" class="input filter-input" placeholder="搜索描述与期望结果" @keyup.enter="applyFilters" />
      </div>
      <button class="button button-ink button-sm" type="button" :disabled="loading" @click="applyFilters">
        <AppIcon name="search" :size="13" />
        筛选
      </button>
    </div>

    <div v-if="error" class="alert alert-danger">
      <AppIcon name="alert" :size="15" />
      <span>{{ error }}</span>
    </div>

    <div class="panel table-panel">
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>编号</th>
              <th>提交时间</th>
              <th>类型</th>
              <th>工具</th>
              <th>描述摘要</th>
              <th>状态</th>
              <th>IP</th>
              <th>最近更新</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data?.items ?? []" :key="item.id" class="clickable-row" @click="openDetail(item.id)">
              <td class="mono-cell">{{ item.number }}</td>
              <td class="mono-cell">{{ formatDateTime(item.created_at) }}</td>
              <td>{{ item.type_name }}</td>
              <td class="mono-cell">{{ item.tool_code || '不确定' }}</td>
              <td><span class="summary">{{ item.description }}</span></td>
              <td><span class="badge" :class="statusClass(item.status)">{{ item.status_name }}</span></td>
              <td class="mono-cell">{{ item.ip }}</td>
              <td class="mono-cell">{{ formatDateTime(item.updated_at) }}</td>
            </tr>
            <tr v-if="!loading && !(data?.items.length)">
              <td colspan="8">
                <div class="empty-state"><strong>暂无反馈</strong><span>所选状态、类型或时间范围内没有记录。</span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AdminPagination
        v-if="data"
        :page="filters.page"
        :pages="data.pages"
        :total="data.total"
        @change="changePage"
      />
    </div>

    <div v-if="detail || detailLoading" class="detail-overlay" @click.self="closeDetail">
      <aside class="detail-panel">
        <div class="detail-head">
          <div>
            <span class="mono-label">FEEDBACK DETAIL</span>
            <h3 class="serif">{{ detail?.number ?? '读取中…' }}</h3>
          </div>
          <button class="icon-button" type="button" aria-label="关闭详情" @click="closeDetail">
            <AppIcon name="x" :size="16" />
          </button>
        </div>

        <div v-if="detailLoading" class="detail-loading">
          <AppIcon name="refresh" :size="18" class="spin" />
          正在读取反馈…
        </div>

        <template v-else-if="detail">
          <div class="detail-body">
            <div class="detail-meta">
              <span class="badge" :class="statusClass(detail.status)">{{ detail.status_name }}</span>
              <span class="mono-label">{{ detail.type_name }}</span>
              <span class="mono-label">{{ detail.tool_code || '不确定' }}</span>
              <span class="mono-label">{{ formatDateTime(detail.created_at) }}</span>
            </div>

            <section class="detail-section">
              <h4>问题描述</h4>
              <p class="plain-text">{{ detail.description }}</p>
            </section>

            <section v-if="detail.expected" class="detail-section">
              <h4>期望结果</h4>
              <p class="plain-text">{{ detail.expected }}</p>
            </section>

            <section v-if="detail.contact" class="detail-section">
              <h4>联系方式</h4>
              <p class="contact">{{ detail.contact }}</p>
            </section>

            <section class="detail-section">
              <h4>自动上下文</h4>
              <dl class="context-list">
                <div v-for="(value, key) in detail.context" :key="key">
                  <dt>{{ contextLabels[String(key)] ?? String(key) }}</dt>
                  <dd>{{ contextValue(value) }}</dd>
                </div>
                <div>
                  <dt>提交 IP</dt>
                  <dd>{{ detail.ip }}</dd>
                </div>
              </dl>
            </section>

            <section class="detail-section">
              <h4>状态与备注</h4>
              <ul class="timeline">
                <li v-for="event in detail.events" :key="event.id">
                  <span class="timeline-dot" :class="{ note: event.kind === 'note' }"></span>
                  <div>
                    <p v-if="event.kind === 'status'">
                      {{ statusLabels[event.from_status || ''] || '提交' }} →
                      <strong>{{ statusLabels[event.to_status || ''] || event.to_status }}</strong>
                    </p>
                    <p v-else class="note-text">{{ event.note }}</p>
                    <span class="timeline-meta mono">{{ event.actor }} · {{ formatDateTime(event.created_at) }}</span>
                  </div>
                </li>
              </ul>
              <div class="note-form">
                <textarea
                  v-model="note"
                  class="textarea"
                  rows="2"
                  maxlength="1000"
                  placeholder="添加内部备注，仅维护者可见（不超过 1000 字）"
                ></textarea>
                <button class="button button-ghost button-sm" type="button" :disabled="!note.trim() || actionLoading" @click="submitNote">
                  添加备注
                </button>
              </div>
            </section>

            <div v-if="detailError" class="mini-alert danger">
              <AppIcon name="alert" :size="14" />
              <span>{{ detailError }}</span>
            </div>
          </div>

          <div class="detail-actions">
            <button
              v-for="action in transitions[detail.status] ?? []"
              :key="action.status"
              class="button button-sm"
              :class="action.kind === 'primary' ? 'button-ink' : 'button-ghost'"
              type="button"
              :disabled="actionLoading"
              @click="changeStatus(action.status)"
            >
              {{ action.label }}
            </button>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.feedback-admin {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.page-toolbar .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.page-toolbar h2 {
  margin-top: 7px;
  font-size: 24px;
  font-weight: 500;
}

.toolbar-note {
  margin-top: 7px;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.65;
}

.entry-toggle {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface);
}

.entry-toggle .mono-label {
  display: block;
  color: var(--faint);
  font-size: 7.5px;
}

.entry-toggle strong {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  font-weight: 500;
}

.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
}

.status-tabs button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
}

.status-tabs button.is-active {
  background: var(--ink);
  color: var(--paper);
}

.status-tabs .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.status-tabs button.is-active .mono-label {
  color: rgba(244, 241, 232, 0.6);
}

.filter-bar {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 16px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.filter-field .mono-label {
  color: var(--faint);
  font-size: 7.5px;
}

.filter-select {
  min-width: 124px;
  padding: 8px 30px 8px 10px;
  font-size: 11.5px;
}

.filter-input {
  width: 200px;
  padding: 8px 10px;
  font-size: 11.5px;
}

.table-panel {
  overflow: hidden;
}

.clickable-row {
  cursor: pointer;
}

.summary {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-width: 320px;
  color: var(--muted);
  font-size: 11.5px;
}

.detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  justify-content: flex-end;
  background: rgba(12, 20, 16, 0.42);
  backdrop-filter: blur(3px);
}

.detail-panel {
  display: flex;
  flex-direction: column;
  width: min(100%, 560px);
  height: 100%;
  background: var(--paper);
  border-left: 1px solid var(--line);
  overflow: hidden;
}

.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
}

.detail-head .mono-label {
  color: var(--faint);
  font-size: 7.5px;
}

.detail-head h3 {
  margin-top: 4px;
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 500;
}

.detail-loading {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 28px 22px;
  color: var(--muted);
  font-size: 12px;
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px;
}

.detail-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
}

.detail-meta .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.detail-section {
  padding: 16px 0;
  border-bottom: 1px solid var(--line);
}

.detail-section h4 {
  margin-bottom: 8px;
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.plain-text {
  color: var(--ink-2);
  font-size: 12.5px;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.contact {
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: 11px;
  overflow-wrap: anywhere;
}

.context-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 0;
}

.context-list > div {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 8px;
}

.context-list dt {
  color: var(--faint);
  font-size: 9.5px;
}

.context-list dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 9.5px;
  line-height: 1.5;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
}

.timeline li {
  position: relative;
  display: flex;
  gap: 10px;
}

.timeline-dot {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  flex: none;
  border-radius: 50%;
  background: var(--server);
}

.timeline-dot.note {
  background: var(--local);
}

.timeline p {
  color: var(--ink-2);
  font-size: 11.5px;
  line-height: 1.6;
}

.note-text {
  padding: 7px 9px;
  border-radius: 6px;
  background: var(--surface-2);
  white-space: pre-wrap;
}

.timeline-meta {
  display: block;
  margin-top: 2px;
  color: var(--faint);
  font-size: 8.5px;
}

.note-form {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.note-form .textarea {
  min-height: 64px;
  font-size: 12px;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--line);
  background: var(--surface);
}

@media (max-width: 560px) {
  .filter-input,
  .keyword-field {
    width: 100%;
  }

  .detail-panel {
    width: 100%;
  }
}
</style>
