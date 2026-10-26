<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { fetchOverview, type OverviewData } from '@/api/admin'
import { parseApiError } from '@/api/client'
import { formatBytes, formatDateTime } from '@/utils/format'

const days = ref(30)
const data = ref<OverviewData | null>(null)
const loading = ref(true)
const error = ref('')

const ranges = [7, 30, 90]

onMounted(() => {
  void load()
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchOverview(days.value)
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    loading.value = false
  }
}

async function changeRange(value: number) {
  days.value = value
  await load()
}

const metrics = computed(() => data.value?.metrics)
const dailyMax = computed(() => Math.max(1, ...(data.value?.daily.map((item) => item.count) ?? [1])))
const hasUsage = computed(() => (data.value?.metrics.total ?? 0) > 0)
const engineTotal = computed(() => {
  if (!data.value) return 0
  return data.value.engine_split.server + data.value.engine_split.local
})
const serverRatio = computed(() =>
  engineTotal.value ? Math.round((data.value!.engine_split.server / engineTotal.value) * 100) : 0,
)
const circumference = 2 * Math.PI * 52
const serverDash = computed(() => (serverRatio.value / 100) * circumference)
const dailyLabelInterval = computed(() => Math.max(1, Math.ceil((data.value?.daily.length ?? 1) / 6)))

function barHeight(count: number): string {
  return `${Math.max(2, (count / dailyMax.value) * 100)}%`
}

function shortDate(value: string): string {
  return value.slice(5)
}
</script>

