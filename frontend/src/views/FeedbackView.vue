<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { parseApiError } from '@/api/client'
import { submitFeedback } from '@/api/feedback'
import { useSite } from '@/composables/useSite'
import { FEEDBACK_TYPES } from '@/data/feedback'
import type { FeedbackReceipt } from '@/types'
import { formatDateTime } from '@/utils/format'
import { takeFeedbackPrefill, type FeedbackPrefill } from '@/utils/feedbackPrefill'

const { payload, load } = useSite()
const router = useRouter()

const type = ref('bug')
const toolCode = ref('unsure')
const description = ref('')
const expected = ref('')
const contact = ref('')
const prefill = ref<FeedbackPrefill | null>(null)
const submitting = ref(false)
const error = ref('')
const retryAt = ref('')
const receipt = ref<FeedbackReceipt | null>(null)
const touched = ref(false)
const lastToolCode = ref('')

const browserInfo = computed(() => navigator.userAgent.slice(0, 200))
const viewport = computed(() => `${window.innerWidth}×${window.innerHeight}`)
const pagePath = computed(() => prefill.value?.path || window.location.pathname)

const descriptionCount = computed(() => description.value.length)
const descriptionError = computed(() => {
  const text = description.value.trim()
  if (!text) return '请说明「做了什么、看到什么」'
  if (text.length < 10) return `还需 ${10 - text.length} 个字符（至少 10 个）`
  if (text.length > 2000) return `超出 ${text.length - 2000} 个字符（上限 2000）`
  const compact = text.replace(/\s/g, '')
  if (new Set(compact.split('')).size < 3) return '重复字符无法帮助定位问题，请具体描述'
  return ''
})

const expectedError = computed(() => (expected.value.length > 500 ? '期望结果不能超过 500 个字符' : ''))
const contactError = computed(() => (contact.value.length > 100 ? '联系方式不能超过 100 个字符' : ''))

const canSubmit = computed(
  () =>
    Boolean(FEEDBACK_TYPES.find((item) => item.key === type.value)) &&
    !descriptionError.value &&
    !expectedError.value &&
    !contactError.value &&
    !submitting.value,
)

const toolName = computed(() => {
  if (toolCode.value === 'unsure' || !payload.value) return '不确定'
  return payload.value.tools.find((tool) => tool.code === toolCode.value)?.name ?? toolCode.value
})

onMounted(() => {
  void load()
  prefill.value = takeFeedbackPrefill()
  if (prefill.value?.toolCode) toolCode.value = prefill.value.toolCode
})

async function submit() {
  touched.value = true
  error.value = ''
  retryAt.value = ''
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const result = await submitFeedback({
      type: type.value,
      tool_code: toolCode.value === 'unsure' ? null : toolCode.value,
      description: description.value,
      expected: expected.value.trim() || undefined,
      contact: contact.value.trim() || undefined,
      context: {
        path: pagePath.value,
        tool_code: prefill.value?.toolCode || (toolCode.value === 'unsure' ? undefined : toolCode.value),
        task_id: prefill.value?.taskId,
        error_code: prefill.value?.errorCode,
        browser: browserInfo.value,
        viewport: viewport.value,
      },
    })
    receipt.value = result
    lastToolCode.value = prefill.value?.toolCode || (toolCode.value === 'unsure' ? '' : toolCode.value)
    description.value = ''
    expected.value = ''
    contact.value = ''
    prefill.value = null
    touched.value = false
  } catch (err) {
    const info = parseApiError(err)
    error.value = info.message
    retryAt.value = info.retryAt ? formatDateTime(info.retryAt) : ''
  } finally {
    submitting.value = false
  }
}

function backToTool() {
  const code = lastToolCode.value || prefill.value?.toolCode
  if (code) {
    const tool = payload.value?.tools.find((item) => item.code === code)
    if (tool) {
      void router.push(`/t/${tool.slug}`)
      return
    }
  }
  void router.push('/')
}
</script>

