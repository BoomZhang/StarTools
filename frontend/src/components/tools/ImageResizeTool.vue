<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ImageCropEditor from '@/components/ImageCropEditor.vue'
import LocalImageResults from '@/components/LocalImageResults.vue'
import ServerResultPanel from '@/components/ServerResultPanel.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { reportUsage } from '@/api/feedback'
import { useServerTask } from '@/composables/useServerTask'
import { useSite } from '@/composables/useSite'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { CropRect, Tool } from '@/types'
import { imageDimensions, resizeImageLocal, type LocalFormat, type LocalImageResult } from '@/utils/localImage'

type FormatValue = 'auto' | LocalFormat | 'gif' | 'bmp' | 'tiff'
type CropPreset = 'free' | '1:1' | '4:3' | '16:9' | 'original'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()
const { payload } = useSite()

const files = ref<File[]>([])
const mode = ref<'crop' | 'pixel' | 'percent' | 'preset'>('pixel')
const width = ref(1280)
const height = ref(720)
const percent = ref(100)
const preset = ref('1080x1080')
const lockRatio = ref(true)
const fit = ref<'contain' | 'cover' | 'stretch'>('contain')
const background = ref('#FFFFFF')
const format = ref<FormatValue>('auto')
const quality = ref(90)
const crop = ref<CropRect>({ x: 0, y: 0, width: 1, height: 1 })
const cropPreset = ref<CropPreset>('free')

const aspect = ref<number | null>(null)
const originalSize = ref<{ width: number; height: number } | null>(null)

const localResults = ref<LocalImageResult[]>([])
const localErrors = ref<string[]>([])
const localProcessing = ref(false)
const localProgress = ref(0)

const isServer = computed(() => props.tool.engine === 'server')

const cropRatio = computed(() => {
  if (cropPreset.value === 'free') return null
  if (cropPreset.value === 'original') return aspect.value
  return { '1:1': 1, '4:3': 4 / 3, '16:9': 16 / 9 }[cropPreset.value] ?? null
})

const hasCrop = computed(
  () =>
    crop.value.x > 0.001 ||
    crop.value.y > 0.001 ||
    crop.value.width < 0.999 ||
    crop.value.height < 0.999,
)

const croppedSize = computed(() => {
  if (!originalSize.value) return null
  return {
    width: Math.max(1, Math.round(originalSize.value.width * crop.value.width)),
    height: Math.max(1, Math.round(originalSize.value.height * crop.value.height)),
  }
})

const formatOptions = computed(() => {
  const options: { value: FormatValue; label: string }[] = [
    { value: 'auto', label: '与输入一致' },
    { value: 'jpg', label: 'JPG' },
    { value: 'png', label: 'PNG' },
    { value: 'webp', label: 'WebP' },
  ]
  const supported = payload.value?.site.capabilities.image_output_formats ?? []
  if (isServer.value) {
    if (supported.includes('avif')) options.push({ value: 'avif', label: 'AVIF' })
    if (supported.includes('gif')) options.push({ value: 'gif', label: 'GIF（静态）' })
    if (supported.includes('bmp')) options.push({ value: 'bmp', label: 'BMP' })
    if (supported.includes('tiff')) options.push({ value: 'tiff', label: 'TIFF' })
  }
  return options
})

watch(formatOptions, (options) => {
  if (!options.some((item) => item.value === format.value)) format.value = 'auto'
})

const upscaleWarning = computed(() => {
  if (!originalSize.value) return false
  if (mode.value === 'crop') return false
  const sourceWidth = Math.max(1, Math.round(originalSize.value.width * crop.value.width))
  const sourceHeight = Math.max(1, Math.round(originalSize.value.height * crop.value.height))
  const sourceArea = sourceWidth * sourceHeight
  let area = 0
  if (mode.value === 'pixel') area = width.value * height.value
  else if (mode.value === 'percent') area = sourceArea * (percent.value / 100) ** 2
  else {
    const [presetWidth, presetHeight] = preset.value.split('x').map(Number)
    area = presetWidth * presetHeight
  }
  return area > sourceArea * 4
})

