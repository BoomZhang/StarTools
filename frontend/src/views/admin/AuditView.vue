<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { fetchAudit, type AuditResponse } from '@/api/admin'
import { parseApiError } from '@/api/client'
import { formatDateTime } from '@/utils/format'

const data = ref<AuditResponse | null>(null)
const days = ref(30)
const page = ref(1)
const loading = ref(true)
const error = ref('')

const actionLabels: Record<string, string> = {
  login: '登录成功',
  login_failed: '登录失败',
  'tool.update': '工具配置变更',
  'feedback.status': '反馈状态变更',
  'feedback.note': '添加反馈备注',
  'settings.feedback': '反馈入口开关',
  'raw.preview': '预览原始文件',
  'raw.download': '下载原始文件',
  'raw.delete': '删除原始文件',
  'cleanup.manual': '手动清理',
  'cleanup.auto': '自动清理',
}

onMounted(() => {
  void load()
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchAudit(days.value, page.value)
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    loading.value = false
  }
}

async function changeRange(value: number) {
  days.value = value
  page.value = 1
  await load()
}

function changePage(next: number) {
  page.value = next
  void load()
}

function detailText(detail: Record<string, unknown>): string {
  if (!detail || !Object.keys(detail).length) return '—'
  if ('before' in detail || 'after' in detail) {
    return JSON.stringify(detail.after ?? detail)
  }
  return JSON.stringify(detail)
}
</script>

<template>
  <div class="audit-admin">
    <div class="page-toolbar">
      <div>
        <p class="mono-label">AUDIT / RETENTION 90 DAYS</p>
        <h2 class="serif">维护者的高影响操作都留痕。</h2>
        <p class="toolbar-note">记录登录、配置变更、原始数据访问/删除、反馈处理与手动清理；不记录密码、文件内容与反馈正文。</p>
      </div>
      <div class="toolbar-actions">
        <div class="segmented">
          <button v-for="value in [7, 30, 90]" :key="value" type="button" :class="{ 'is-active': days === value }" @click="changeRange(value)">
            {{ value }} 天
          </button>
        </div>
        <button class="button button-ghost button-sm" type="button" :disabled="loading" @click="load">
          <AppIcon name="refresh" :size="13" />
          刷新
        </button>
      </div>
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
              <th>时间</th>
              <th>账号</th>
              <th>动作</th>
              <th>目标</th>
              <th>变更摘要</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data?.items ?? []" :key="item.id">
              <td class="mono-cell">{{ formatDateTime(item.created_at) }}</td>
              <td class="mono-cell">{{ item.actor || '—' }}</td>
              <td><span class="action">{{ actionLabels[item.action] ?? item.action }}</span></td>
              <td class="mono-cell">{{ item.target }}</td>
              <td><code class="detail-cell">{{ detailText(item.detail) }}</code></td>
              <td class="mono-cell">{{ item.ip || '—' }}</td>
            </tr>
            <tr v-if="!loading && !(data?.items.length)">
              <td colspan="6">
                <div class="empty-state"><strong>暂无操作记录</strong><span>所选区间内没有管理台操作。</span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AdminPagination v-if="data" :page="page" :pages="data.pages" :total="data.total" @change="changePage" />
    </div>
  </div>
</template>

<style scoped>
.audit-admin {
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
  max-width: 640px;
  margin-top: 7px;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.65;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.table-panel {
  overflow: hidden;
}

.action {
  color: var(--ink-2);
  font-size: 11.5px;
  white-space: nowrap;
}

.detail-cell {
  display: inline-block;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 9.5px;
}
</style>
