<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ServerResultPanel from '@/components/ServerResultPanel.vue'
import TextTaskPanel from '@/components/TextTaskPanel.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { useServerTask } from '@/composables/useServerTask'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()

const files = ref<File[]>([])
const language = ref('mixed')
const autoRotate = ref(true)
const ranges = ref('')

const isPdf = computed(() => props.tool.code === 'OCR-02')
const isServer = computed(() => props.tool.engine === 'server')

const canRun = computed(
  () => files.value.length > 0 && props.tool.available && isServer.value && accepted.value && !server.busy.value,
)
const hint = computed(() => {
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!files.value.length) return isPdf.value ? '请选择 1 个 PDF' : '请选择至少 1 张图片'
  if (!accepted.value) return '请先确认上传说明'
  return ''
})
const params = computed(() => ({
  language: language.value,
  auto_rotate: autoRotate.value,
  ranges: ranges.value || 'all',
}))

const preview = computed(() => {
  const value = server.task.value?.results[0]?.meta?.preview
  return Array.isArray(value) ? (value as string[][]) : []
})

onMounted(() => {
  if (isServer.value) void server.restore()
})

async function run() {
  if (!canRun.value) return
  await server.run(files.value, params.value, { isRetry: server.state.value === 'failed' })
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>{{ isPdf ? '选择 PDF' : '上传表格图片' }}</h2>
          </div>
          <span class="section-aside">{{ isPdf ? '单文件' : `${files.length} / ${tool.max_count} 张` }}</span>
        </div>
        <FilePicker
          v-if="isPdf"
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          accept="application/pdf,.pdf"
          title="拖拽扫描版 PDF 到这里"
          :hint="`单文件 · 上限 ${tool.max_file_mb}MB · 不超过 50 页`"
          :disabled="!tool.available"
        />
        <FilePicker
          v-else
          v-model="files"
          multiple
          :max-count="tool.max_count"
          :max-file-mb="tool.max_file_mb"
          accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/heic,image/heif,image/*"
          title="拖拽表格图片到这里，或点击选择"
          :hint="`单张上限 ${tool.max_file_mb}MB · 最多 ${tool.max_count} 张`"
          :disabled="!tool.available"
        />
        <p v-if="!isPdf" class="tool-tip option-gap">每个文件会写入一个独立工作表；合并单元格为尽力还原。</p>
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
          <div v-if="isPdf" class="field">
            <span class="field-label"><strong>页码范围</strong><span>留空为全部</span></span>
            <input v-model="ranges" class="input input-mono" placeholder="例如 1-3,5" />
          </div>
          <div class="field">
            <span class="field-label"><strong>自动旋转</strong></span>
            <label class="checkbox"><input v-model="autoRotate" type="checkbox" /> 识别前自动校正方向</label>
          </div>
        </div>
        <div class="mini-alert option-gap">
          <AppIcon name="alert" :size="14" />
          <span>识别结果需人工校对；表格结构为尽力还原，合并单元格可能需要人工调整。</span>
        </div>
        <div class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">{{ isPdf ? '按页输出可编辑文本；可导出 TXT 或 Markdown。' : '导出 XLSX，每个文件一个工作表。' }}</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="scan" :size="15" />
              {{ server.busy.value ? '识别中…' : isPdf ? '识别 PDF' : '识别表格' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <TextTaskPanel
        v-if="isPdf"
        :tool="tool"
        :task="server.task.value"
        :state="server.state.value"
        :error="server.error.value"
        :restoring="server.restoring.value"
        @retry="run"
        @delete="server.removeResults"
      />
      <div v-else>
        <ServerResultPanel
          :tool="tool"
          :task="server.task.value"
          :state="server.state.value"
          :progress="server.progress.value"
          :error="server.error.value"
          :restoring="server.restoring.value"
          @retry="run"
          @delete="server.removeResults"
        />
        <div v-if="preview.length" class="table-preview panel">
          <div class="panel-head"><h3>识别预览（前 8 行）</h3><span class="mono-label">XLSX PREVIEW</span></div>
          <div class="table-wrap">
            <table class="table">
              <tbody>
                <tr v-for="(row, rowIndex) in preview" :key="rowIndex">
                  <td v-for="(cell, cellIndex) in row" :key="cellIndex" :class="{ 'header-cell': rowIndex === 0 }">
                    {{ cell }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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

.table-preview {
  margin-top: 12px;
  overflow: hidden;
}

.table-preview .panel-head h3 {
  font-size: 13px;
}

.header-cell {
  font-weight: 600;
  color: var(--ink);
  background: var(--surface-2);
}
</style>
