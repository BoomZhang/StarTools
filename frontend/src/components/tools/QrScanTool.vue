<script setup lang="ts">
import jsQR from 'jsqr'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { imageFileToDataUrl } from '@/utils/files'
import { qrDomain, qrResultType } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const files = ref<File[]>([])
const previewUrl = ref('')
const content = ref('')
const resultType = ref('')
const decoded = ref(false)
const error = ref('')
const scanning = ref(false)
const cameraOpen = ref(false)
const cameraError = ref('')
const video = ref<HTMLVideoElement | null>(null)
const startedAt = ref(0)
let stream: MediaStream | null = null

const domain = computed(() => (resultType.value === '网址' ? qrDomain(content.value) : null))
const isUrl = computed(() => /^https?:\/\//i.test(content.value))

watch(files, async (value) => {
  resetResult()
  const file = value[0]
  if (!file) {
    previewUrl.value = ''
    return
  }
  try {
    previewUrl.value = await imageFileToDataUrl(file)
    await decodeImageFile(file)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '图片读取失败'
  }
})

onBeforeUnmount(() => {
  stopCamera()
})

function resetResult() {
  content.value = ''
  resultType.value = ''
  decoded.value = false
  error.value = ''
}

async function decodeImageFile(file: File) {
  scanning.value = true
  try {
    const image = await loadImage(file)
    const canvas = document.createElement('canvas')
    const scale = Math.min(1, 1600 / Math.max(image.width, image.height))
    canvas.width = Math.round(image.width * scale)
    canvas.height = Math.round(image.height * scale)
    const context = canvas.getContext('2d')
    if (!context) throw new Error('画布不可用')
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const data = context.getImageData(0, 0, canvas.width, canvas.height)
    const code = jsQR(data.data, data.width, data.height, { inversionAttempts: 'attemptBoth' })
    if (!code || !code.data) {
      error.value = '未识别到二维码。请裁剪到二维码区域、提高对比度，或避免反光与模糊后重试。'
      return
    }
    content.value = code.data
    resultType.value = qrResultType(code.data)
    decoded.value = true
    if (!startedAt.value) startedAt.value = performance.now()
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - startedAt.value),
      file_count: 1,
      total_size: file.size,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '二维码识别失败'
  } finally {
    scanning.value = false
  }
}

function loadImage(file: File): Promise<HTMLImageElement> {
  const url = URL.createObjectURL(file)
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片无法解码，请换一张 JPG、PNG、WebP 或 BMP 图片'))
    }
    image.src = url
  })
}

async function openCamera() {
  cameraError.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = '当前浏览器不支持调用摄像头，请上传图片识别。'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false,
    })
    cameraOpen.value = true
    await new Promise((resolve) => window.setTimeout(resolve, 60))
    if (video.value) {
      video.value.srcObject = stream
      await video.value.play()
    }
  } catch (err) {
    cameraError.value =
      err instanceof DOMException && err.name === 'NotAllowedError'
        ? '摄像头权限被拒绝。可以改用上传图片，图片不会上传到服务器。'
        : '摄像头无法启动，请改用上传图片。'
    stopCamera()
  }
}

function stopCamera() {
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  cameraOpen.value = false
}

function capture() {
  if (!video.value) return
  const canvas = document.createElement('canvas')
  canvas.width = video.value.videoWidth
  canvas.height = video.value.videoHeight
  const context = canvas.getContext('2d')
  if (!context) return
  context.drawImage(video.value, 0, 0, canvas.width, canvas.height)
  const data = context.getImageData(0, 0, canvas.width, canvas.height)
  const code = jsQR(data.data, data.width, data.height, { inversionAttempts: 'attemptBoth' })
  if (!code?.data) {
    cameraError.value = '这一帧没有识别到二维码，请对准二维码后再试。'
    return
  }
  content.value = code.data
  resultType.value = qrResultType(code.data)
  decoded.value = true
  error.value = ''
  previewUrl.value = canvas.toDataURL('image/png')
  resetFiles()
  stopCamera()
  void reportUsage({ tool_code: props.tool.code, result: 'succeeded', duration_ms: 0, file_count: 1, total_size: 0 })
}

function resetFiles() {
  files.value = []
}

async function copyContent() {
  if (decoded.value) await copy(content.value)
}