const canRun = computed(() => {
  if (!files.value.length || !props.tool.available) return false
  if (mode.value === 'pixel' && (!width.value || !height.value || width.value > 10000 || height.value > 10000)) return false
  if (mode.value === 'percent' && (percent.value < 1 || percent.value > 400)) return false
  if (isServer.value) return accepted.value && !server.busy.value
  return !localProcessing.value
})

const hint = computed(() => {
  if (!files.value.length) return '请先选择图片'
  if (mode.value === 'pixel' && (!width.value || !height.value)) return '请填写目标宽度与高度'
  if (mode.value === 'pixel' && (width.value > 10000 || height.value > 10000)) return '宽高需在 1–10000px 之间'
  if (isServer.value && !accepted.value) return '请先确认上传说明'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  return ''
})

const cropParams = computed(() =>
  hasCrop.value
    ? {
        crop_x: crop.value.x,
        crop_y: crop.value.y,
        crop_width: crop.value.width,
        crop_height: crop.value.height,
      }
    : {},
)

const params = computed(() => ({
  mode: mode.value,
  width: width.value,
  height: height.value,
  percent: percent.value,
  preset: preset.value,
  fit: fit.value,
  background: background.value,
  format: format.value,
  quality: quality.value,
  ...cropParams.value,
}))

watch(
  files,
  async () => {
    localResults.value = []
    localErrors.value = []
    crop.value = { x: 0, y: 0, width: 1, height: 1 }
    cropPreset.value = 'free'
    const file = files.value[0]
    if (!file) {
      aspect.value = null
      originalSize.value = null
      return
    }
    try {
      const size = await imageDimensions(file)
      originalSize.value = size
      aspect.value = size.width / size.height
    } catch {
      aspect.value = null
      originalSize.value = null
    }
  },
  { deep: false },
)

watch(width, (value) => {
  if (!lockRatio.value || !aspect.value) return
  height.value = Math.max(1, Math.min(10000, Math.round(value / aspect.value)))
})

watch([mode, percent, preset, fit, background, format, quality], () => {
  localResults.value = []
  localErrors.value = []
})

watch(
  crop,
  () => {
    localResults.value = []
    localErrors.value = []
  },
  { deep: true },
)