<template>
  <div class="feedback container">
    <header class="feedback-head">
      <p class="eyebrow">FEEDBACK / 问题反馈</p>
      <h1 class="serif">把问题说清楚，<br />比“打不开”更有用。</h1>
      <p>
        反馈会直接进入维护者的管理台。不需要登录，也不会生成公开页面；
        提交后你会得到一个反馈编号，用于维护者定位问题。
      </p>
    </header>

    <div v-if="payload && !payload.site.feedback_enabled" class="feedback-disabled panel">
      <div class="panel-body disabled-body">
        <AppIcon name="message" :size="24" />
        <h2 class="serif">反馈暂不可用</h2>
        <p>维护者暂时关闭了反馈入口。已有反馈仍可在管理台查看；工具本身不受影响。</p>
        <RouterLink to="/" class="button button-ink">返回工具目录</RouterLink>
      </div>
    </div>

    <div v-else-if="receipt" class="receipt panel">
      <div class="panel-body">
        <div class="receipt-stamp">已收到</div>
        <p class="mono-label">FEEDBACK RECEIPT</p>
        <h2 class="serif">{{ receipt.number }}</h2>
        <p class="receipt-time">提交时间：{{ formatDateTime(receipt.created_at) }}</p>
        <p class="receipt-message">{{ receipt.message }}</p>
        <p class="tool-tip">不承诺回复时间，也不提供进度查询；如果留下联系方式，维护者可能线下联系。</p>
        <div class="receipt-actions">
          <button class="button button-ink" type="button" @click="backToTool">返回原工具</button>
          <RouterLink to="/" class="button button-ghost">回到首页</RouterLink>
        </div>
      </div>
    </div>

    <div v-else class="feedback-layout">
      <form class="feedback-form panel" @submit.prevent="submit">
        <div class="panel-head">
          <h2>反馈内容</h2>
          <span class="mono-label">NO ATTACHMENTS · NO LOGIN</span>
        </div>
        <div class="panel-body form-body">
          <div v-if="prefill" class="prefill-box">
            <span class="mono-label">AUTO CONTEXT</span>
            <p>
              已从工具页带入
              <template v-if="prefill.toolCode">工具 <strong>{{ prefill.toolCode }}</strong></template>
              <template v-if="prefill.errorCode"> · 错误 <strong>{{ prefill.errorCode }}</strong></template>
              <template v-if="prefill.taskId"> · 任务 <strong>{{ prefill.taskId }}</strong></template>
              。带入内容不可编辑，不会包含文件名或文本内容。
            </p>
          </div>

          <div class="field">
            <span class="field-label"><strong>问题类型</strong><span>必填</span></span>
            <div class="type-options">
              <label v-for="item in FEEDBACK_TYPES" :key="item.key" class="type-option">
                <input v-model="type" type="radio" :value="item.key" name="feedback-type" />
                <span>{{ item.label }}</span>
              </label>
            </div>
          </div>

          <div class="field">
            <span class="field-label"><strong>关联工具</strong><span>可选</span></span>
            <select v-model="toolCode" class="select">
              <option value="unsure">不确定</option>
              <option v-for="tool in payload?.tools ?? []" :key="tool.code" :value="tool.code">
                {{ tool.code }} · {{ tool.name }}
              </option>
            </select>
          </div>

          <div class="field">
            <span class="field-label">
              <strong>问题描述</strong>
              <span>{{ descriptionCount }} / 2000</span>
            </span>
            <textarea
              v-model="description"
              class="textarea"
              rows="6"
              maxlength="2000"
              placeholder="做了什么、看到什么。例如：合并 3 份 PDF 后，第 3 页顺序与列表相反。"
              @blur="touched = true"
            ></textarea>
            <p v-if="touched && descriptionError" class="field-error">{{ descriptionError }}</p>
            <p class="field-hint">请只描述问题，不要粘贴文件内容、密码或识别结果。</p>
          </div>

          <div class="field">
            <span class="field-label"><strong>期望结果</strong><span>{{ expected.length }} / 500</span></span>
            <textarea v-model="expected" class="textarea" rows="2" maxlength="500" placeholder="原本期望看到什么（可选）"></textarea>
            <p v-if="expectedError" class="field-error">{{ expectedError }}</p>
          </div>

          <div class="field">
            <span class="field-label"><strong>联系方式</strong><span>{{ contact.length }} / 100</span></span>
            <input v-model="contact" class="input" maxlength="100" placeholder="邮箱、微信号等（可选，仅维护者可见）" />
            <p v-if="contactError" class="field-error">{{ contactError }}</p>
          </div>

          <div class="context-box">
            <span class="mono-label">AUTO ATTACHED</span>
            <dl>
              <div><dt>页面</dt><dd>{{ pagePath }}</dd></div>
              <div v-if="prefill?.toolCode"><dt>工具</dt><dd>{{ prefill.toolCode }}</dd></div>
              <div v-if="prefill?.errorCode"><dt>错误编号</dt><dd>{{ prefill.errorCode }}</dd></div>
              <div v-if="prefill?.taskId"><dt>任务编号</dt><dd>{{ prefill.taskId }}</dd></div>
              <div><dt>浏览器</dt><dd>{{ browserInfo }}</dd></div>
              <div><dt>视口</dt><dd>{{ viewport }}</dd></div>
            </dl>
          </div>

          <div v-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>
              {{ error }}
              <template v-if="retryAt">预计 {{ retryAt }} 后可重试。</template>
            </span>
          </div>

          <div class="submit-area">
            <p class="submit-note">
              提交后会记录 IP、浏览器与当前页面信息，仅用于排查问题；反馈内容只有维护者可见。
            </p>
            <button class="button button-ink" type="submit" :disabled="!canSubmit">
              <AppIcon name="message" :size="15" />
              {{ submitting ? '提交中…' : '提交反馈' }}
            </button>
          </div>
        </div>
      </form>

      <aside class="feedback-aside">
        <div class="aside-block">
          <span class="mono-label">WHAT HAPPENS</span>
          <h3 class="serif">提交之后</h3>
          <ol>
            <li><span class="mono-label">01</span> 页面显示反馈编号与提交时间。</li>
            <li><span class="mono-label">02</span> 维护者在管理台查看完整描述与自动上下文。</li>
            <li><span class="mono-label">03</span> 状态从待处理变为处理中、已解决或已忽略。</li>
          </ol>
        </div>
        <div class="aside-block">
          <span class="mono-label">NOT INCLUDED</span>
          <h3 class="serif">不包含什么</h3>
          <p>不接收附件与截图；不记录文件名、文件内容、输入文本、识别结果、密码或哈希值。</p>
          <p>同一 IP、同一工具、相同描述在 10 分钟内视为重复；每小时最多提交 5 条。</p>
        </div>
        <div class="aside-block aside-current">
          <span class="mono-label">CURRENT</span>
          <p>关联工具：<strong>{{ toolName }}</strong></p>
          <p>反馈入口：{{ payload?.site.feedback_enabled ? '开放' : '关闭' }}</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.feedback {
  padding-top: 46px;
  padding-bottom: 30px;
}