<template>
  <div class="overview">
    <div class="page-toolbar">
      <div class="toolbar-copy">
        <p class="mono-label">DASHBOARD / {{ days }} DAYS</p>
        <h2 class="serif">用得多不多，哪些工具用得多。</h2>
      </div>
      <div class="toolbar-actions">
        <div class="segmented">
          <button
            v-for="range in ranges"
            :key="range"
            type="button"
            :class="{ 'is-active': days === range }"
            @click="changeRange(range)"
          >
            {{ range }} 天
          </button>
        </div>
        <button class="button button-ghost button-sm" type="button" :disabled="loading" @click="load">
          <AppIcon name="refresh" :size="13" :class="{ spin: loading }" />
          刷新
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger">
      <AppIcon name="alert" :size="15" />
      <span>{{ error }}</span>
    </div>

    <div class="metric-grid">
      <div class="metric-card">
        <span class="mono-label">TODAY</span>
        <strong>{{ metrics?.today ?? '—' }}</strong>
        <span class="metric-label">今日使用次数</span>
      </div>
      <div class="metric-card">
        <span class="mono-label">RANGE TOTAL</span>
        <strong>{{ metrics?.total ?? '—' }}</strong>
        <span class="metric-label">近 {{ days }} 天总次数</span>
      </div>
      <div class="metric-card">
        <span class="mono-label">SERVER SHARE</span>
        <strong>{{ metrics ? `${metrics.server_ratio}%` : '—' }}</strong>
        <span class="metric-label">服务端处理占比 · {{ metrics?.server_tasks ?? 0 }} 次</span>
      </div>
      <div class="metric-card">
        <span class="mono-label">TOOLS</span>
        <strong>{{ metrics ? `${metrics.online_tools}/${metrics.total_tools}` : '—' }}</strong>
        <span class="metric-label">已上线 / 工具总数</span>
      </div>
      <div class="metric-card">
        <span class="mono-label">RAW STORAGE</span>
        <strong>{{ formatBytes(metrics?.raw_bytes ?? 0) }}</strong>
        <span class="metric-label">磁盘 {{ metrics?.disk.percent ?? '—' }}% · 剩余 {{ formatBytes(metrics?.disk.free ?? 0) }}</span>
      </div>
      <div class="metric-card">
        <span class="mono-label">FEEDBACK</span>
        <strong>{{ metrics?.pending_feedback ?? '—' }}</strong>
        <span class="metric-label">待处理反馈</span>
      </div>
    </div>

    <div class="chart-grid">
      <section class="panel chart-panel">
        <div class="panel-head">
          <h2>每日使用次数</h2>
          <span class="mono-label">{{ data?.daily[0]?.date }} → {{ data?.daily[data.daily.length - 1]?.date }}</span>
        </div>
        <div class="trend-body">
          <div class="trend-chart">
            <div v-for="(item, index) in data?.daily ?? []" :key="item.date" class="trend-column">
              <span class="bar" :style="{ height: barHeight(item.count) }" :title="`${item.date} · ${item.count} 次`"></span>
              <span v-if="index % dailyLabelInterval === 0" class="bar-label">{{ shortDate(item.date) }}</span>
            </div>
            <div v-if="!loading && !hasUsage" class="chart-empty">该区间暂无使用记录</div>
          </div>
        </div>
      </section>

      <section class="panel engine-panel">
        <div class="panel-head">
          <h2>引擎占比</h2>
          <span class="mono-label">SERVER / LOCAL</span>
        </div>
        <div class="engine-body">
          <div class="donut">
            <svg viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="var(--paper-deep)" stroke-width="12" />
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke="var(--server)"
                stroke-width="12"
                stroke-linecap="round"
                :stroke-dasharray="`${serverDash} ${circumference}`"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="donut-center">
              <strong>{{ serverRatio }}%</strong>
              <span>服务端</span>
            </div>
          </div>
          <div class="engine-legend">
            <div><span class="legend-dot server"></span>服务端 <strong>{{ data?.engine_split.server ?? 0 }}</strong></div>
            <div><span class="legend-dot local"></span>前端 <strong>{{ data?.engine_split.local ?? 0 }}</strong></div>
            <p class="mono-label">TOTAL {{ engineTotal }} TASKS</p>
          </div>
        </div>
      </section>
    </div>

    <div class="chart-grid lower">
      <section class="panel ranking-panel">
        <div class="panel-head">
          <h2>工具使用排行</h2>
          <span class="mono-label">TOP 10</span>
        </div>
        <div class="panel-body">
          <div v-if="data?.ranking.length" class="ranking-list">
            <div v-for="(item, index) in data.ranking" :key="item.code" class="ranking-row">
              <span class="rank-index mono-label">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="rank-name">{{ item.name }}</span>
              <span class="rank-track"><span :style="{ width: `${Math.max(4, item.ratio)}%` }"></span></span>
              <span class="rank-count mono">{{ item.count }}</span>
            </div>
          </div>
          <div v-else class="empty-state">该区间暂无使用记录</div>
        </div>
      </section>

      <section class="panel feedback-summary">
        <div class="panel-head">
          <h2>反馈状态</h2>
          <RouterLink to="/admin/feedback" class="text-button">查看反馈</RouterLink>
        </div>
        <div class="panel-body">
          <div class="feedback-counts">
            <div><span class="mono-label">PENDING</span><strong>{{ data?.feedback_counts.pending ?? 0 }}</strong></div>
            <div><span class="mono-label">PROCESSING</span><strong>{{ data?.feedback_counts.processing ?? 0 }}</strong></div>
            <div><span class="mono-label">RESOLVED</span><strong>{{ data?.feedback_counts.resolved ?? 0 }}</strong></div>
            <div><span class="mono-label">IGNORED</span><strong>{{ data?.feedback_counts.ignored ?? 0 }}</strong></div>
          </div>
          <p class="tool-tip">反馈不计入工具使用次数与引擎占比，单独统计并保留 90 天。</p>
        </div>
      </section>
    </div>

    <section class="panel tool-table-panel">
      <div class="panel-head">
        <h2>工具明细</h2>
        <span class="mono-label">USAGE · {{ days }} DAYS</span>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>工具</th>
              <th>分类</th>
              <th>总次数</th>
              <th>成功</th>
              <th>失败</th>
              <th>取消</th>
              <th>最近使用</th>
              <th>最近 IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data?.tool_table ?? []" :key="row.code">
              <td>
                <span class="tool-cell">
                  <span class="mono-cell">{{ row.code }}</span>
                  <strong>{{ row.name }}</strong>
                </span>
              </td>
              <td>{{ row.category }}</td>
              <td class="mono-cell">{{ row.total }}</td>
              <td class="mono-cell">{{ row.succeeded }}</td>
              <td class="mono-cell">{{ row.failed }}</td>
              <td class="mono-cell">{{ row.canceled }}</td>
              <td class="mono-cell">{{ row.last_used ? formatDateTime(row.last_used) : '—' }}</td>
              <td class="mono-cell">{{ row.last_ip || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.toolbar-copy .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.toolbar-copy h2 {
  margin-top: 7px;
  font-size: 24px;
  font-weight: 500;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 15px 16px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
}

.metric-card .mono-label {
  color: var(--faint);
  font-size: 7.5px;
}

.metric-card strong {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 600;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.metric-label {
  color: var(--faint);
  font-size: 9.5px;
  line-height: 1.5;
}

.chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(0, 0.8fr);
  gap: 12px;
}

.chart-grid.lower {
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 0.7fr);
}

.chart-panel,
.engine-panel {
  min-width: 0;
}

.trend-body {
  padding: 16px 18px 12px;
}

.trend-chart {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 190px;
  padding-top: 10px;
  border-bottom: 1px solid var(--line);
  background-image: linear-gradient(rgba(217, 211, 196, 0.35) 1px, transparent 1px);
  background-size: 100% 25%;
}

.trend-column {
  position: relative;
  display: flex;
  flex: 1;
  align-items: flex-end;
  justify-content: center;
  height: 100%;
  min-width: 2px;
}

.bar {
  width: 100%;
  max-width: 26px;
  border-radius: 2px 2px 0 0;
  background: linear-gradient(180deg, var(--forest-3), var(--server));
  transition: height 0.3s var(--ease-out);
}

.bar:hover {
  background: var(--accent);
}

.bar-label {
  position: absolute;
  bottom: -20px;
  left: 50%;
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 8px;
  transform: translateX(-50%);
  white-space: nowrap;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--faint);
  font-size: 11px;
}