function localFormat(): 'auto' | LocalFormat {
  return format.value === 'auto' ||
    format.value === 'jpg' ||
    format.value === 'png' ||
    format.value === 'webp' ||
    format.value === 'avif'
    ? format.value
    : 'auto'
}

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
        await resizeImageLocal(file, {
          mode: mode.value,
          width: width.value,
          height: height.value,
          percent: percent.value,
          preset: preset.value,
          fit: fit.value,
          background: background.value,
          format: localFormat(),
          quality: quality.value,
          crop: hasCrop.value ? { ...crop.value } : undefined,
        }),
      )
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
          :hint="`单张上限 ${tool.max_file_mb}MB · 单张不超过 80MP`"
          :disabled="!tool.available"
        />
        <p v-if="originalSize" class="original-size">
          第一张原图：{{ originalSize.width }} × {{ originalSize.height }} px
          <template v-if="hasCrop && croppedSize"> · 裁剪后 {{ croppedSize.width }} × {{ croppedSize.height }} px</template>
        </p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>尺寸与裁剪</h2>
          </div>
        </div>

        <div v-if="files.length" class="crop-block">
          <div class="crop-ratio-bar">
            <span class="mono-label">裁剪比例</span>
            <div class="segmented segmented-sm">
              <button type="button" :class="{ 'is-active': cropPreset === 'free' }" @click="cropPreset = 'free'">自由</button>
              <button type="button" :class="{ 'is-active': cropPreset === '1:1' }" @click="cropPreset = '1:1'">1:1</button>
              <button type="button" :class="{ 'is-active': cropPreset === '4:3' }" @click="cropPreset = '4:3'">4:3</button>
              <button type="button" :class="{ 'is-active': cropPreset === '16:9' }" @click="cropPreset = '16:9'">16:9</button>
              <button type="button" :class="{ 'is-active': cropPreset === 'original' }" @click="cropPreset = 'original'">原图</button>
            </div>
          </div>
          <ImageCropEditor :file="files[0]" :ratio="cropRatio" v-model="crop" :disabled="!tool.available" />
        </div>

        <div class="segmented option-gap">
          <button type="button" :class="{ 'is-active': mode === 'crop' }" @click="mode = 'crop'">仅裁剪</button>
          <button type="button" :class="{ 'is-active': mode === 'pixel' }" @click="mode = 'pixel'">按像素</button>
          <button type="button" :class="{ 'is-active': mode === 'percent' }" @click="mode = 'percent'">按百分比</button>
          <button type="button" :class="{ 'is-active': mode === 'preset' }" @click="mode = 'preset'">常用尺寸</button>
        </div>

        <p v-if="mode === 'crop'" class="tool-tip option-gap">
          输出尺寸等于裁剪框内区域；拖动裁剪框选择区域，四角手柄调整大小。
        </p>

        <div v-if="mode === 'pixel'" class="param-grid option-gap">
          <div class="field">
            <span class="field-label"><strong>宽度</strong><span>1–10000 px</span></span>
            <input v-model.number="width" class="input input-mono" type="number" min="1" max="10000" />
          </div>
          <div class="field">
            <span class="field-label"><strong>高度</strong><span>1–10000 px</span></span>
            <input v-model.number="height" class="input input-mono" type="number" min="1" max="10000" :disabled="lockRatio" />
          </div>
        </div>

        <div v-else-if="mode === 'percent'" class="field option-gap">
          <span class="field-label"><strong>缩放比例</strong><span>1–400%</span></span>
          <div class="range-row">
            <input v-model.number="percent" type="range" min="1" max="400" />
            <span class="range-value">{{ percent }}%</span>
          </div>
        </div>

        <div v-else-if="mode === 'preset'" class="field option-gap">
          <span class="field-label"><strong>常用尺寸</strong></span>
          <select v-model="preset" class="select">
            <option value="1080x1080">1080 × 1080</option>
            <option value="1920x1080">1920 × 1080</option>
            <option value="1280x720">1280 × 720</option>
            <option value="750x1000">750 × 1000</option>
          </select>
        </div>

        <div class="param-grid option-gap">
          <div class="field">
            <span class="field-label"><strong>适配方式</strong></span>
            <select v-model="fit" class="select">
              <option value="contain">等比缩放并留白</option>
              <option value="cover">裁剪填充（居中）</option>
              <option value="stretch">拉伸</option>
            </select>
          </div>
          <div class="field">
            <span class="field-label"><strong>输出格式</strong></span>
            <select v-model="format" class="select">
              <option v-for="item in formatOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </div>
          <div class="field">
            <span class="field-label"><strong>留白背景</strong></span>
            <div class="color-field">
              <input v-model="background" type="color" aria-label="背景色" />
              <input v-model="background" class="input" aria-label="背景色值" />
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>质量</strong><span>{{ quality }}</span></span>
            <div class="range-row">
              <input v-model.number="quality" type="range" min="60" max="100" />
              <span class="range-value">{{ quality }}</span>
            </div>
          </div>
        </div>

        <div class="inline-options option-gap">
          <label class="checkbox">
            <input v-model="lockRatio" type="checkbox" />
            锁定宽高比（按第一张图片）
          </label>
        </div>

        <div v-if="upscaleWarning" class="mini-alert option-gap">
          <AppIcon name="alert" :size="14" />
          <span>目标尺寸超过原图 200%，会明显损失清晰度；仍可继续处理。</span>
        </div>
        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">先按 EXIF 方向校正，再按裁剪框裁剪并缩放；批量参数对所有图片一致。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ server.busy.value ? '处理中…' : '开始调整' }}
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
        idle-text="选择图片并设置尺寸参数，新的尺寸会显示在这里。"
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

.crop-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.crop-ratio-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.crop-ratio-bar .mono-label {
  color: var(--faint);
  font-size: 8.5px;
}

.segmented-sm {
  flex: 1;
}

.segmented-sm button {
  min-height: 32px;
  padding: 0 12px;
  font-size: 11.5px;
}

.original-size {
  margin-top: 9px;
  color: var(--faint);
  font-size: 10.5px;
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}

.local-retry {
  margin-top: 10px;
}
</style>