function openLink() {
  if (!isUrl.value) return
  const host = domain.value || content.value
  if (window.confirm(`将打开外部网站：${host}\n二维码内容可能指向钓鱼站点，确认继续？`)) {
    window.open(content.value, '_blank', 'noopener,noreferrer')
  }
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / IMAGE</span>
            <h2>二维码图片</h2>
          </div>
          <span class="section-aside">支持 JPG · PNG · WEBP · BMP</span>
        </div>
        <FilePicker
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          accept="image/jpeg,image/png,image/webp,image/bmp,.jpg,.jpeg,.png,.webp,.bmp"
          title="拖拽、粘贴或点击选择二维码图片"
          :hint="`图片只在浏览器内解码，不上传；单张上限 ${tool.max_file_mb}MB`"
          paste
        />
        <div class="camera-row">
          <button class="button button-ghost button-sm" type="button" @click="openCamera">
            <AppIcon name="scan" :size="14" />
            打开摄像头扫描
          </button>
          <span class="tool-tip">摄像头权限被拒时，可直接使用上面的图片上传。</span>
        </div>
        <p v-if="cameraError" class="mini-alert danger camera-error">{{ cameraError }}</p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / NOTES</span>
            <h2>识别说明</h2>
          </div>
        </div>
        <ul class="scan-notes">
          <li>识别到网址时不会自动打开，需要你确认目标域名。</li>
          <li>一张图检测到多个二维码时，只展示第一个。</li>
          <li>识别结果不写入本地存储，刷新即清除。</li>
        </ul>
        <button class="text-button" type="button" @click="resetResult">清除当前结果</button>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 识别结果</span>
          <span v-if="error" class="badge badge-danger">未识别</span>
          <span v-else-if="decoded" class="badge badge-local">{{ resultType }}</span>
          <span v-else class="badge badge-neutral">等待图片</span>
        </div>
        <div class="local-result-body">
          <div v-if="!decoded && !error" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="qr" :size="21" /></span>
            <strong>等待图片</strong>
            <p>上传、粘贴或拍摄二维码图片后，解码内容会显示在这里。</p>
          </div>
          <div v-else-if="scanning" class="scan-loading">
            <AppIcon name="refresh" :size="18" class="spin" />
            <span>正在本地解码…</span>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else>
            <div v-if="previewUrl" class="scan-preview">
              <img :src="previewUrl" alt="二维码原图" />
            </div>
            <div class="metric-line">
              <span>识别类型</span>
              <span>{{ resultType }}</span>
            </div>
            <div v-if="domain" class="metric-line">
              <span>目标域名</span>
              <span>{{ domain }}</span>
            </div>
            <textarea class="text-output scan-output" readonly :value="content" aria-label="二维码内容" spellcheck="false"></textarea>
            <div class="result-toolbar" style="margin-top: 12px">
              <button class="button button-ghost button-sm" type="button" @click="copyContent">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : '复制内容' }}
              </button>
              <button v-if="isUrl" class="button button-soft button-sm" type="button" @click="openLink">
                <AppIcon name="external" :size="13" />
                打开网站
              </button>
            </div>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>

  <div v-if="cameraOpen" class="camera-overlay" role="dialog" aria-label="摄像头扫描">
    <div class="camera-modal">
      <div class="camera-head">
        <span class="mono-label">CAMERA / 本地扫描</span>
        <button class="icon-button" type="button" aria-label="关闭摄像头" @click="stopCamera">
          <AppIcon name="x" :size="16" />
        </button>
      </div>
      <video ref="video" class="camera-video" playsinline muted></video>
      <p class="camera-note">将二维码放入画面中央，点击下方按钮捕获一帧。</p>
      <button class="button button-accent button-block" type="button" @click="capture">捕获并识别</button>
    </div>
  </div>
</template>

<style scoped>
.camera-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.camera-error {
  margin-top: 10px;
}

.scan-notes {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-bottom: 14px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.scan-notes li {
  position: relative;
  padding-left: 14px;
}

.scan-notes li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--line-strong);
}

.scan-loading {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 20px 6px;
  color: var(--muted);
  font-size: 12px;
}

.scan-preview {
  display: grid;
  place-items: center;
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-2);
}

.scan-preview img {
  max-height: 140px;
  max-width: 100%;
  border-radius: 4px;
}

.scan-output {
  min-height: 120px;
  margin-top: 10px;
}

.camera-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(12, 20, 16, 0.72);
  backdrop-filter: blur(6px);
}

.camera-modal {
  width: min(100%, 460px);
  padding: 18px;
  border-radius: var(--radius-md);
  background: var(--surface);
}

.camera-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.camera-head .mono-label {
  color: var(--faint);
  font-size: 8.5px;
}

.camera-video {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 9px;
  background: #101613;
  object-fit: cover;
}

.camera-note {
  margin: 10px 0 12px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.6;
}
</style>
