<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import FilePicker from '@/components/FilePicker.vue'
import ServerResultPanel from '@/components/ServerResultPanel.vue'
import TextTaskPanel from '@/components/TextTaskPanel.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import UploadConsentNotice from '@/components/UploadConsentNotice.vue'
import { useServerTask } from '@/composables/useServerTask'
import { useUploadConsent } from '@/composables/useUploadConsent'
import type { Tool } from '@/types'

const props = defineProps<{ tool: Tool }>()
const server = useServerTask(props.tool.code)
const { accepted } = useUploadConsent()

const files = ref<File[]>([])
const audioFormat = ref('mp3')
const bitrate = ref('192k')
const start = ref(0)
const end = ref(3)
const width = ref(480)
const fps = ref(12)
const level = ref<'light' | 'balanced' | 'max'>('balanced')
const extractFormat = ref('mp3')
const videoFormat = ref('mp4')
const language = ref('auto')
const output = ref<'text' | 'timestamped' | 'srt'>('text')
const text = ref('')
const voice = ref<'zh' | 'en'>('zh')
const speed = ref(1.0)
const ttsFormat = ref<'mp3' | 'wav'>('mp3')

const advanced = ref(false)
const videoCodec = ref<'h264' | 'h265'>('h264')
const rateMode = ref<'crf' | 'bitrate'>('crf')
const crf = ref(23)
const videoBitrate = ref(2)
const encoderPreset = ref('medium')
const compressWidth = ref(1920)
const compressFps = ref(0)
const audioMode = ref<'aac' | 'mp3' | 'copy' | 'none'>('aac')
const audioBitrate = ref('128k')
const audioChannels = ref('keep')
const audioSampleRate = ref('keep')
const trimStart = ref(0)
const trimEnd = ref<number | null>(null)
const faststart = ref(true)

const AUDIO_FORMATS = [
  { value: 'mp3', label: 'MP3' },
  { value: 'wav', label: 'WAV' },
  { value: 'm4a', label: 'M4A' },
  { value: 'aac', label: 'AAC' },
  { value: 'flac', label: 'FLAC' },
  { value: 'ogg', label: 'OGG' },
  { value: 'opus', label: 'OPUS' },
  { value: 'wma', label: 'WMA' },
  { value: 'aiff', label: 'AIFF' },
]

const VIDEO_FORMATS = [
  { value: 'mp4', label: 'MP4' },
  { value: 'webm', label: 'WebM' },
  { value: 'mov', label: 'MOV' },
  { value: 'mkv', label: 'MKV' },
  { value: 'avi', label: 'AVI' },
  { value: 'flv', label: 'FLV' },
  { value: 'm4v', label: 'M4V' },
  { value: 'wmv', label: 'WMV' },
  { value: 'ts', label: 'TS' },
]

const BITRATES = ['64k', '96k', '128k', '192k', '256k', '320k']
const ENCODER_PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']

const isTextOnly = computed(() => props.tool.code === 'AV-07')
const isSpeech = computed(() => props.tool.code === 'AV-06')
const isAudioConvert = computed(() => props.tool.code === 'AV-01')
const isGif = computed(() => props.tool.code === 'AV-02')
const isCompress = computed(() => props.tool.code === 'AV-03')
const isExtract = computed(() => props.tool.code === 'AV-04')
const isVideoConvert = computed(() => props.tool.code === 'AV-05')
const isServer = computed(() => props.tool.engine === 'server')
const isAudioInput = computed(() => isAudioConvert.value || isSpeech.value)

const accept = computed(() =>
  isAudioInput.value
    ? '.mp3,.wav,.m4a,.aac,.flac,.ogg,.opus,.wma,.aiff,audio/*'
    : '.mp4,.webm,.mov,.mkv,.avi,.flv,.m4v,.wmv,.ts,.gif,video/*',
)

const textLength = computed(() => text.value.length)
const canRun = computed(() => {
  if (!props.tool.available || !isServer.value || server.busy.value) return false
  if (isTextOnly.value) return Boolean(text.value.trim()) && textLength.value <= 5000
  return files.value.length === 1 && accepted.value
})

const hint = computed(() => {
  if (!props.tool.available) return props.tool.unavailable_reason || '该工具当前不可用'
  if (!isServer.value) return '当前为前端处理，但该工具暂无浏览器实现'
  if (isTextOnly.value) {
    if (!text.value.trim()) return '请输入要合成的文本'
    if (textLength.value > 5000) return `文本 ${textLength.value} 字符，上限 5000`
    return ''
  }
  if (files.value.length !== 1) return isAudioInput.value ? '请选择 1 个音频文件' : '请选择 1 个视频文件'
  if (!accepted.value) return '请先确认上传说明'
  return ''
})

