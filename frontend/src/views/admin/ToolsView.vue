<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import { fetchAdminTools, updateAdminTool, type AdminTool, type AdminToolGroup, type ToolPatch } from '@/api/admin'
import { parseApiError } from '@/api/client'
import { formatDateTime } from '@/utils/format'

interface Draft {
  online: boolean
  server_enabled: boolean
  max_file_mb: number | null
  max_count: number
}

const groups = ref<AdminToolGroup[]>([])
const drafts = reactive<Record<string, Draft>>({})
const loading = ref(true)
const error = ref('')
const rowError = ref<Record<string, string>>({})
const saving = ref<Record<string, boolean>>({})

onMounted(() => {
  void load()
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    groups.value = await fetchAdminTools()
    groups.value.forEach((group) => {
      group.tools.forEach((tool) => {
        drafts[tool.code] = {
          online: tool.online,
          server_enabled: tool.server_enabled,
          max_file_mb: tool.max_file_mb,
          max_count: tool.max_count,
        }
      })
    })
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    loading.value = false
  }
}

function isDirty(tool: AdminTool): boolean {
  const draft = drafts[tool.code]
  if (!draft) return false
  return (
    draft.online !== tool.online ||
    draft.server_enabled !== tool.server_enabled ||
    draft.max_file_mb !== tool.max_file_mb ||
    draft.max_count !== tool.max_count
  )
}

function anyDirty(): boolean {
  return groups.value.some((group) => group.tools.some((tool) => isDirty(tool)))
}

function toggleOnline(tool: AdminTool, event: Event) {
  const target = event.target as HTMLInputElement
  const next = target.checked
  if (!tool.implemented) {
    target.checked = false
    return
  }
  const message = next
    ? `确认上线「${tool.name}」？上线后将出现在首页工具列表中。`
    : `确认关闭「${tool.name}」？关闭后会从首页工具列表隐藏，直接访问显示已下线。`
  if (!window.confirm(message)) {
    target.checked = drafts[tool.code].online
    return
  }
  drafts[tool.code].online = next
}

function toggleServer(tool: AdminTool, event: Event) {
  const target = event.target as HTMLInputElement
  const next = target.checked
  if (tool.engine_type !== 'dual') {
    target.checked = tool.server_enabled
    return
  }
  const message = next
    ? `确认将「${tool.name}」切回服务端处理？文件会上传并保留 30 天，保存后只影响新任务。`
    : `确认将「${tool.name}」切换为前端处理？文件将不再上传，保存后只影响新任务。`
  if (!window.confirm(message)) {
    target.checked = drafts[tool.code].server_enabled
    return
  }
  drafts[tool.code].server_enabled = next
}

function validate(tool: AdminTool): string {
  const draft = drafts[tool.code]
  if (tool.accepts_files && draft.max_file_mb !== null) {
    if (!Number.isInteger(draft.max_file_mb) || draft.max_file_mb < 1 || draft.max_file_mb > tool.hard_limit_mb) {
      return `单文件上限需在 1–${tool.hard_limit_mb}MB 之间`
    }
  }
  if (tool.fixed_count && draft.max_count !== 1) return '该工具仅接受单文件，数量固定为 1'
  if (draft.max_count < 1 || draft.max_count > 50) return '单次数量需在 1–50 之间'
  return ''
}

async function save(tool: AdminTool) {
  const message = validate(tool)
  if (message) {
    rowError.value[tool.code] = message
    return
  }
  const draft = drafts[tool.code]
  const patch: ToolPatch = {}
  if (draft.online !== tool.online) patch.online = draft.online
  if (draft.server_enabled !== tool.server_enabled) patch.server_enabled = draft.server_enabled
  if (draft.max_file_mb !== tool.max_file_mb) patch.max_file_mb = draft.max_file_mb ?? undefined
  if (draft.max_count !== tool.max_count) patch.max_count = draft.max_count
  if (!Object.keys(patch).length) return

  saving.value[tool.code] = true
  rowError.value[tool.code] = ''
  try {
    const updated = await updateAdminTool(tool.code, patch)
    const group = groups.value.find((item) => item.key === updated.category)
    if (group) {
      const index = group.tools.findIndex((item) => item.code === updated.code)
      if (index >= 0) group.tools[index] = updated
    }
    drafts[tool.code] = {
      online: updated.online,
      server_enabled: updated.server_enabled,
      max_file_mb: updated.max_file_mb,
      max_count: updated.max_count,
    }
  } catch (err) {
    rowError.value[tool.code] = parseApiError(err).message
  } finally {
    saving.value[tool.code] = false
  }
}

function statusBadge(tool: AdminTool): { label: string; className: string } {
  if (tool.status === 'unimplemented') return { label: '未实现', className: 'badge-neutral' }
  if (tool.status === 'offline') return { label: '已下线', className: 'badge-warn' }
  return { label: '已生效', className: 'badge-success' }
}

function engineHint(tool: AdminTool): string {
  if (tool.engine_type === 'server') return '该功能无前端实现，服务端处理锁定为开'
  if (tool.engine_type === 'local') return '该功能无服务端实现，服务端处理锁定为关'
  return '双端工具：开=服务端，关=前端'
}

const totalTools = computed(() => groups.value.reduce((sum, group) => sum + group.tools.length, 0))
const onlineTools = computed(() =>
  groups.value.reduce((sum, group) => sum + group.tools.filter((tool) => tool.online).length, 0),
)
</script>

