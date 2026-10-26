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
const rotate = ref(0)
const removePages = ref('')
const extractPages = ref('')
const order = ref('')
const level = ref<'light' | 'balanced' | 'max'>('balanced')
const passwordMode = ref<'add' | 'remove'>('add')
const password = ref('')
const confirmPassword = ref('')

const isServer = computed(() => props.tool.engine === 'server')
const isPages = computed(() => props.tool.code === 'DOC-05')
const isCompress = computed(() => props.tool.code === 'DOC-06')
const isOffice = computed(() => props.tool.code === 'DOC-07')
const isWord = computed(() => props.tool.code === 'DOC-08')
const isPassword = computed(() => props.tool.code === 'DOC-09')

const accept = computed(() =>
  isOffice.value
    ? '.docx,.xlsx,.pptx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.presentationml.presentation'
    : 'application/pdf,.pdf',
)

const passwordError = computed(() => {
  if (!isPassword.value) return ''
  if (!password.value) return '请输入密码'
  if (password.value.length > 64) return '密码不能超过 64 个字符'
  if (passwordMode.value === 'add' && password.value !== confirmPassword.value) return '两次输入的密码不一致'
  return ''
})

const canRun = computed(() => {
  if (!props.tool.available || !isServer.value || !accepted.value || server.busy.value) return false
  if (files.value.length !== 1) return false
  if (isPassword.value && passwordError.value) return false
  return true
})

const hint = computed(() => {
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (files.value.length !== 1) return isOffice.value ? '请选择 1 个 Office 文件' : '请选择 1 个 PDF'
  if (!accepted.value) return '请先确认上传说明'
  if (passwordError.value) return passwordError.value
  return ''
})

const params = computed(() => {
  if (isPages.value) {
    return {
      rotate: rotate.value,
      remove: removePages.value,
      extract: extractPages.value,
      order: order.value,
    }
  }
  if (isCompress.value) return { level: level.value }
  if (isPassword.value) return { mode: passwordMode.value, password: password.value }
  return {}
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
            <h2>{{ isOffice ? '选择 Office 文件' : '选择 PDF' }}</h2>
          </div>
          <span class="section-aside">单文件 ≤ {{ tool.max_file_mb }}MB</span>
        </div>
        <FilePicker
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          :accept="accept"
          :title="isOffice ? '拖拽 DOCX / XLSX / PPTX 到这里' : '拖拽 PDF 到这里，或点击选择'"
          :hint="isOffice ? '支持 DOCX、XLSX、PPTX；宏与嵌入脚本不会执行' : `上限 ${tool.max_file_mb}MB · 加密 PDF 请先移除密码`"
          :disabled="!tool.available"
        />
        <div v-if="isWord" class="mini-alert option-gap">
          <AppIcon name="info" :size="14" />
          <span>仅支持文本型 PDF；扫描件请改用 OCR-02。版式为尽力保留。</span>
        </div>
        <div v-if="isCompress" class="mini-alert info option-gap">
          <AppIcon name="info" :size="14" />
          <span>仅对嵌入图片降采样，文字仍保持可选中；原数字签名失效。</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>{{ isPages ? '页面操作' : isCompress ? '压缩档位' : isPassword ? '密码设置' : '处理说明' }}</h2>
          </div>
        </div>

        <template v-if="isPages">
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>旋转</strong></span>
              <select v-model.number="rotate" class="select">
                <option :value="0">不旋转</option>
                <option :value="90">顺时针 90°</option>
                <option :value="180">180°</option>
                <option :value="270">顺时针 270°</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>删除页码</strong><span>可留空</span></span>
              <input v-model="removePages" class="input input-mono" placeholder="例如 2,4-5" />
            </div>
            <div class="field">
              <span class="field-label"><strong>抽取页码</strong><span>可留空</span></span>
              <input v-model="extractPages" class="input input-mono" placeholder="例如 1-3,5" />
            </div>
            <div class="field">
              <span class="field-label"><strong>自定义顺序</strong><span>可留空</span></span>
              <input v-model="order" class="input input-mono" placeholder="例如 3,1,2" />
            </div>
          </div>
          <p class="tool-tip option-gap">抽取与自定义顺序同时填写时，以抽取结果为准；删除在抽取后执行。</p>
        </template>

        <template v-else-if="isCompress">
          <div class="segmented">
            <button type="button" :class="{ 'is-active': level === 'light' }" @click="level = 'light'">轻</button>
            <button type="button" :class="{ 'is-active': level === 'balanced' }" @click="level = 'balanced'">推荐</button>
            <button type="button" :class="{ 'is-active': level === 'max' }" @click="level = 'max'">极致</button>
          </div>
          <p class="tool-tip option-gap">档位越高，图片分辨率与质量越低；文字层保持不变。</p>
        </template>

        <template v-else-if="isPassword">
          <div class="segmented">
            <button type="button" :class="{ 'is-active': passwordMode === 'add' }" @click="passwordMode = 'add'">添加密码</button>
            <button type="button" :class="{ 'is-active': passwordMode === 'remove' }" @click="passwordMode = 'remove'">移除密码</button>
          </div>
          <div class="param-grid option-gap">
            <div class="field">
              <span class="field-label"><strong>密码</strong><span>1–64 字符</span></span>
              <input v-model="password" class="input" type="password" autocomplete="new-password" placeholder="输入密码" />
            </div>
            <div v-if="passwordMode === 'add'" class="field">
              <span class="field-label"><strong>确认密码</strong></span>
              <input v-model="confirmPassword" class="input" type="password" autocomplete="new-password" placeholder="再次输入" />
            </div>
          </div>
          <p v-if="passwordError" class="field-error">{{ passwordError }}</p>
          <div class="mini-alert option-gap">
            <AppIcon name="alert" :size="14" />
            <span>密码不会写入日志、使用记录或操作记录；遗失密码后无法恢复。添加密码使用 AES-256。</span>
          </div>
        </template>

        <template v-else>
          <p class="tool-tip">
            {{ isOffice ? '转换使用服务端 Office 引擎；字体缺失可能导致版式变化。' : '提取 PDF 文本并生成 DOCX；扫描件会建议改用 OCR-02。' }}
          </p>
        </template>

        <div class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">
            {{ isPages ? '结果区会显示页数；原签名、书签与表单不保留。' : isPassword ? '操作不可撤销，请确认密码。' : '上传文件仅维护者可访问。' }}
          </p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon name="file" :size="15" />
              {{
                server.busy.value
                  ? '处理中…'
                  : isPages
                    ? '保存页面'
                    : isCompress
                      ? '开始压缩'
                      : isOffice
                        ? '转换为 PDF'
                        : isWord
                          ? '转换为 Word'
                          : passwordMode === 'add'
                            ? '添加密码'
                            : '移除密码'
              }}
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

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
}

.field-error {
  margin-top: 8px;
  color: var(--danger);
  font-size: 10.5px;
}
</style>
