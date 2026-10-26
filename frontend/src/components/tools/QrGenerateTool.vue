<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import type { Tool } from '@/types'
import { buildQrContent, byteLength, contrastRatio, generateQrDataUrl, type QrFields, type QrType } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()

const type = ref<QrType>('text')
const fields = reactive<QrFields>({
  text: '',
  url: '',
  wifiSsid: '',
  wifiPassword: '',
  wifiEncryption: 'WPA',
  wifiHidden: false,
  name: '',
  company: '',
  title: '',
  mobile: '',
  phone: '',
  email: '',
  website: '',
  address: '',
  smsNumber: '',
  smsMessage: '',
  emailTo: '',
  emailSubject: '',
  emailBody: '',
  telNumber: '',
})
const size = ref(512)
const level = ref<'L' | 'M' | 'Q' | 'H'>('M')
const margin = ref(4)
const dark = ref('#000000')
const light = ref('#FFFFFF')

const preview = ref('')
const generating = ref(false)
const error = ref('')
const typeNotice = ref('')
const notice = ref('')
let debounceTimer: number | undefined

const typeOptions: { key: QrType; label: string }[] = [
  { key: 'text', label: '文本' },
  { key: 'url', label: '网址' },
  { key: 'wifi', label: 'WiFi' },
  { key: 'vcard', label: '名片' },
  { key: 'sms', label: '短信' },
  { key: 'email', label: '邮件' },
  { key: 'tel', label: '电话' },
]

const content = computed(() => buildQrContent(type.value, fields))
const bytes = computed(() => byteLength(content.value))
const overLimit = computed(() => bytes.value > 1200)
const contrast = computed(() => contrastRatio(dark.value, light.value))
const contrastWarning = computed(() => contrast.value < 3)

const validation = computed(() => {
  if (!content.value.trim()) return '请填写二维码内容'
  if (overLimit.value) return `内容编码后 ${bytes.value} 字节，超过 1200 字节上限`
  if (type.value === 'wifi') {
    if (fields.wifiSsid.length > 32) return 'WiFi 名称需在 1–32 字符之间'
    if (fields.wifiEncryption !== 'nopass' && fields.wifiPassword.length > 63) return 'WiFi 密码不能超过 63 个字符'
  }
  return ''
})

const canGenerate = computed(() => !validation.value)

const finalUrl = computed(() => {
  if (type.value !== 'url' || !fields.url.trim()) return ''
  return content.value
})

watch(
  [type, content, size, level, margin, dark, light],
  () => {
    window.clearTimeout(debounceTimer)
    if (!canGenerate.value) {
      preview.value = ''
      return
    }
    debounceTimer = window.setTimeout(() => {
      void render()
    }, 220)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.clearTimeout(debounceTimer)
})

watch(type, () => {
  notice.value = ''
  typeNotice.value = '已切换内容类型；不适用的字段不会写入二维码，公共字段保留。'
  window.setTimeout(() => {
    typeNotice.value = ''
  }, 2600)
})

