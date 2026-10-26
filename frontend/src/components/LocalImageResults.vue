<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { LocalImageResult } from '@/utils/localImage'
import { saveLocalResult } from '@/utils/localImage'
import { formatBytes } from '@/utils/format'
import { downloadZip } from '@/utils/zip'

const props = defineProps<{
  results: LocalImageResult[]
  processing: boolean
  progress?: number
  errors: string[]
  idleText?: string
}>()

const emit = defineEmits<{ (event: 'clear'): void }>()

const urls = ref<string[]>([])
const zipping = ref(false)

function refreshUrls() {
  urls.value.forEach((url) => URL.revokeObjectURL(url))
  urls.value = props.results.map((result) => URL.createObjectURL(result.blob))
}

watch(
  () => props.results,
  () => refreshUrls(),
  { immediate: true, deep: false },
)

onBeforeUnmount(() => {
  urls.value.forEach((url) => URL.revokeObjectURL(url))
})

const totalSize = computed(() => props.results.reduce((sum, item) => sum + item.size, 0))
const hasResults = computed(() => props.results.length > 0)

function summary(result: LocalImageResult): string {
  const parts = [formatBytes(result.size)]
  if (result.width && result.height) parts.push(`${result.width}×${result.height}`)
  if (result.meta.ratio !== undefined) parts.push(`压缩 ${result.meta.ratio}%`)
  if (result.meta.note) parts.push(String(result.meta.note))
  return parts.join(' · ')
}

async function downloadAll() {
  if (zipping.value || !hasResults.value) return
  zipping.value = true
  try {
    await downloadZip(
      props.results.map((item) => ({ filename: item.filename, blob: item.blob })),
      `图片处理_${new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')}.zip`,
    )
  } finally {
    zipping.value = false
  }
}
</script>

<template>
  <div class="local-result">
    <div class="local-result-head">
      <span class="mono-label">RESULT / 本地处理</span>
      <span v-if="errors.length && hasResults" class="badge badge-warn">部分成功</span>
      <span v-else-if="hasResults" class="badge badge-success">完成</span>
      <span v-else-if="processing" class="badge badge-neutral">处理中</span>
      <span v-else class="badge badge-neutral">等待输入</span>
    </div>
    <div class="local-result-body">
      <div v-if="processing && !hasResults" class="local-processing">
        <AppIcon name="refresh" :size="18" class="spin" />
        <span>正在浏览器内处理…{{ progress ? ` ${progress}%` : '' }}</span>
      </div>

      <div v-else-if="!hasResults && !errors.length" class="local-empty">
        <span class="local-empty-mark"><AppIcon name="image" :size="21" /></span>
        <strong>等待输入</strong>
        <p>{{ idleText || '选择文件并开始处理后，结果会显示在这里。' }}</p>
        <p class="tool-tip">文件不上传，结果只存在当前页面内存。</p>
      </div>

      <template v-else>
        <ul v-if="errors.length" class="local-errors" role="alert">
          <li v-for="(message, index) in errors" :key="index">{{ message }}</li>
        </ul>

        <ul v-if="hasResults" class="local-result-list">
          <li v-for="(result, index) in results" :key="`${result.filename}-${index}`">
            <span class="thumb">
              <img v-if="urls[index]" :src="urls[index]" alt="" />
            </span>
            <span class="info">
              <span class="name">{{ result.filename }}</span>
              <span class="meta mono">{{ summary(result) }}</span>
            </span>
            <button class="download-button" type="button" aria-label="下载" @click="saveLocalResult(result)">
              <AppIcon name="download" :size="14" />
            </button>
          </li>
        </ul>

        <div v-if="hasResults" class="result-footer">
          <span class="mono">{{ results.length }} 个结果 · {{ formatBytes(totalSize) }}</span>
          <div class="download-actions">
            <button v-if="results.length > 1" class="button button-ink button-sm" type="button" :disabled="zipping" @click="downloadAll">
              <AppIcon name="download" :size="13" />
              {{ zipping ? '打包中…' : '打包下载 ZIP' }}
            </button>
            <button class="text-button" type="button" @click="emit('clear')">清除结果</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.local-processing {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 20px 4px;
  color: var(--muted);
  font-size: 12px;
}

.local-errors {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 11px;
  line-height: 1.55;
}

.local-result-list {
  display: flex;
  flex-direction: column;
}

.local-result-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(217, 211, 196, 0.55);
}

.local-result-list li:last-child {
  border-bottom: 0;
}

.thumb {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: none;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface-2);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink-2);
  font-size: 11.5px;
}

.meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--faint);
  font-size: 9px;
}

.download-button {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--muted);
}

.download-button:hover {
  border-color: var(--ink-2);
  color: var(--ink);
}

.result-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
}

.result-footer > .mono {
  color: var(--faint);
  font-size: 9px;
}
</style>
