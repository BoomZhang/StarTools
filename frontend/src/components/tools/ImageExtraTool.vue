<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ServerResultPanel from '@/components/ServerResultPanel.vue'
import StitchBoard from '@/components/StitchBoard.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { useServerTask } from '@/composables/useServerTask'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()

const files = ref<File[]>([])
const watermarkFile = ref<File[]>([])
const mode = ref<'text' | 'image'>('text')
const text = ref('仅限内部使用')
const fontSize = ref(36)
const color = ref('#FFFFFF')
const opacity = ref(60)
const position = ref('bottom-right')
const tile = ref(false)
const direction = ref<'horizontal' | 'vertical' | 'grid'>('horizontal')
const columns = ref(2)
const gap = ref(8)
const background = ref('#FFFFFF')
const format = ref<'png' | 'jpg' | 'webp'>('png')
const quality = ref(92)

const isServer = computed(() => props.tool.engine === 'server')
const isWatermark = computed(() => props.tool.code === 'IMG-04')
const isStitch = computed(() => props.tool.code === 'IMG-05')
const isIcon = computed(() => props.tool.code === 'IMG-07')

const uploadFiles = computed(() =>
  isWatermark.value && mode.value === 'image' && watermarkFile.value[0]
    ? [...files.value, watermarkFile.value[0]]
    : files.value,
)

const params = computed(() => {
  if (isWatermark.value) {
    return {
      mode: mode.value,
      watermark_last: mode.value === 'image',
      text: text.value,
      font_size: fontSize.value,
      color: color.value,
      opacity: opacity.value,
      position: position.value,
      tile: tile.value,
    }
  }
  if (isStitch.value) {
    return {
      direction: direction.value,
      columns: columns.value,
      gap: gap.value,
      background: background.value,
      format: format.value,
      quality: quality.value,
    }
  }
  return {}
})

const canRun = computed(() => {
  if (!props.tool.available || !isServer.value || server.busy.value) return false
  if (!accepted.value) return false
  if (isWatermark.value) {
    if (!files.value.length) return false
    if (mode.value === 'image' && !watermarkFile.value.length) return false
    if (mode.value === 'text' && !text.value.trim()) return false
    return true
  }
  if (isStitch.value) return files.value.length >= 2
  return files.value.length === 1
})

const hint = computed(() => {
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!accepted.value) return '请先确认上传说明'
  if (isWatermark.value) {
    if (!files.value.length) return '请先选择待加水印的图片'
    if (mode.value === 'text' && !text.value.trim()) return '请填写水印文字'
    if (mode.value === 'image' && !watermarkFile.value.length) return '请选择水印图片'
    return ''
  }
  if (isStitch.value && files.value.length < 2) return '至少添加 2 张图片'
  if (isIcon.value && !files.value.length) return '请选择一张不小于 256×256 的 PNG 或 JPG'
  return ''
})

const accept = computed(() => (isIcon.value ? '.png,.jpg,.jpeg,image/png,image/jpeg' : 'image/*'))

onMounted(() => {
  if (isServer.value) void server.restore()
})

