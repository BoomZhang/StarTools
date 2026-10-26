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
const page = ref<'a4' | 'letter' | 'original'>('a4')
const orientation = ref<'auto' | 'portrait' | 'landscape'>('auto')
const margin = ref<'none' | 'small' | 'medium'>('small')

const isServer = computed(() => props.tool.engine === 'server')
const canRun = computed(
  () => files.value.length > 0 && props.tool.available && accepted.value && !server.busy.value && isServer.value,
)
const hint = computed(() => {
  if (!files.value.length) return '请先添加至少 1 张图片'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!accepted.value) return '请先确认上传说明'
  return ''
})

const params = computed(() => ({
  page: page.value,
  orientation: orientation.value,
  margin: margin.value,
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
            <h2>添加图片</h2>
          </div>
          <span class="section-aside">{{ files.length }} / {{ tool.max_count }} 张</span>
        </div>
        <FilePicker
          v-model="files"
          multiple
          :max-count="tool.max_count"
          :max-file-mb="tool.max_file_mb"
          accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/gif,image/avif,image/heic,image/heif,image/*"
          title="拖拽图片到这里，或点击选择"
          :hint="`JPG · PNG · WebP · BMP · HEIC · 单张上限 ${tool.max_file_mb}MB`"
          :disabled="!tool.available"
        />
        <p class="page-note">共 {{ files.length }} 张图片，预计生成 {{ files.length }} 页 PDF；可上移/下移调整顺序。</p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / PAGE</span>
            <h2>页面设置</h2>
          </div>
        </div>
        <div class="param-grid">
          <div class="field">
            <span class="field-label"><strong>页面尺寸</strong></span>
            <select v-model="page" class="select">
              <option value="a4">A4</option>
              <option value="letter">Letter</option>
              <option value="original">原图尺寸</option>
            </select>
          </div>
          <div class="field">
            <span class="field-label"><strong>方向</strong></span>
            <select v-model="orientation" class="select">
              <option value="auto">自动</option>
              <option value="portrait">纵向</option>
              <option value="landscape">横向</option>
            </select>
          </div>
          <div class="field">
            <span class="field-label"><strong>边距</strong></span>
            <select v-model="margin" class="select">
              <option value="none">无</option>
              <option value="small">小（10mm）</option>
              <option value="medium">中（20mm）</option>
            </select>
          </div>
        </div>
        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">图片等比缩放并居中，不裁切、不拉伸；透明背景填充白色。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="file" :size="15" />
              {{ server.busy.value ? '生成中…' : '生成 PDF' }}
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

.page-note {
  margin-top: 9px;
  color: var(--faint);
  font-size: 10.5px;
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}
</style>