<template>
  <div class="tools-admin">
    <div class="page-toolbar">
      <div>
        <p class="mono-label">CONFIG / PER TOOL</p>
        <h2 class="serif">逐工具配置，不做全局限额。</h2>
        <p class="toolbar-note">
          覆盖全部 {{ totalTools }} 个工具，当前 {{ onlineTools }} 个已上线。关闭工具或切换引擎会二次确认，
          保存后 10 秒内对新任务生效。
        </p>
      </div>
      <button class="button button-ghost button-sm" type="button" :disabled="loading" @click="load">
        <AppIcon name="refresh" :size="13" />
        重新读取
      </button>
    </div>

    <div v-if="error" class="alert alert-danger">
      <AppIcon name="alert" :size="15" />
      <span>{{ error }}</span>
    </div>

    <div v-if="anyDirty()" class="alert alert-warn">
      <AppIcon name="info" :size="15" />
      <span>有未保存的变更。每行需单独点击「保存」才会写入配置并记录操作。</span>
    </div>

    <div v-for="group in groups" :key="group.key" class="config-group">
      <header class="group-head">
        <div class="group-title">
          <h3 class="serif">{{ group.name }}</h3>
          <span class="mono-label">{{ group.tools.length }} TOOLS</span>
        </div>
        <p>{{ group.blurb }}</p>
      </header>

      <div class="table-wrap panel">
        <table class="table config-table">
          <thead>
            <tr>
              <th>工具</th>
              <th>上线</th>
              <th>服务端处理</th>
              <th>单文件上限</th>
              <th>单次数量</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tool in group.tools" :key="tool.code">
              <td>
                <div class="tool-cell">
                  <span class="mono-cell">{{ tool.code }} · {{ tool.priority }}</span>
                  <strong>{{ tool.name }}</strong>
                  <span class="tool-engine-type">{{ engineHint(tool) }}</span>
                  <span v-if="!tool.available && tool.implemented" class="availability">{{ tool.unavailable_reason }}</span>
                </div>
              </td>
              <td>
                <label class="switch" :title="tool.implemented ? '' : 'P1 工具未实现前不可上线'">
                  <input
                    type="checkbox"
                    :checked="drafts[tool.code]?.online"
                    :disabled="!tool.implemented"
                    @change="toggleOnline(tool, $event)"
                  />
                  <span></span>
                </label>
              </td>
              <td>
                <label
                  class="switch"
                  :title="tool.engine_type === 'dual' ? '双端工具可切换' : engineHint(tool)"
                >
                  <input
                    type="checkbox"
                    :checked="drafts[tool.code]?.server_enabled"
                    :disabled="tool.engine_type !== 'dual'"
                    @change="toggleServer(tool, $event)"
                  />
                  <span></span>
                </label>
                <span class="locked-label">{{ tool.engine_type === 'dual' ? '双端' : tool.engine_type === 'server' ? '仅服务端' : '仅前端' }}</span>
              </td>
              <td>
                <template v-if="tool.accepts_files">
                  <span class="input-with-unit">
                    <input
                      v-model.number="drafts[tool.code].max_file_mb"
                      class="input input-mono config-input"
                      type="number"
                      min="1"
                      :max="tool.hard_limit_mb"
                      aria-label="单文件上限"
                    />
                    <span>MB</span>
                  </span>
                </template>
                <span v-else class="dash">—</span>
              </td>
              <td>
                <input
                  v-model.number="drafts[tool.code].max_count"
                  class="input input-mono config-input"
                  type="number"
                  min="1"
                  max="50"
                  :disabled="tool.fixed_count"
                  aria-label="单次数量"
                />
                <span v-if="tool.fixed_count" class="locked-label">固定 1</span>
              </td>
              <td>
                <span class="badge" :class="statusBadge(tool).className">{{ statusBadge(tool).label }}</span>
                <span class="updated-at">{{ tool.updated_at ? formatDateTime(tool.updated_at) : '' }}</span>
              </td>
              <td>
                <button
                  class="button button-ink button-sm"
                  type="button"
                  :disabled="!isDirty(tool) || saving[tool.code]"
                  @click="save(tool)"
                >
                  {{ saving[tool.code] ? '保存中…' : '保存' }}
                </button>
                <p v-if="rowError[tool.code]" class="row-error">{{ rowError[tool.code] }}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tools-admin {
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
  max-width: 620px;
  margin-top: 8px;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.65;
}

.config-group {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.group-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 4px 0;
}

.group-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.group-title h3 {
  font-size: 21px;
  font-weight: 600;
}

.group-title .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.group-head > p {
  color: var(--faint);
  font-size: 10.5px;
  text-align: right;
}

.config-table {
  min-width: 900px;
}

.config-table td {
  vertical-align: top;
}

.tool-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-width: 240px;
}

.tool-cell strong {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-2);
}

.tool-cell .mono-cell {
  color: var(--faint);
  font-size: 8.5px;
}

.tool-engine-type {
  color: var(--faint);
  font-size: 9.5px;
  line-height: 1.5;
}

.availability {
  color: var(--warn);
  font-size: 9.5px;
}

.locked-label {
  display: block;
  margin-top: 4px;
  color: var(--faint);
  font-size: 8.5px;
}

.config-input {
  width: 74px;
  padding: 7px 9px;
  font-size: 11px;
}

.input-with-unit {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.input-with-unit span {
  color: var(--faint);
  font-size: 9px;
}

.dash {
  color: var(--faint);
  font-size: 11px;
}

.updated-at {
  display: block;
  margin-top: 4px;
  color: var(--faint);
  font-size: 8px;
}

.row-error {
  max-width: 180px;
  margin-top: 5px;
  color: var(--danger);
  font-size: 9px;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .group-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }

  .group-head > p {
    text-align: left;
  }
}
</style>