async function run() {
  if (!canRun.value) return
  await server.run(uploadFiles.value, params.value, { isRetry: server.state.value === 'failed' })
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>{{ isIcon ? '选择源图' : '选择图片' }}</h2>
          </div>
          <span class="section-aside">
            {{ isIcon ? '1 张' : `${files.length} / ${tool.max_count} 张` }}
          </span>
        </div>

        <FilePicker
          v-model="files"
          :multiple="!isIcon"
          :max-count="isIcon ? 1 : tool.max_count"
          :max-file-mb="tool.max_file_mb"
          :accept="accept"
          :title="isIcon ? '选择 PNG / JPG 图标源图' : '拖拽图片到这里，或点击选择'"
          :hint="isIcon ? '源图需不小于 256×256；输出多尺寸 PNG 与 ICO' : `单张上限 ${tool.max_file_mb}MB`"
          :disabled="!tool.available"
          :show-list="!isStitch"
        />

        <template v-if="isWatermark">
          <div class="segmented option-gap">
            <button type="button" :class="{ 'is-active': mode === 'text' }" @click="mode = 'text'">文字水印</button>
            <button type="button" :class="{ 'is-active': mode === 'image' }" @click="mode = 'image'">图片水印</button>
          </div>
          <div v-if="mode === 'image'" class="watermark-file option-gap">
            <FilePicker
              v-model="watermarkFile"
              :max-file-mb="2"
              accept="image/png,image/jpeg,image/webp"
              title="选择水印图片（上限 2MB）"
              hint="水印按原图宽度 20% 缩放，批量使用同一模板"
              :disabled="!tool.available"
            />
          </div>
        </template>

        <StitchBoard
          v-if="isStitch"
          v-model:files="files"
          :direction="direction"
          :columns="columns"
          :gap="gap"
          :background="background"
        />
        <div v-if="isIcon" class="mini-alert option-gap">
          <AppIcon name="info" :size="14" />
          <span>输出 16 / 32 / 48 / 64 / 128 / 256 px 的 6 个 PNG 和一个多尺寸 ICO，打包为 ZIP。</span>
        </div>
      </div>
    </section>

    <section v-if="!isIcon" class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>{{ isWatermark ? '水印参数' : '拼接参数' }}</h2>
          </div>
        </div>

        <template v-if="isWatermark">
          <div v-if="mode === 'text'" class="param-grid">
            <div class="field span-full">
              <span class="field-label"><strong>水印文字</strong><span>{{ text.length }} / 80</span></span>
              <input v-model="text" class="input" maxlength="80" placeholder="例如：仅限内部使用" />
            </div>
            <div class="field">
              <span class="field-label"><strong>字号</strong><span>{{ fontSize }} px</span></span>
              <div class="range-row">
                <input v-model.number="fontSize" type="range" min="12" max="200" />
                <span class="range-value">{{ fontSize }}</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label"><strong>颜色</strong></span>
              <div class="color-field">
                <input v-model="color" type="color" aria-label="水印颜色" />
                <input v-model="color" class="input" aria-label="水印颜色值" />
              </div>
            </div>
          </div>

          <div class="param-grid option-gap">
            <div class="field">
              <span class="field-label"><strong>位置</strong></span>
              <select v-model="position" class="select" :disabled="tile">
                <option value="top-left">左上</option>
                <option value="top-center">上中</option>
                <option value="top-right">右上</option>
                <option value="center-left">左中</option>
                <option value="center">居中</option>
                <option value="center-right">右中</option>
                <option value="bottom-left">左下</option>
                <option value="bottom-center">下中</option>
                <option value="bottom-right">右下</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>透明度</strong><span>{{ opacity }}%</span></span>
              <div class="range-row">
                <input v-model.number="opacity" type="range" min="5" max="100" />
                <span class="range-value">{{ opacity }}%</span>
              </div>
            </div>
            <div class="field span-full">
              <label class="checkbox"><input v-model="tile" type="checkbox" /> 平铺水印（覆盖整张图）</label>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="segmented">
            <button type="button" :class="{ 'is-active': direction === 'horizontal' }" @click="direction = 'horizontal'">横向</button>
            <button type="button" :class="{ 'is-active': direction === 'vertical' }" @click="direction = 'vertical'">纵向</button>
            <button type="button" :class="{ 'is-active': direction === 'grid' }" @click="direction = 'grid'">网格</button>
          </div>
          <div class="param-grid option-gap">
            <div v-if="direction === 'grid'" class="field">
              <span class="field-label"><strong>列数</strong></span>
              <select v-model.number="columns" class="select">
                <option :value="2">2 列</option>
                <option :value="3">3 列</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>间距</strong><span>{{ gap }} px</span></span>
              <div class="range-row">
                <input v-model.number="gap" type="range" min="0" max="50" />
                <span class="range-value">{{ gap }}</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label"><strong>背景色</strong></span>
              <div class="color-field">
                <input v-model="background" type="color" aria-label="背景色" />
                <input v-model="background" class="input" aria-label="背景色值" />
              </div>
            </div>
            <div class="field">
              <span class="field-label"><strong>输出格式</strong></span>
              <select v-model="format" class="select">
                <option value="png">PNG</option>
                <option value="jpg">JPG</option>
                <option value="webp">WebP</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>质量</strong><span>{{ quality }}</span></span>
              <div class="range-row">
                <input v-model.number="quality" type="range" min="60" max="100" />
                <span class="range-value">{{ quality }}</span>
              </div>
            </div>
          </div>
        </template>

        <div class="option-gap">
          <UploadConsentNotice :file-count="uploadFiles.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">
            {{ isWatermark ? '水印不超出画布；批量使用同一模板。' : '总输出像素不超过 80MP，超限时自动等比缩小。' }}
          </p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ server.busy.value ? '处理中…' : isWatermark ? '开始加水印' : '开始拼接' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section v-else class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OUTPUT</span>
            <h2>图标输出</h2>
          </div>
        </div>
        <p class="tool-tip">源图会居中裁切为正方形，再生成 6 种尺寸的 PNG 与 ICO。</p>
        <div class="option-gap">
          <UploadConsentNotice :file-count="uploadFiles.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">结果打包为 ZIP；上传图片仅维护者可访问。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="sparkles" :size="15" />
              {{ server.busy.value ? '生成中…' : '生成图标' }}
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

.watermark-file {
  display: flex;
  flex-direction: column;
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}
</style>
