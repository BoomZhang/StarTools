<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch, type CSSProperties } from 'vue'

import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{
  files: File[]
  direction: 'horizontal' | 'vertical' | 'grid'
  columns: number
  gap: number
  background: string
}>()

const emit = defineEmits<{
  (event: 'update:files', value: File[]): void
}>()

const urls = ref<string[]>([])
const dragIndex = ref<number | null>(null)
const overIndex = ref<number | null>(null)

function revoke() {
  urls.value.forEach((url) => URL.revokeObjectURL(url))
  urls.value = []
}

watch(
  () => props.files,
  (files) => {
    revoke()
    urls.value = files.map((file) => URL.createObjectURL(file))
  },
  { immediate: true },
)

onBeforeUnmount(revoke)

const layoutStyle = computed<CSSProperties>(() => {
  if (props.direction === 'grid') {
    return {
      display: 'grid',
      gridTemplateColumns: `repeat(${props.columns}, minmax(0, 1fr))`,
      gap: `${props.gap}px`,
      background: props.background,
    }
  }
  return {
    display: 'flex',
    flexDirection: props.direction === 'horizontal' ? 'row' : 'column',
    alignItems: 'center',
    gap: `${props.gap}px`,
    background: props.background,
  }
})

function reorder(from: number, to: number) {
  if (from === to || from < 0 || to < 0) return
  const next = props.files.slice()
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  emit('update:files', next)
}

function onDragStart(event: DragEvent, index: number) {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragOver(event: DragEvent, index: number) {
  event.preventDefault()
  overIndex.value = index
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}

function onDrop(event: DragEvent, index: number) {
  event.preventDefault()
  const from = dragIndex.value ?? Number(event.dataTransfer?.getData('text/plain'))
  reorder(Number.isFinite(from) ? from : -1, index)
  dragIndex.value = null
  overIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  overIndex.value = null
}

function move(index: number, offset: -1 | 1) {
  reorder(index, index + offset)
}

function remove(index: number) {
  emit('update:files', props.files.filter((_, item) => item !== index))
}
</script>

<template>
  <div class="stitch-board">
    <div class="board-head">
      <span class="mono-label">拖动缩略图调整顺序</span>
      <span class="board-count mono">{{ files.length }} 张</span>
    </div>
    <div class="board-preview" :style="layoutStyle">
      <div
        v-for="(file, index) in files"
        :key="`${file.name}-${file.size}-${index}`"
        class="board-tile"
        :class="{
          'is-dragging': dragIndex === index,
          'is-over': overIndex === index && dragIndex !== index,
        }"
        draggable="true"
        @dragstart="onDragStart($event, index)"
        @dragover="onDragOver($event, index)"
        @drop="onDrop($event, index)"
        @dragend="onDragEnd"
      >
        <img :src="urls[index]" :alt="file.name" draggable="false" />
        <span class="tile-index mono">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="tile-actions">
          <button type="button" class="tile-button" :disabled="index === 0" aria-label="上移" @click="move(index, -1)">
            <AppIcon name="chevron-left" :size="12" class="rotate-left" />
          </button>
          <button
            type="button"
            class="tile-button"
            :disabled="index === files.length - 1"
            aria-label="下移"
            @click="move(index, 1)"
          >
            <AppIcon name="chevron-right" :size="12" class="rotate-right" />
          </button>
          <button type="button" class="tile-button is-remove" aria-label="移除" @click="remove(index)">
            <AppIcon name="x" :size="12" />
          </button>
        </span>
      </div>
    </div>
    <p class="board-hint">
      {{ direction === 'grid' ? `网格 ${columns} 列，按顺序填充` : direction === 'horizontal' ? '横向拼接，按列表顺序从左到右' : '纵向拼接，按列表顺序从上到下' }}；也可用箭头微调。
    </p>
  </div>
</template>

<style scoped>
.stitch-board {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--faint);
}

.board-head .mono-label {
  font-size: 8.5px;
}

.board-count {
  font-size: 9px;
}

.board-preview {
  padding: 10px;
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
  min-height: 96px;
  overflow-x: auto;
}

.board-tile {
  position: relative;
  flex: none;
  width: 104px;
  height: 96px;
  border: 1.5px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.75);
  overflow: hidden;
  cursor: grab;
  transition: border-color 0.15s, opacity 0.15s, transform 0.15s;
}

.board-tile:active {
  cursor: grabbing;
}

.board-tile.is-dragging {
  opacity: 0.45;
}

.board-tile.is-over {
  border-color: var(--accent);
  transform: scale(1.02);
}

.board-tile img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
}

.tile-index {
  position: absolute;
  top: 4px;
  left: 4px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(20, 24, 18, 0.7);
  color: #fff;
  font-size: 8px;
}

.tile-actions {
  position: absolute;
  right: 3px;
  bottom: 3px;
  display: flex;
  gap: 2px;
}

.tile-button {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: rgba(252, 251, 247, 0.92);
  color: var(--muted);
}

.tile-button:hover:not(:disabled) {
  color: var(--ink);
  border-color: var(--line-strong);
}

.tile-button:disabled {
  opacity: 0.3;
}

.tile-button.is-remove {
  color: var(--danger);
}

.rotate-left {
  transform: rotate(90deg);
}

.rotate-right {
  transform: rotate(-90deg);
}

.board-hint {
  color: var(--faint);
  font-size: 10px;
  line-height: 1.6;
}

@media (max-width: 560px) {
  .board-tile {
    width: 88px;
    height: 82px;
  }
}
</style>
