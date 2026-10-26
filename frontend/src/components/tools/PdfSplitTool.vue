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
const mode = ref<'per_page' | 'every_n' | 'range'>('per_page')
const size = ref(1)
const ranges = ref('')

const isServer = computed(() => props.tool.engine === 'server')
const rangeError = computed(() => {
  if (mode.value !== 'range' || !ranges.value.trim()) return ''
  if (!/^[\d\s,，、\-－–—]+$/.test(ranges.value.trim())) return '页码范围只能包含数字、连字符与逗号，例如 1-3,5,8-10'
  return ''
})
const canRun = computed(
  () =>
    files.value.length === 1 &&
    props.tool.available &&
    accepted.value &&
    !server.busy.value &&
    isServer.value &&
    !rangeError.value &&
    (mode.value !== 'every_n' || (size.value >= 1 && size.value <= 100)) &&
    (mode.value !== 'range' || Boolean(ranges.value.trim())),
)
const hint = computed(() => {
  if (files.value.length !== 1) return '请先添加 1 个 PDF'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!accepted.value) return '请先确认上传说明'
  if (rangeError.value) return rangeError.value
  if (mode.value === 'every_n' && (size.value < 1 || size.value > 100)) return '每份页数需在 1–100 之间'
  if (mode.value === 'range' && !ranges.value.trim()) return '请填写页码范围'
  return ''
})

const params = computed(() => ({
  mode: mode.value,
  size: size.value,
  ranges: ranges.value,
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
          <span class="section-aside">单文件 ≤ {{ tool.max_file_mb }}MB</span>
        </div>
        <FilePicker
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          accept="application/pdf,.pdf"
          title="拖拽 PDF 到这里，或点击选择"
          :hint="`单个 PDF · 不超过 500 页 · 上限 ${tool.max_file_mb}MB`"
          :disabled="!tool.available"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / MODE</span>
            <h2>拆分方式</h2>
          </div>
        </div>
        <div class="segmented">
          <button type="button" :class="{ 'is-active': mode === 'per_page' }" @click="mode = 'per_page'">每页一份</button>
          <button type="button" :class="{ 'is-active': mode === 'every_n' }" @click="mode = 'every_n'">每 N 页一份</button>
          <button type="button" :class="{ 'is-active': mode === 'range' }" @click="mode = 'range'">页码范围</button>
        </div>

        <div v-if="mode === 'every_n'" class="field option-gap">
          <span class="field-label"><strong>每份页数</strong><span>1–100</span></span>
          <div class="input-row">
            <input v-model.number="size" class="input input-mono" type="number" min="1" max="100" />
            <span class="unit">页</span>
          </div>
        </div>

        <div v-if="mode === 'range'" class="field option-gap">
          <span class="field-label"><strong>页码范围</strong><span>示例 1-3,5,8-10</span></span>
          <input v-model="ranges" class="input input-mono" placeholder="1-3,5,8-10" />
          <p class="tool-tip">允许区间重叠；不允许逆序或越界。全角逗号与顿号会自动转换为半角。</p>
          <p v-if="rangeError" class="range-error">{{ rangeError }}</p>
        </div>

        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">处理前会显示预计生成份数与页数；多份结果可打包下载 ZIP。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="file" :size="15" />
              {{ server.busy.value ? '拆分中…' : '开始拆分' }}
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

.unit {
  flex: none;
  color: var(--faint);
  font-size: 11px;
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
