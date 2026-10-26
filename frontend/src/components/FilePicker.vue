<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import { formatBytes } from '@/utils/format'
import { validateFiles } from '@/utils/files'

const props = withDefaults(
  defineProps<{
    modelValue: File[]
    accept?: string
    multiple?: boolean
    maxCount?: number
    maxFileMB?: number | null
    title?: string
    hint?: string
    disabled?: boolean
    paste?: boolean
    showList?: boolean
  }>(),
  {
    accept: '',
    multiple: false,
    maxCount: 1,
    maxFileMB: null,
    title: '拖拽文件到这里，或点击选择',
    hint: '',
    disabled: false,
    paste: false,
    showList: true,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: File[]): void
  (event: 'errors', value: string[]): void
}>()

const input = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const errors = ref<string[]>([])

const canAddMore = computed(() => props.multiple && props.modelValue.length < props.maxCount)

function reportErrors(messages: string[]) {
  errors.value = messages
  if (messages.length) emit('errors', messages)
}

function addFiles(list: FileList | File[]) {
  if (props.disabled) return
  const incoming = Array.from(list)
  if (!incoming.length) return
  const { accepted, errors: messages } = validateFiles(incoming, props.modelValue, {
    accept: props.accept,
    maxFileMB: props.maxFileMB,
    maxCount: props.multiple ? props.maxCount : 1,
  })
  reportErrors(messages)
  if (!accepted.length) return
  const next = props.multiple ? [...props.modelValue, ...accepted] : [accepted[0]]
  emit('update:modelValue', next)
  if (input.value) input.value.value = ''
}

function onInput(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) addFiles(target.files)
}

function onDrop(event: DragEvent) {
  dragging.value = false
  if (props.disabled) return
  if (event.dataTransfer?.files) addFiles(event.dataTransfer.files)
}

function remove(index: number) {
  const next = props.modelValue.slice()
  next.splice(index, 1)
  emit('update:modelValue', next)
  errors.value = []
}

function move(index: number, direction: -1 | 1) {
  const next = props.modelValue.slice()
  const target = index + direction
  if (target < 0 || target >= next.length) return
  ;[next[index], next[target]] = [next[target], next[index]]
  emit('update:modelValue', next)
}

function openPicker() {
  if (!props.disabled) input.value?.click()
}

function onPaste(event: ClipboardEvent) {
  if (!props.paste || props.disabled) return
  const files = Array.from(event.clipboardData?.files ?? [])
  if (files.length) {
    event.preventDefault()
    addFiles(files)
  }
}

onMounted(() => {
  if (props.paste) window.addEventListener('paste', onPaste)
})

onBeforeUnmount(() => {
  if (props.paste) window.removeEventListener('paste', onPaste)
})
</script>

<template>
  <div class="file-picker">
    <button
      type="button"
      class="dropzone"
      :class="{ 'is-dragging': dragging, 'is-disabled': disabled }"
      :disabled="disabled || (!multiple && modelValue.length > 0)"
      @click="openPicker"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <span class="drop-icon">
        <AppIcon name="upload" :size="21" />
      </span>
      <span class="drop-copy">
        <strong>{{ title }}</strong>
        <span v-if="hint" class="drop-hint">{{ hint }}</span>
        <span v-else-if="maxFileMB" class="drop-hint">
          单文件最大 {{ maxFileMB }} MB<span v-if="multiple"> · 最多 {{ maxCount }} 个</span>
        </span>
      </span>
      <input
        ref="input"
        class="sr-only"
        type="file"
        :accept="accept || undefined"
        :multiple="multiple"
        @change="onInput"
      />
    </button>

    <ul v-if="showList && modelValue.length" class="file-list">
      <li v-for="(file, index) in modelValue" :key="`${file.name}-${file.size}-${index}`" class="file-row">
        <span class="file-index mono-label">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size mono">{{ formatBytes(file.size) }}</span>
        </span>
        <span class="file-actions">
          <button
            v-if="multiple && modelValue.length > 1"
            type="button"
            class="mini-button"
            :disabled="index === 0"
            aria-label="上移"
            @click="move(index, -1)"
          >
            <AppIcon name="chevron-left" :size="13" class="rotate-up" />
          </button>
          <button
            v-if="multiple && modelValue.length > 1"
            type="button"
            class="mini-button"
            :disabled="index === modelValue.length - 1"
            aria-label="下移"
            @click="move(index, 1)"
          >
            <AppIcon name="chevron-right" :size="13" class="rotate-down" />
          </button>
          <button type="button" class="mini-button" aria-label="移除文件" @click="remove(index)">
            <AppIcon name="x" :size="13" />
          </button>
        </span>
      </li>
    </ul>

    <div v-if="showList && canAddMore && modelValue.length" class="add-more">
      <button type="button" class="text-button" @click="openPicker">
        <AppIcon name="plus" :size="13" />
        继续添加（还可添加 {{ maxCount - modelValue.length }} 个）
      </button>
    </div>

    <ul v-if="errors.length" class="file-errors" role="alert">
      <li v-for="(message, index) in errors" :key="index">{{ message }}</li>
    </ul>
  </div>
</template>

<style scoped>
.file-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dropzone {
  display: flex;
  align-items: center;
  gap: 15px;
  width: 100%;
  min-height: 116px;
  padding: 20px;
  border: 1.5px dashed var(--line-strong);
  border-radius: 12px;
  background: var(--surface-2);
  text-align: left;
  transition: border-color 0.2s, background-color 0.2s;
}

.dropzone:not(:disabled):hover,
.dropzone.is-dragging {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.dropzone.is-disabled,
.dropzone:disabled {
  cursor: default;
  opacity: 0.6;
}

.drop-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  color: var(--accent-deep);
}

.drop-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.drop-copy strong {
  font-size: 13.5px;
  font-weight: 600;
}

.drop-hint {
  color: var(--faint);
  font-size: 11.5px;
}

.file-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: var(--surface);
}

.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 46px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(217, 211, 196, 0.55);
}

.file-row:last-child {
  border-bottom: 0;
}

.file-index {
  color: var(--faint);
  font-size: 9px;
  flex: none;
}

.file-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
}

.file-size {
  flex: none;
  color: var(--faint);
  font-size: 10px;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: none;
}

.mini-button {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--faint);
}

.mini-button:hover:not(:disabled) {
  border-color: var(--line);
  background: var(--surface-2);
  color: var(--ink);
}

.mini-button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.rotate-up {
  transform: rotate(90deg);
}

.rotate-down {
  transform: rotate(-90deg);
}

.add-more {
  padding-left: 2px;
}

.file-errors {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 9px 12px;
  border-radius: 8px;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 11.5px;
  line-height: 1.6;
}

@media (max-width: 560px) {
  .dropzone {
    padding: 16px;
  }

  .file-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
}
</style>
