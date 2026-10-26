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
import { useSite } from '@/composables/useSite'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'
import { fileExtension } from '@/utils/files'
import { convertImageLocal, type LocalFormat, type LocalImageResult } from '@/utils/localImage'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()
const { payload } = useSite()

const files = ref<File[]>([])
const format = ref<LocalFormat>('jpg')
const quality = ref(90)
const background = ref('#FFFFFF')

const localResults = ref<LocalImageResult[]>([])
const localErrors = ref<string[]>([])
const localProcessing = ref(false)
const localProgress = ref(0)

const isServer = computed(() => props.tool.engine === 'server')
const formatOptions = computed(() =>
  isServer.value
    ? payload.value?.site.capabilities?.image_output_formats ?? ['jpg', 'png', 'webp']
    : ['jpg', 'png', 'webp'],
)
const accept = computed(() => props.tool.code === 'IMG-01' ? '.jpg,.jpeg,.png,.webp,.avif,.heic,.heif,.tif,.tiff,.bmp,.gif,.svg,image/*' : 'image/*')

const sameFormat = computed(() => {
  if (!files.value.length) return false
  return files.value.every((file) => {
    const ext = fileExtension(file.name).replace('.', '')
    const normalized = ext === 'jpeg' ? 'jpg' : ext
    return normalized === format.value
  })
})

const canRun = computed(() => {
  if (!files.value.length || !props.tool.available || sameFormat.value) return false
  if (isServer.value) return accepted.value && !server.busy.value
  return !localProcessing.value
})

const hint = computed(() => {
  if (!files.value.length) return '请先选择至少 1 张图片'
  if (sameFormat.value) return '输出格式与输入格式相同，请选择不同的输出格式'
  if (isServer.value && !accepted.value) return '请先确认上传说明'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  return ''
})

const params = computed(() => ({
  format: format.value,
  quality: quality.value,
  background: background.value,
}))

watch([format, quality, background], () => {
  localResults.value = []
  localErrors.value = []
})

watch(formatOptions, (options) => {
  if (!options.includes(format.value)) {
    format.value = (options[0] as LocalFormat) ?? 'jpg'
  }
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
      const result = await convertImageLocal(file, {
        format: format.value,
        quality: quality.value,
        background: background.value,
      })
      results.push(result)
    } catch (err) {
      errors.push(err instanceof Error ? err.message : `${file.name} 处理失败`)
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
    is_retry: localResults.value.length > 0,
  })
}

function retryLocal() {
  void runLocal()
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
          :accept="accept"
          title="拖拽图片到这里，或点击选择"
          :hint="`JPG · PNG · WebP · AVIF · HEIC · TIFF · BMP · GIF · SVG · 单张上限 ${tool.max_file_mb}MB`"
          :disabled="!tool.available"
        />
        <div v-if="!isServer" class="mini-alert option-gap">
          <AppIcon name="monitor" :size="14" />
          <span>当前由浏览器前端处理。HEIC 取决于浏览器解码能力，AVIF 输出不可用时不会出现。</span>
        </div>
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
            <span class="field-label"><strong>输出格式</strong></span>
            <div class="segmented">
              <button
                v-for="item in formatOptions"
                :key="item"
                type="button"
                :class="{ 'is-active': format === item }"
                @click="format = item as LocalFormat"
              >
                {{ item.toUpperCase() }}
              </button>
            </div>
          </div>
          <div v-if="['jpg', 'webp', 'avif'].includes(format)" class="field">
            <span class="field-label"><strong>质量</strong><span>{{ quality }}</span></span>
            <div class="range-row">
              <input v-model.number="quality" type="range" min="60" max="100" />
              <span class="range-value">{{ quality }}</span>
            </div>
          </div>
          <div v-if="format === 'jpg'" class="field">
            <span class="field-label"><strong>透明区域填充</strong></span>
            <div class="color-field">
              <input v-model="background" type="color" aria-label="填充色" />
              <input v-model="background" class="input" aria-label="填充色值" />
            </div>
          </div>
        </div>
        <div v-if="sameFormat" class="mini-alert danger option-gap">
          <AppIcon name="alert" :size="14" />
          <span>输出格式与当前所有输入格式相同。请选择不同的输出格式，不做无意义的同格式重编码。</span>
        </div>
        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">
            {{ isServer ? '服务端统一移除 EXIF、GPS 与设备信息；动画只取首帧。' : '前端处理不上传文件，EXIF 与位置信息不会保留在输出中。' }}
          </p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ server.busy.value ? '处理中…' : '开始转换' }}
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
        idle-text="选择图片并设置输出格式，转换结果会显示在这里。"
        @clear="clearLocal"
      />
      <div v-if="!isServer && (localResults.length || localErrors.length)" class="local-retry">
        <button class="button button-ghost button-sm" type="button" @click="retryLocal">
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

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}

.local-retry {
  margin-top: 10px;
}
</style>
