<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { fetchAdminTools, fetchUsage, type AdminTool, type UsageResponse } from '@/api/admin'
import { parseApiError } from '@/api/client'
import { formatBytes, formatDateTime, formatDuration } from '@/utils/format'

const route = useRoute()
const data = ref<UsageResponse | null>(null)
const tools = ref<AdminTool[]>([])
const loading = ref(true)
const error = ref('')

const filters = reactive({
  days: 30,
  tool: String(route.query.tool ?? ''),
  result: '',
  engine: '',
  ip: '',
  page: 1,
})

const resultLabels: Record<string, string> = {
  succeeded: '成功',
  partial: '部分成功',
  failed: '失败',
  canceled: '已取消',
}

const engineLabels: Record<string, string> = { server: '服务端', local: '前端' }

onMounted(async () => {
  try {
    const groups = await fetchAdminTools()
    tools.value = groups.flatMap((group) => group.tools)
  } catch {
    tools.value = []
  }
  await load()
})

watch(
  () => filters.days,
  () => {
    filters.page = 1
    void load()
  },
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchUsage({
      days: filters.days,
      tool: filters.tool || undefined,
      result: filters.result || undefined,
      engine: filters.engine || undefined,
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

function resultClass(result: string): string {
  if (result === 'succeeded') return 'badge-success'
  if (result === 'partial') return 'badge-warn'
  if (result === 'failed') return 'badge-danger'
  return 'badge-neutral'
}

const totalPages = computed(() => data.value?.pages ?? 1)
</script>

<template>
  <div class="usage-admin">
    <div class="page-toolbar">
      <div>
        <p class="mono-label">USAGE / RETENTION 90 DAYS</p>
        <h2 class="serif">谁在什么时候用了哪个工具。</h2>
        <p class="toolbar-note">记录不含文件名、文件内容、文本或识别结果；IP 只用于统计与限流。</p>
      </div>
      <span class="mono-label total-label">{{ data?.total ?? 0 }} RECORDS</span>
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
        <span class="mono-label">RESULT</span>
        <select v-model="filters.result" class="select filter-select">
          <option value="">全部结果</option>
          <option value="succeeded">成功</option>
          <option value="partial">部分成功</option>
          <option value="failed">失败</option>
          <option value="canceled">已取消</option>
        </select>
      </div>
      <div class="filter-field">
        <span class="mono-label">ENGINE</span>
        <select v-model="filters.engine" class="select filter-select">
          <option value="">全部引擎</option>
          <option value="server">服务端</option>
          <option value="local">前端</option>
        </select>
      </div>
      <div class="filter-field ip-field">
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
              <th>时间</th>
              <th>工具</th>
              <th>结果</th>
              <th>引擎</th>
              <th>耗时</th>
              <th>文件</th>
              <th>大小</th>
              <th>IP</th>
              <th>错误</th>
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
              <td>
                <span class="badge" :class="resultClass(item.result)">{{ resultLabels[item.result] ?? item.result }}</span>
                <span v-if="item.is_retry" class="retry-tag">重试</span>
              </td>
              <td class="mono-cell">{{ engineLabels[item.engine] ?? item.engine }}</td>
              <td class="mono-cell">{{ formatDuration(item.duration_ms) }}</td>
              <td class="mono-cell">{{ item.file_count }}</td>
              <td class="mono-cell">{{ formatBytes(item.total_size) }}</td>
              <td class="mono-cell">{{ item.ip || '—' }}</td>
              <td class="mono-cell">{{ item.error_code || '—' }}</td>
            </tr>
            <tr v-if="!loading && !(data?.items.length)">
              <td colspan="9">
                <div class="empty-state"><strong>暂无使用记录</strong><span>所选区间或筛选条件下没有任务记录。</span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AdminPagination
        v-if="data"
        :page="filters.page"
        :pages="totalPages"
        :total="data.total"
        @change="changePage"
      />
    </div>

    <p class="footer-note">前端工具离线时无法上报使用记录，因此本页不含离线使用，不伪造数据。</p>
  </div>
</template>

<style scoped>
.usage-admin {
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

.total-label {
  padding-bottom: 4px;
  color: var(--faint);
  font-size: 8.5px;
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
  min-width: 132px;
  padding: 8px 30px 8px 10px;
  font-size: 11.5px;
}

.filter-input {
  width: 150px;
  padding: 8px 10px;
  font-size: 11.5px;
}

.ip-field .filter-input {
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

.retry-tag {
  margin-left: 4px;
  color: var(--faint);
  font-size: 8.5px;
}

.footer-note {
  color: var(--faint);
  font-size: 10px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .filter-select {
    min-width: 112px;
  }
}
</style>