.feedback-head {
  max-width: 760px;
  margin-bottom: 32px;
}

.feedback-head h1 {
  margin: 15px 0 16px;
  font-size: clamp(32px, 4.4vw, 50px);
  font-weight: 500;
  line-height: 1.26;
  letter-spacing: -0.015em;
}

.feedback-head > p:not(.eyebrow) {
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.85;
}

.feedback-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(0, 0.7fr);
  gap: 18px;
  align-items: start;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 17px;
}

.prefill-box {
  padding: 11px 13px;
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  background: var(--surface-2);
}

.prefill-box .mono-label {
  color: var(--accent-deep);
  font-size: 8px;
}

.prefill-box p {
  margin-top: 5px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.65;
}

.type-options {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.type-option {
  position: relative;
  cursor: pointer;
}

.type-option input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.type-option span {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-2);
  color: var(--muted);
  font-size: 11.5px;
  transition: border-color 0.2s, background-color 0.2s, color 0.2s;
}

.type-option input:checked + span {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
}

.field-error {
  color: var(--danger);
  font-size: 10.5px;
}

.context-box {
  padding: 12px 13px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-2);
}

.context-box .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.context-box dl {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 8px 0 0;
}

.context-box dl > div {
  display: grid;
  grid-template-columns: 66px 1fr;
  gap: 8px;
}

.context-box dt {
  color: var(--faint);
  font-size: 10px;
}

.context-box dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 9.5px;
  line-height: 1.5;
}

.submit-area {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding-top: 16px;
  border-top: 1px dashed var(--line);
  flex-wrap: wrap;
}

.submit-note {
  max-width: 420px;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.65;
}

.feedback-aside {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.aside-block {
  padding: 17px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.aside-block .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.aside-block h3 {
  margin: 9px 0 11px;
  font-size: 20px;
  font-weight: 500;
}

.aside-block p,
.aside-block li {
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.7;
}

.aside-block ol {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.aside-block li {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 6px;
}

.aside-block li .mono-label {
  color: var(--accent);
  font-size: 8px;
  padding-top: 3px;
}

.aside-block p + p {
  margin-top: 8px;
}

.aside-current {
  background: var(--surface-2);
}

.feedback-disabled,
.receipt {
  max-width: 640px;
}

.disabled-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 32px;
}

.disabled-body svg {
  color: var(--faint);
}

.disabled-body h2 {
  font-size: 30px;
  font-weight: 500;
}

.disabled-body p {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.8;
}

.receipt .panel-body {
  padding: 32px;
}

.receipt-stamp {
  display: inline-block;
  margin-bottom: 18px;
  padding: 5px 13px;
  border: 2px solid var(--accent);
  border-radius: 3px;
  color: var(--accent);
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.1em;
  transform: rotate(-3deg);
}

.receipt .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.receipt h2 {
  margin: 9px 0 8px;
  font-family: var(--font-mono);
  font-size: clamp(24px, 3vw, 34px);
  font-weight: 500;
}

.receipt-time,
.receipt-message {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.receipt-message {
  margin-top: 8px;
}

.receipt .tool-tip {
  margin-top: 12px;
}

.receipt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

@media (max-width: 980px) {
  .feedback-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .feedback-aside {
    order: 2;
  }
}

@media (max-width: 560px) {
  .feedback {
    padding-top: 30px;
  }

  .submit-area .button {
    width: 100%;
  }
}
</style>