const params = computed(() => {
  if (isAudioConvert.value) return { format: audioFormat.value, bitrate: bitrate.value }
  if (isGif.value) return { start: start.value, end: end.value, width: width.value, fps: fps.value }
  if (isCompress.value) {
    return {
      level: level.value,
      codec: videoCodec.value,
      rate_mode: rateMode.value,
      crf: crf.value,
      video_bitrate: videoBitrate.value,
      preset: encoderPreset.value,
      width: compressWidth.value,
      fps: compressFps.value,
      audio: audioMode.value,
      audio_bitrate: audioBitrate.value,
      audio_channels: audioChannels.value,
      audio_sample_rate: audioSampleRate.value,
      trim_start: trimStart.value,
      trim_end: trimEnd.value ?? '',
      faststart: faststart.value ? 'true' : 'false',
    }
  }
  if (isExtract.value) return { format: extractFormat.value, bitrate: bitrate.value }
  if (isVideoConvert.value) return { format: videoFormat.value }
  if (isSpeech.value) return { language: language.value, output: output.value }
  return { text: text.value, voice: voice.value, speed: speed.value, format: ttsFormat.value }
})

function applyLevel(next: 'light' | 'balanced' | 'max') {
  level.value = next
  const presets = {
    light: { crf: 28, width: 1280 },
    balanced: { crf: 23, width: 1920 },
    max: { crf: 18, width: 1920 },
  }
  crf.value = presets[next].crf
  compressWidth.value = presets[next].width
  rateMode.value = 'crf'
}

function toggleAdvanced() {
  advanced.value = !advanced.value
}

const actionLabel = computed(() => {
  if (isAudioConvert.value) return '开始转换'
  if (isGif.value) return '生成 GIF'
  if (isCompress.value) return '开始压缩'
  if (isExtract.value) return '提取音频'
  if (isVideoConvert.value) return '转换视频'
  if (isSpeech.value) return '开始识别'
  return '合成语音'
})

onMounted(() => {
  if (isServer.value) void server.restore()
})

