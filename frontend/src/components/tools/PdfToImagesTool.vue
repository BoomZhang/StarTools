<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ServerResultPanel from '@/components/ServerResultPanel.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { useServerTask } from '@/composables/useServerTask'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()

const files = ref<File[]>([])
const format = ref<'png' | 'jpg'>('png')
const dpi = ref(144)
const ranges = ref('')

const isServer = computed(() => props.tool.engine === 'server')
const rangeError = computed(() => {
  if (!ranges.value.trim()) return ''
  if (!/^[\d\s,，、\-－–—]+$/.test(ranges.value.trim())) return '页码范围只能包含数字、连字符与逗号，例如 1-5 或 1,3,5'
  return ''
})
const canRun = computed(
  () =>
    files.value.length === 1 &&
    props.tool.available &&
    accepted.value &&
    !server.busy.value &&
    isServer.value &&
    !rangeError.value,
)
const hint = computed(() => {
  if (files.value.length !== 1) return '请先添加 1 个 PDF'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!accepted.value) return '请先确认上传说明'
  if (rangeError.value) return rangeError.value
  return ''
})

const params = computed(() => ({
  format: format.value,
  dpi: dpi.value,
  ranges: ranges.value || 'all',
}))

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
            <h2>选择 PDF</h2>
          </div>
          <span class="section-aside">单次最多 200 页</span>
        </div>
        <FilePicker
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          accept="application/pdf,.pdf"
          title="拖拽 PDF 到这里，或点击选择"
          :hint="`单个 PDF · 上限 ${tool.max_file_mb}MB · 单次最多转换 200 页`"
          :disabled="!tool.available"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>输出参数</h2>
          </div>
        </div>
        <div class="param-grid">
          <div class="field">
            <span class="field-label"><strong>格式</strong></span>
            <div class="segmented">
              <button type="button" :class="{ 'is-active': format === 'png' }" @click="format = 'png'">PNG</button>
              <button type="button" :class="{ 'is-active': format === 'jpg' }" @click="format = 'jpg'">JPG</button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>DPI</strong></span>
            <div class="segmented">
              <button v-for="value in [72, 144, 300]" :key="value" type="button" :class="{ 'is-active': dpi === value }" @click="dpi = value">
                {{ value }}
              </button>
            </div>
          </div>
          <div class="field span-full">
            <span class="field-label"><strong>页码范围</strong><span>留空表示全部</span></span>
            <input v-model="ranges" class="input input-mono" placeholder="例如 1-5 或 1,3,5；不接受重叠区间" />
            <p v-if="rangeError" class="range-error">{{ rangeError }}</p>
          </div>
        </div>
        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">页面背景统一为白色；单页渲染失败不影响其他页。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="image" :size="15" />
              {{ server.busy.value ? '转换中…' : '转换为图片' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
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
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.option-gap {
  margin-top: 14px;
}

.range-error {
  color: var(--danger);
  font-size: 10.5px;
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}
</style>