.trend-chart {
  margin-bottom: 20px;
}

.engine-body {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
}

.donut {
  position: relative;
  width: 128px;
  height: 128px;
  flex: none;
}

.donut svg {
  width: 100%;
  height: 100%;
}

.donut-center {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
}

.donut-center strong {
  font-family: var(--font-display);
  font-size: 25px;
  font-weight: 600;
}

.donut-center span {
  color: var(--faint);
  font-size: 9px;
}

.engine-legend {
  display: flex;
  flex-direction: column;
  gap: 9px;
  color: var(--muted);
  font-size: 11.5px;
}

.engine-legend div {
  display: flex;
  align-items: center;
  gap: 7px;
}

.engine-legend strong {
  margin-left: auto;
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: 11px;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--server);
}

.legend-dot.local {
  background: var(--local);
}

.engine-legend .mono-label {
  color: var(--faint);
  font-size: 7.5px;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.ranking-row {
  display: grid;
  grid-template-columns: 22px 120px 1fr 42px;
  align-items: center;
  gap: 9px;
}

.rank-index {
  color: var(--faint);
  font-size: 8px;
}

.rank-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.rank-track {
  height: 7px;
  border-radius: 999px;
  background: var(--paper-deep);
  overflow: hidden;
}

.rank-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--local);
}

.rank-count {
  color: var(--muted);
  font-size: 9.5px;
  text-align: right;
}

.feedback-counts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.feedback-counts > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-2);
}

.feedback-counts .mono-label {
  color: var(--faint);
  font-size: 7px;
}

.feedback-counts strong {
  font-size: 20px;
  font-weight: 600;
}

.feedback-summary .tool-tip {
  margin-top: 12px;
}

.tool-table-panel {
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

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .chart-grid,
  .chart-grid.lower {
    grid-template-columns: minmax(0, 1fr);
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .engine-body {
    justify-content: center;
  }
}

@media (max-width: 560px) {
  .metric-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .ranking-row {
    grid-template-columns: 20px 92px 1fr 36px;
  }
}
</style>