async function run() {
  if (!canRun.value) return
  await server.run(isTextOnly.value ? [] : files.value, params.value, {
    isRetry: server.state.value === 'failed',
  })
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / INPUT</span>
            <h2>{{ isTextOnly ? '输入文本' : isAudioInput ? '选择音频' : '选择视频' }}</h2>
          </div>
          <span class="section-aside">{{ isTextOnly ? `${textLength} / 5000 字符` : '1 个文件' }}</span>
        </div>

        <template v-if="isTextOnly">
          <textarea
            v-model="text"
            class="textarea textarea-tall"
            placeholder="输入要合成的文本，最多 5000 字符；不接受 SSML 或 HTML。"
            spellcheck="false"
          ></textarea>
          <p v-if="textLength > 5000" class="field-error">超出 {{ textLength - 5000 }} 个字符，请缩短后再合成。</p>
          <div class="mini-alert option-gap">
            <AppIcon name="info" :size="14" />
            <span>文本会发送到服务器合成，完成后立即丢弃，不保存为原始数据。</span>
          </div>
        </template>
        <FilePicker
          v-else
          v-model="files"
          :max-file-mb="tool.max_file_mb"
          :accept="accept"
          :title="isAudioInput ? '拖拽音频到这里，或点击选择' : '拖拽视频到这里，或点击选择'"
          :hint="`单文件上限 ${tool.max_file_mb}MB`"
          :disabled="!tool.available"
        />
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / OPTIONS</span>
            <h2>处理参数</h2>
          </div>
        </div>

        <template v-if="isAudioConvert">
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>输出格式</strong></span>
              <select v-model="audioFormat" class="select">
                <option v-for="item in AUDIO_FORMATS" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>码率</strong><span>无损格式忽略</span></span>
              <select v-model="bitrate" class="select">
                <option v-for="item in BITRATES" :key="item" :value="item">{{ parseInt(item) }} kbps</option>
              </select>
            </div>
          </div>
        </template>

        <template v-else-if="isGif">
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>开始时间（秒）</strong></span>
              <input v-model.number="start" class="input input-mono" type="number" min="0" step="0.1" />
            </div>
            <div class="field">
              <span class="field-label"><strong>结束时间（秒）</strong></span>
              <input v-model.number="end" class="input input-mono" type="number" min="0" step="0.1" />
            </div>
            <div class="field">
              <span class="field-label"><strong>宽度</strong></span>
              <select v-model.number="width" class="select">
                <option :value="320">320 px</option>
                <option :value="480">480 px</option>
                <option :value="640">640 px</option>
                <option :value="800">800 px</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>帧率</strong></span>
              <select v-model.number="fps" class="select">
                <option :value="10">10 fps</option>
                <option :value="15">15 fps</option>
                <option :value="24">24 fps</option>
              </select>
            </div>
          </div>
          <p class="tool-tip option-gap">单段不超过 15 秒；起止时间必须落在视频时长内。</p>
        </template>

        <template v-else-if="isCompress">
          <div class="segmented">
            <button type="button" :class="{ 'is-active': level === 'light' }" @click="applyLevel('light')">轻</button>
            <button type="button" :class="{ 'is-active': level === 'balanced' }" @click="applyLevel('balanced')">推荐</button>
            <button type="button" :class="{ 'is-active': level === 'max' }" @click="applyLevel('max')">极致</button>
          </div>
          <p class="tool-tip option-gap">
            当前：{{ videoCodec === 'h264' ? 'H.264' : 'H.265' }} ·
            {{ rateMode === 'crf' ? `CRF ${crf}` : `${videoBitrate} Mbps` }} ·
            最大宽度 {{ compressWidth }} px{{ compressFps ? ` · ${compressFps} fps` : '' }}
          </p>

          <div class="advanced-toggle option-gap">
            <button class="text-button" type="button" @click="toggleAdvanced">
              {{ advanced ? '收起高级选项' : '展开高级选项' }}
            </button>
          </div>

          <div v-if="advanced" class="param-grid advanced-grid option-gap">
            <div class="field">
              <span class="field-label"><strong>视频编码</strong></span>
              <select v-model="videoCodec" class="select">
                <option value="h264">H.264（兼容性好）</option>
                <option value="h265">H.265 / HEVC（体积更小）</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>码率控制</strong></span>
              <select v-model="rateMode" class="select">
                <option value="crf">CRF 恒定质量</option>
                <option value="bitrate">平均码率</option>
              </select>
            </div>
            <div v-if="rateMode === 'crf'" class="field">
              <span class="field-label"><strong>CRF</strong><span>0–51，越小越清晰</span></span>
              <input v-model.number="crf" class="input input-mono" type="number" min="0" max="51" />
            </div>
            <div v-else class="field">
              <span class="field-label"><strong>视频码率</strong><span>Mbps</span></span>
              <input v-model.number="videoBitrate" class="input input-mono" type="number" min="0.1" max="100" step="0.1" />
            </div>
            <div class="field">
              <span class="field-label"><strong>编码速度</strong></span>
              <select v-model="encoderPreset" class="select">
                <option v-for="item in ENCODER_PRESETS" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>最大宽度</strong><span>px</span></span>
              <input v-model.number="compressWidth" class="input input-mono" type="number" min="128" max="7680" />
            </div>
            <div class="field">
              <span class="field-label"><strong>帧率</strong><span>0 = 保持原帧率</span></span>
              <input v-model.number="compressFps" class="input input-mono" type="number" min="0" max="120" />
            </div>
            <div class="field">
              <span class="field-label"><strong>音频编码</strong></span>
              <select v-model="audioMode" class="select">
                <option value="aac">AAC</option>
                <option value="mp3">MP3</option>
                <option value="copy">直接复制原音轨</option>
                <option value="none">移除音频</option>
              </select>
            </div>
            <div v-if="audioMode === 'aac' || audioMode === 'mp3'" class="field">
              <span class="field-label"><strong>音频码率</strong></span>
              <select v-model="audioBitrate" class="select">
                <option v-for="item in BITRATES" :key="item" :value="item">{{ parseInt(item) }} kbps</option>
              </select>
            </div>
            <div v-if="audioMode === 'aac' || audioMode === 'mp3'" class="field">
              <span class="field-label"><strong>声道</strong></span>
              <select v-model="audioChannels" class="select">
                <option value="keep">保持原样</option>
                <option value="1">单声道</option>
                <option value="2">双声道</option>
              </select>
            </div>
            <div v-if="audioMode === 'aac' || audioMode === 'mp3'" class="field">
              <span class="field-label"><strong>采样率</strong></span>
              <select v-model="audioSampleRate" class="select">
                <option value="keep">保持原样</option>
                <option value="22050">22050 Hz</option>
                <option value="44100">44100 Hz</option>
                <option value="48000">48000 Hz</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>裁剪开始</strong><span>秒</span></span>
              <input v-model.number="trimStart" class="input input-mono" type="number" min="0" step="0.1" />
            </div>
            <div class="field">
              <span class="field-label"><strong>裁剪结束</strong><span>秒，留空到结尾</span></span>
              <input v-model.number="trimEnd" class="input input-mono" type="number" min="0" step="0.1" placeholder="留空" />
            </div>
            <div class="field span-full">
              <label class="checkbox"><input v-model="faststart" type="checkbox" /> MP4 启用 faststart（网页更快开始播放）</label>
            </div>
          </div>
          <p class="tool-tip option-gap">压缩后分辨率不会高于原视频；H.265 体积更小，但旧设备可能无法播放。</p>
        </template>

        <template v-else-if="isExtract">
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>输出格式</strong></span>
              <select v-model="extractFormat" class="select">
                <option v-for="item in AUDIO_FORMATS" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>码率</strong><span>无损格式忽略</span></span>
              <select v-model="bitrate" class="select">
                <option v-for="item in BITRATES" :key="item" :value="item">{{ parseInt(item) }} kbps</option>
              </select>
            </div>
          </div>
          <p class="tool-tip option-gap">视频必须包含音轨；仅提取原音轨并重新编码，不改变画面。</p>
        </template>

        <template v-else-if="isVideoConvert">
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>输出格式</strong></span>
              <select v-model="videoFormat" class="select">
                <option v-for="item in VIDEO_FORMATS" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
          </div>
          <p class="tool-tip option-gap">WebM 使用 VP9 + Opus，转码耗时较长；AVI / WMV 兼容性因设备而异。</p>
        </template>

        <template v-else-if="isSpeech">
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>语言</strong></span>
              <select v-model="language" class="select">
                <option value="auto">自动识别</option>
                <option value="zh-CN">中文</option>
                <option value="en">英文</option>
                <option value="mixed">中英混排</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>输出</strong></span>
              <select v-model="output" class="select">
                <option value="text">纯文本</option>
                <option value="timestamped">带时间戳文本</option>
                <option value="srt">SRT 字幕</option>
              </select>
            </div>
          </div>
          <p class="tool-tip option-gap">音频时长不超过 60 分钟；识别结果需人工校对。</p>
        </template>

        <template v-else>
          <div class="param-grid">
            <div class="field">
              <span class="field-label"><strong>音色</strong></span>
              <select v-model="voice" class="select">
                <option value="zh">中文（内置）</option>
                <option value="en">英文（内置）</option>
              </select>
            </div>
            <div class="field">
              <span class="field-label"><strong>语速</strong><span>{{ speed.toFixed(1) }}×</span></span>
              <div class="range-row">
                <input v-model.number="speed" type="range" min="0.5" max="2" step="0.1" />
                <span class="range-value">{{ speed.toFixed(1) }}</span>
              </div>
            </div>
            <div class="field">
              <span class="field-label"><strong>输出格式</strong></span>
              <select v-model="ttsFormat" class="select">
                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
              </select>
            </div>
          </div>
          <p class="tool-tip option-gap">只使用引擎内置通用音色，不提供声音克隆或名人音色。</p>
        </template>

        <div v-if="!isTextOnly" class="option-gap">
          <UploadConsentNotice :file-count="files.length" />
        </div>
        <div class="run-bar">
          <p class="run-note">
            {{ isTextOnly ? '输入文本不落盘；合成音频作为结果返回。' : '服务端任务完成后结果可下载，上传文件仅维护者可访问。' }}
          </p>
          <div class="run-actions">
            <span v-if="hint" class="run-hint">{{ hint }}</span>
            <button class="button button-ink" type="button" :disabled="!canRun" @click="run">
              <AppIcon :name="isSpeech ? 'scan' : 'sparkles'" :size="15" />
              {{ server.busy.value ? '处理中…' : actionLabel }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <TextTaskPanel
        v-if="isSpeech"
        :tool="tool"
        :task="server.task.value"
        :state="server.state.value"
        :error="server.error.value"
        :restoring="server.restoring.value"
        @retry="run"
        @delete="server.removeResults"
      />
      <ServerResultPanel
        v-else
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
  margin-top: 7px;
  color: var(--danger);
  font-size: 10.5px;
}

.advanced-toggle {
  display: flex;
  justify-content: flex-start;
}

.advanced-grid {
  padding: 14px;
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
  background: var(--surface-2);
}
</style>
