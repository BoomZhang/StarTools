<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import {
  deleteRawFile,
  fetchAdminTools,
  fetchRawFiles,
  manualCleanup,
  rawDownloadUrl,
  rawPreviewUrl,
  type AdminTool,
  type RawResponse,
} from '@/api/admin'
import { parseApiError } from '@/api/client'
import { formatBytes, formatDateTime } from '@/utils/format'

const data = ref<RawResponse | null>(null)
const tools = ref<AdminTool[]>([])
const loading = ref(true)
const error = ref('')
const cleaning = ref(false)
const cleanupMessage = ref('')

const filters = reactive({
  days: 30,
  tool: '',
  ip: '',
  page: 1,
})

onMounted(async () => {
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
    data.value = await fetchRawFiles({
      days: filters.days,
      tool: filters.tool || undefined,
      ip: filters.ip.trim() || undefined,
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

function changePage(page: number) {
  filters.page = page
  void load()
}

async function remove(id: string, filename: string) {
  if (!window.confirm(`确认提前删除「${filename}」？删除不可恢复，且不会影响使用记录。`)) return
  try {
    await deleteRawFile(id)
    await load()
  } catch (err) {
    error.value = parseApiError(err).message
  }
}

async function cleanup() {
  if (!window.confirm('确认清理所有到期数据？原始文件按 30 天、结果按 1 小时、记录按 90 天删除，均不可恢复。')) return
  cleaning.value = true
  cleanupMessage.value = ''
  try {
    const counts = await manualCleanup()
    cleanupMessage.value = `清理完成：原始文件 ${counts.raw ?? 0}、结果 ${counts.results ?? 0}、任务 ${counts.tasks ?? 0}、使用记录 ${counts.usage ?? 0}、反馈 ${counts.feedback ?? 0}、操作记录 ${counts.audit ?? 0}。`
    await load()
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    cleaning.value = false
  }
}
</script>

<template>
  <div class="raw-admin">
    <div class="page-toolbar">
      <div>
        <p class="mono-label">RAW FILES / 30 DAYS</p>
        <h2 class="serif">原始文件只在服务端处理时产生。</h2>
        <p class="toolbar-note">
          访客不能提前删除；维护者查看、下载与删除都会写入操作记录。当前占用
          <strong>{{ formatBytes(data?.total_bytes ?? 0) }}</strong>。
        </p>
      </div>
      <div class="toolbar-side">
        <span class="mono-label total-label">{{ data?.total ?? 0 }} FILES</span>
        <div class="toolbar-actions">
          <button class="button button-ghost button-sm" type="button" :disabled="loading" @click="load">
            <AppIcon name="refresh" :size="13" />
            刷新
          </button>
          <button class="button button-ghost button-sm" type="button" :disabled="cleaning" @click="cleanup">
            <AppIcon name="trash" :size="13" />
            {{ cleaning ? '清理中…' : '清理到期数据' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="cleanupMessage" class="alert alert-success">
      <AppIcon name="check-circle" :size="15" />
      <span>{{ cleanupMessage }}</span>
    </div>

    <div class="filter-bar panel">
      <div class="filter-field">
        <span class="mono-label">RANGE</span>
        <select v-model.number="filters.days" class="select filter-select">
          <option :value="7">7 天</option>
          <option :value="30">30 天</option>
          <option :value="90">90 天</option>
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
        <span class="mono-label">IP</span>
        <input v-model="filters.ip" class="input filter-input" placeholder="精确 IP" @keyup.enter="applyFilters" />
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
              <th>上传时间</th>
              <th>工具</th>
              <th>文件名</th>
              <th>类型</th>
              <th>大小</th>
              <th>IP</th>
              <th>到期时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data?.items ?? []" :key="item.id">
              <td class="mono-cell">{{ formatDateTime(item.created_at) }}</td>
              <td>
                <span class="tool-cell">
                  <strong>{{ item.tool_name }}</strong>
                  <span class="mono-cell">{{ item.tool_code }}</span>
                </span>
              </td>
              <td><span class="file-name">{{ item.filename }}</span></td>
              <td class="mono-cell">{{ item.content_type }}</td>
              <td class="mono-cell">{{ formatBytes(item.size) }}</td>
              <td class="mono-cell">{{ item.ip }}</td>
              <td class="mono-cell">{{ formatDateTime(item.expires_at) }}</td>
              <td>
                <div class="row-actions">
                  <a class="button button-ghost button-sm" :href="rawPreviewUrl(item.id)" target="_blank" rel="noreferrer">
                    <AppIcon name="eye" :size="12" />
                    预览
                  </a>
                  <a class="button button-soft button-sm" :href="rawDownloadUrl(item.id)">
                    <AppIcon name="download" :size="12" />
                    下载
                  </a>
                  <button class="text-button danger" type="button" @click="remove(item.id, item.filename)">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && !(data?.items.length)">
              <td colspan="8">
                <div class="empty-state"><strong>暂无原始文件</strong><span>只有实际走服务端处理的任务才会产生原始文件。</span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AdminPagination v-if="data" :page="filters.page" :pages="data.pages" :total="data.total" @change="changePage" />
    </div>
  </div>
</template>

<style scoped>
.raw-admin {
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

.toolbar-note strong {
  color: var(--ink-2);
}

.total-label {
  padding-bottom: 4px;
  color: var(--faint);
  font-size: 8.5px;
}

.toolbar-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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
  min-width: 128px;
  padding: 8px 30px 8px 10px;
  font-size: 11.5px;
}

.filter-input {
  width: 150px;
  padding: 8px 10px;
  font-size: 11.5px;
  font-family: var(--font-mono);
}

.table-panel {
  overflow: hidden;
}

.tool-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tool-cell strong {
  font-size: 11.5px;
  font-weight: 500;
}

.tool-cell .mono-cell {
  color: var(--faint);
  font-size: 8.5px;
}

.file-name {
  display: inline-block;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
  font-size: 11px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.row-actions .button {
  min-height: 30px;
  padding: 0 9px;
}

.danger {
  color: var(--danger);
}

@media (max-width: 900px) {
  .filter-input {
    width: 100%;
  }
}
</style>
