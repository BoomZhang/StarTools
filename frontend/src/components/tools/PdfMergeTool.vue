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
const isServer = computed(() => props.tool.engine === 'server')
const canRun = computed(
  () => files.value.length >= 2 && props.tool.available && accepted.value && !server.busy.value && isServer.value,
)
const hint = computed(() => {
  if (files.value.length < 2) return '至少添加 2 份 PDF'
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (!accepted.value) return '请先确认上传说明'
  return ''
})

onMounted(() => {
  if (isServer.value) void server.restore()
})

async function run() {
  if (!canRun.value) return
  await server.run(files.value, {}, { isRetry: server.state.value === 'failed' })
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>添加 PDF</h2>
          </div>
          <span class="section-aside">{{ files.length }} / {{ tool.max_count }} 份</span>
        </div>
        <FilePicker
          v-model="files"
          multiple
          :max-count="tool.max_count"
          :max-file-mb="tool.max_file_mb"
          accept="application/pdf,.pdf"
          title="拖拽 PDF 到这里，或点击选择"
          :hint="`至少 2 份 · 单份上限 ${tool.max_file_mb}MB · 合计不超过 500 页`"
          :disabled="!tool.available"
        />
        <p class="merge-note">按列表顺序合并；可上移/下移调整顺序。合并后页面尺寸保持原样。</p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / RULES</span>
            <h2>合并说明</h2>
          </div>
        </div>
        <ul class="merge-rules">
          <li>加密 PDF 会被拒绝，并指出具体文件名；不提供忽略密码的选项。</li>
          <li>书签、表单、注释与链接不保证保留，原数字签名会失效。</li>
          <li>不同页面尺寸可以混排，不会自动缩放或重排为 A4。</li>
        </ul>
        <div v-if="isServer" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">结果区显示总页数、文件大小，并提示签名失效。</p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="file" :size="15" />
              {{ server.busy.value ? '合并中…' : '合并 PDF' }}
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

.merge-note {
  margin-top: 9px;
  color: var(--faint);
  font-size: 10.5px;
}

.merge-rules {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.merge-rules li {
  position: relative;
  padding-left: 13px;
}

.merge-rules li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--line-strong);
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}
</style>