async function render() {
  generating.value = true
  error.value = ''
  try {
    preview.value = await generateQrDataUrl(content.value, {
      size: size.value,
      level: level.value,
      margin: margin.value,
      dark: dark.value,
      light: light.value,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '二维码生成失败'
    preview.value = ''
  } finally {
    generating.value = false
  }
}

function report(action: 'download' | 'copy') {
  void reportUsage({
    tool_code: props.tool.code,
    result: 'succeeded',
    duration_ms: 0,
  })
  notice.value = action === 'download' ? '已开始下载 PNG。' : '二维码图片已复制。'
  window.setTimeout(() => {
    notice.value = ''
  }, 2200)
}

function download() {
  if (!preview.value) return
  const stamp = new Date()
    .toLocaleString('zh-CN', { hour12: false })
    .replace(/[/: ]/g, '')
    .slice(0, 12)
  const anchor = document.createElement('a')
  anchor.href = preview.value
  anchor.download = `二维码_${stamp}.png`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  report('download')
}

async function copyImage() {
  if (!preview.value) return
  try {
    if (!navigator.clipboard || typeof ClipboardItem === 'undefined') {
      throw new Error('unsupported')
    }
    const blob = await (await fetch(preview.value)).blob()
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    report('copy')
  } catch {
    notice.value = '当前浏览器不支持复制图片，请下载 PNG。'
    window.setTimeout(() => {
      notice.value = ''
    }, 2400)
  }
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / CONTENT</span>
            <h2>二维码内容</h2>
          </div>
          <span class="section-aside">{{ bytes }} / 1200 字节</span>
        </div>

        <div class="type-tabs">
          <button
            v-for="item in typeOptions"
            :key="item.key"
            type="button"
            :class="{ 'is-active': type === item.key }"
            @click="type = item.key"
          >
            {{ item.label }}
          </button>
        </div>

        <p v-if="typeNotice" class="type-notice">{{ typeNotice }}</p>

        <div class="type-fields">
          <div v-if="type === 'text'" class="field">
            <span class="field-label"><strong>多行文本</strong></span>
            <textarea v-model="fields.text" class="textarea" rows="4" placeholder="输入要编码进二维码的文字…" aria-label="二维码文本"></textarea>
          </div>

          <div v-else-if="type === 'url'" class="field">
            <span class="field-label"><strong>网址</strong></span>
            <input v-model="fields.url" class="input input-mono" placeholder="example.com 或 https://example.com" aria-label="二维码网址" />
            <span v-if="finalUrl" class="field-hint">最终内容：{{ finalUrl }}</span>
          </div>

          <template v-else-if="type === 'wifi'">
            <div class="param-grid">
              <div class="field">
                <span class="field-label"><strong>SSID</strong><span>1–32 字符</span></span>
                <input v-model="fields.wifiSsid" class="input" maxlength="32" placeholder="WiFi 名称" />
              </div>
              <div class="field">
                <span class="field-label"><strong>密码</strong><span>0–63 字符</span></span>
                <input v-model="fields.wifiPassword" class="input" maxlength="63" placeholder="无密码可留空" />
              </div>
              <div class="field">
                <span class="field-label"><strong>加密方式</strong></span>
                <select v-model="fields.wifiEncryption" class="select">
                  <option value="WPA">WPA / WPA2 / WPA3</option>
                  <option value="WEP">WEP</option>
                  <option value="nopass">无密码</option>
                </select>
              </div>
              <div class="field">
                <span class="field-label"><strong>隐藏网络</strong></span>
                <label class="checkbox">
                  <input v-model="fields.wifiHidden" type="checkbox" />
                  该网络不广播 SSID
                </label>
              </div>
            </div>
          </template>

          <template v-else-if="type === 'vcard'">
            <div class="param-grid">
              <div class="field">
                <span class="field-label"><strong>姓名</strong><span>必填</span></span>
                <input v-model="fields.name" class="input" placeholder="姓名" />
              </div>
              <div class="field">
                <span class="field-label"><strong>公司</strong></span>
                <input v-model="fields.company" class="input" placeholder="公司或组织" />
              </div>
              <div class="field">
                <span class="field-label"><strong>职位</strong></span>
                <input v-model="fields.title" class="input" placeholder="职位" />
              </div>
              <div class="field">
                <span class="field-label"><strong>手机</strong></span>
                <input v-model="fields.mobile" class="input" placeholder="手机号码" />
              </div>
              <div class="field">
                <span class="field-label"><strong>电话</strong></span>
                <input v-model="fields.phone" class="input" placeholder="办公电话" />
              </div>
              <div class="field">
                <span class="field-label"><strong>邮箱</strong></span>
                <input v-model="fields.email" class="input" placeholder="name@example.com" />
              </div>
              <div class="field">
                <span class="field-label"><strong>网址</strong></span>
                <input v-model="fields.website" class="input" placeholder="https://example.com" />
              </div>
              <div class="field">
                <span class="field-label"><strong>地址</strong></span>
                <input v-model="fields.address" class="input" placeholder="地址" />
              </div>
            </div>
          </template>

          <template v-else-if="type === 'sms'">
            <div class="field">
              <span class="field-label"><strong>号码</strong><span>必填</span></span>
              <input v-model="fields.smsNumber" class="input input-mono" placeholder="+8613800000000" />
            </div>
            <div class="field">
              <span class="field-label"><strong>短信内容</strong></span>
              <textarea v-model="fields.smsMessage" class="textarea" rows="3" placeholder="可留空"></textarea>
            </div>
          </template>

          <template v-else-if="type === 'email'">
            <div class="field">
              <span class="field-label"><strong>收件人</strong><span>必填</span></span>
              <input v-model="fields.emailTo" class="input input-mono" placeholder="name@example.com" />
            </div>
            <div class="field">
              <span class="field-label"><strong>主题</strong></span>
              <input v-model="fields.emailSubject" class="input" placeholder="可留空" />
            </div>
            <div class="field">
              <span class="field-label"><strong>正文</strong></span>
              <textarea v-model="fields.emailBody" class="textarea" rows="3" placeholder="可留空"></textarea>
            </div>
          </template>

          <div v-else class="field">
            <span class="field-label"><strong>电话号码</strong><span>必填</span></span>
            <input v-model="fields.telNumber" class="input input-mono" placeholder="+86 138 0000 0000" />
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / STYLE</span>
            <h2>外观参数</h2>
          </div>
        </div>
        <div class="param-grid">
          <div class="field">
            <span class="field-label"><strong>尺寸</strong></span>
            <div class="segmented">
              <button v-for="value in [128, 256, 512, 1024]" :key="value" type="button" :class="{ 'is-active': size === value }" @click="size = value">
                {{ value }}
              </button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>容错等级</strong></span>
            <div class="segmented">
              <button v-for="value in ['L', 'M', 'Q', 'H']" :key="value" type="button" :class="{ 'is-active': level === value }" @click="level = value as 'L' | 'M' | 'Q' | 'H'">
                {{ value }}
              </button>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>静区</strong><span>0–8 模块</span></span>
            <div class="range-row">
              <input v-model.number="margin" type="range" min="0" max="8" />
              <span class="range-value">{{ margin }}</span>
            </div>
          </div>
          <div class="field">
            <span class="field-label"><strong>颜色</strong></span>
            <div class="color-pair">
              <div class="color-field">
                <input v-model="dark" type="color" aria-label="前景色" />
                <input v-model="dark" class="input" aria-label="前景色值" />
              </div>
              <div class="color-field">
                <input v-model="light" type="color" aria-label="背景色" />
                <input v-model="light" class="input" aria-label="背景色值" />
              </div>
            </div>
          </div>
        </div>
        <div v-if="contrastWarning" class="mini-alert option-gap">
          <AppIcon name="alert" :size="14" />
          <span>前景与背景对比度仅 {{ contrast }}:1，低于 3:1，扫描可能失败。允许继续生成。</span>
        </div>
        <div class="run-bar">
          <p class="run-note">预览随输入更新；下载的 PNG 与预览一致，不嵌入 Logo 或追踪参数。</p>
          <div class="run-actions">
            <span v-if="validation" class="run-hint">{{ validation }}</span>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 二维码</span>
          <span v-if="preview" class="badge badge-local">可扫描</span>
          <span v-else class="badge badge-neutral">等待内容</span>
        </div>
        <div class="local-result-body">
          <div v-if="!preview" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="qr" :size="21" /></span>
            <strong>等待内容</strong>
            <p>填写内容后，这里会实时生成二维码预览。</p>
            <p v-if="error" class="qr-error">{{ error }}</p>
          </div>
          <template v-else>
            <div class="qr-preview">
              <img :src="preview" alt="二维码预览" />
              <span v-if="generating" class="qr-loading">更新中…</span>
            </div>
            <div class="metric-line">
              <span>内容字节</span>
              <span>{{ bytes }} / 1200</span>
            </div>
            <div class="metric-line">
              <span>尺寸 / 容错</span>
              <span>{{ size }}px · {{ level }}</span>
            </div>
            <div class="download-actions" style="margin-top: 12px">
              <button class="button button-ink button-sm" type="button" @click="download">
                <AppIcon name="download" :size="13" />
                下载 PNG
              </button>
              <button class="button button-ghost button-sm" type="button" @click="copyImage">
                <AppIcon name="copy" :size="13" />
                复制图片
              </button>
            </div>
            <p v-if="notice" class="notice-line">{{ notice }}</p>
            <details class="content-details">
              <summary>查看编码内容</summary>
              <pre>{{ content }}</pre>
            </details>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 14px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
}

.type-tabs button {
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
}

.type-tabs button.is-active {
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 1px 4px rgba(25, 28, 23, 0.08);
}

.type-notice {
  margin-bottom: 11px;
  padding: 8px 10px;
  border-radius: 7px;
  background: var(--surface-2);
  color: var(--faint);
  font-size: 10.5px;
}

.type-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.option-gap {
  margin-top: 14px;
}

.run-hint {
  color: var(--faint);
  font-size: 10.5px;
  text-align: right;
}

.color-pair {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.qr-preview {
  position: relative;
  display: grid;
  place-items: center;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
}

.qr-preview img {
  width: min(100%, 240px);
  height: auto;
  image-rendering: auto;
}

.qr-loading {
  position: absolute;
  right: 10px;
  bottom: 8px;
  padding: 3px 7px;
  border-radius: 4px;
  background: rgba(25, 28, 23, 0.72);
  color: #fff;
  font-size: 9px;
}

.qr-error {
  color: var(--danger) !important;
}

.notice-line {
  margin-top: 9px;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.6;
}

.content-details {
  margin-top: 12px;
  border-top: 1px dashed var(--line);
  padding-top: 10px;
}

.content-details summary {
  cursor: pointer;
  color: var(--faint);
  font-size: 10.5px;
}

.content-details pre {
  margin: 8px 0 0;
  max-height: 150px;
  overflow: auto;
  padding: 9px;
  border-radius: 7px;
  background: var(--surface-2);
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
