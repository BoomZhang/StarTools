<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import LocalImageResults from '@/components/LocalImageResults.vue'
import ServerResultPanel from '@/components/ServerResultPanel.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { reportUsage } from '@/api/feedback'
import { useServerTask } from '@/composables/useServerTask'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'
import { formatBytes } from '@/utils/format'
import { compressImageLocal, type LocalImageResult } from '@/utils/localImage'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()

const files = ref<File[]>([])
const mode = ref<'quality' | 'target'>('quality')
const quality = ref(80)
const targetKB = ref(200)
const allowWebp = ref(true)

const localResults = ref<LocalImageResult[]>([])
const localErrors = ref<string[]>([])
const localProcessing = ref(false)
const localProgress = ref(0)

const isServer = computed(() => props.tool.engine === 'server')
const targetTooLarge = computed(() => {
  if (mode.value !== 'target' || !files.value.length) return false
  return targetKB.value * 1024 >= files.value[0].size
})
const canRun = computed(() => {
  if (!files.value.length || !props.tool.available || targetTooLarge.value) return false
  if (isServer.value) return accepted.value && !server.busy.value
  return !localProcessing.value
})
const hint = computed(() => {
  if (!files.value.length) return '请先选择图片'
  if (targetTooLarge.value) return '目标大小不小于原文件，无需压缩'
  if (isServer.value && !accepted.value) return '请先确认上传说明'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  return ''
})
const params = computed(() => ({
  mode: mode.value,
  quality: quality.value,
  target_kb: targetKB.value,
  allow_webp: allowWebp.value,
}))

watch([mode, quality, targetKB, allowWebp], () => {
  localResults.value = []
  localErrors.value = []
})

onMounted(() => {
  if (isServer.value) void server.restore()
})

async function run() {
  if (!canRun.value) return
  if (isServer.value) {
    await server.run(files.value, params.value, { isRetry: server.state.value === 'failed' })
    return
  }
  await runLocal()
}

async function runLocal() {
  const wasRetry = localResults.value.length > 0 || localErrors.value.length > 0
  localProcessing.value = true
  localProgress.value = 0
  localResults.value = []
  localErrors.value = []
  const started = performance.now()
  const results: LocalImageResult[] = []
  const errors: string[] = []
  for (let index = 0; index < files.value.length; index += 1) {
    const file = files.value[index]
    try {
      results.push(
        await compressImageLocal(file, {
          mode: mode.value,
          quality: quality.value,
          targetKB: targetKB.value,
          allowWebp: allowWebp.value,
        }),
      )
    } catch (err) {
      errors.push(err instanceof Error ? err.message : `${file.name} 压缩失败`)
    }
    localProgress.value = Math.round(((index + 1) / files.value.length) * 100)
    localResults.value = [...results]
  }
  localErrors.value = errors
  localProcessing.value = false
  void reportUsage({
    tool_code: props.tool.code,
    result: results.length && errors.length ? 'partial' : results.length ? 'succeeded' : 'failed',
    duration_ms: Math.round(performance.now() - started),
    file_count: files.value.length,
    total_size: files.value.reduce((sum, file) => sum + file.size, 0),
    error_code: results.length ? undefined : 'E3-422',
    is_retry: wasRetry,
  })
}

function clearLocal() {
  localResults.value = []
  localErrors.value = []
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>选择图片</h2>
          </div>
          <span class="section-aside">{{ files.length }} / {{ tool.max_count }} 张</span>
        </div>
        <FilePicker
          v-model="files"
          :multiple="tool.max_count > 1"
          :max-count="tool.max_count"
          :max-file-mb="tool.max_file_mb"
          accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/heif,image/tiff,image/bmp,image/gif,image/*"
          title="拖拽图片到这里，或点击选择"
          :hint="`JPG · PNG · WebP · AVIF · 单张上限 ${tool.max_file_mb}MB`"
          :disabled="!tool.available"
        />
        <div v-if="files.length && mode === 'target'" class="file-size-note">
          第一张原文件：{{ formatBytes(files[0].size) }}；目标 {{ targetKB }} KB
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>压缩方式</h2>
          </div>
        </div>
        <div class="segmented">
          <button type="button" :class="{ 'is-active': mode === 'quality' }" @click="mode = 'quality'">按质量</button>
          <button type="button" :class="{ 'is-active': mode === 'target' }" @click="mode = 'target'">按目标大小</button>
        </div>

        <div v-if="mode === 'quality'" class="field option-gap">
          <span class="field-label"><strong>质量</strong><span>1–100，默认 80</span></span>
          <div class="range-row">
            <input v-model.number="quality" type="range" min="1" max="100" />
            <span class="range-value">{{ quality }}</span>
          </div>
          <p class="tool-tip">PNG 在质量模式下执行无损重编码，压缩幅度有限。</p>
        </div>

        <div v-else class="param-grid option-gap">
          <div class="field">
            <span class="field-label"><strong>目标大小</strong><span>10KB–5MB</span></span>
            <div class="input-row">
              <input v-model.number="targetKB" class="input input-mono" type="number" min="10" max="5120" />
              <span class="unit">KB</span>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>PNG 目标大小模式</strong></span>
            <label class="checkbox">
              <input v-model="allowWebp" type="checkbox" />
              允许转为 WebP
            </label>
          </div>
        </div>

        <div v-if="mode === 'target' && allowWebp" class="mini-alert info option-gap">
          <AppIcon name="info" :size="14" />
          <span>PNG 图片在目标大小模式下会转为 WebP；其他格式保持原格式，最低质量 40。</span>
        </div>
        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">结果不小于原文件时保留原文件并标记「已是最优」，不计为失败。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ server.busy.value ? '处理中…' : '开始压缩' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <ServerResultPanel
        v-if="isServer"
        :tool="tool"
        :task="server.task.value"
        :state="server.state.value"
        :progress="server.progress.value"
        :error="server.error.value"
        :restoring="server.restoring.value"
        @retry="run"
        @delete="server.removeResults"
      />
      <LocalImageResults
        v-else
        :results="localResults"
        :processing="localProcessing"
        :progress="localProgress"
        :errors="localErrors"
        idle-text="选择图片并设置压缩方式，压缩率与结果大小会显示在这里。"
        @clear="clearLocal"
      />
      <div v-if="!isServer && (localResults.length || localErrors.length)" class="local-retry">
        <button class="button button-ghost button-sm" type="button" @click="run">
          <AppIcon name="refresh" :size="13" />
          重新处理
        </button>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.option-gap {
  margin-top: 14px;
}

.file-size-note {
  margin-top: 9px;
  color: var(--faint);
  font-size: 10.5px;
}

.unit {
  flex: none;
  color: var(--faint);
  font-size: 11px;
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}

.local-retry {
  margin-top: 10px;
}
</style>
