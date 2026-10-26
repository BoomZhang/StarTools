<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import type { CropRect } from '@/types'

const props = withDefaults(
  defineProps<{
    file: File | null
    ratio: number | null
    modelValue: CropRect
    disabled?: boolean
  }>(),
  { disabled: false },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: CropRect): void
}>()

type Handle = 'move' | 'nw' | 'ne' | 'sw' | 'se'

const container = ref<HTMLDivElement | null>(null)
const image = ref<HTMLImageElement | null>(null)
const url = ref('')
const natural = ref({ width: 0, height: 0 })
const loadError = ref('')
const dragging = ref<Handle | null>(null)

let drag:
  | { handle: Handle; startX: number; startY: number; base: CropRect; boxW: number; boxH: number }
  | null = null

const imageRatio = computed(() => (natural.value.height ? natural.value.width / natural.value.height : 1))
const normRatio = computed(() => {
  if (!props.ratio) return null
  return imageRatio.value / props.ratio
})

const cropSize = computed(() => {
  if (!natural.value.width) return ''
  const width = Math.max(1, Math.round(props.modelValue.width * natural.value.width))
  const height = Math.max(1, Math.round(props.modelValue.height * natural.value.height))
  return `${width} × ${height} px`
})

const boxStyle = computed(() => ({
  left: `${props.modelValue.x * 100}%`,
  top: `${props.modelValue.y * 100}%`,
  width: `${props.modelValue.width * 100}%`,
  height: `${props.modelValue.height * 100}%`,
}))

function revoke() {
  if (url.value) {
    URL.revokeObjectURL(url.value)
    url.value = ''
  }
}

watch(
  () => props.file,
  (file) => {
    revoke()
    natural.value = { width: 0, height: 0 }
    loadError.value = ''
    if (file) url.value = URL.createObjectURL(file)
  },
  { immediate: true },
)

watch(
  () => props.ratio,
  () => {
    if (props.ratio && natural.value.width) {
      emit('update:modelValue', centeredRect(props.ratio))
    }
  },
)

onBeforeUnmount(() => {
  revoke()
  stopDrag()
})

function onLoad() {
  const element = image.value
  if (!element) return
  natural.value = { width: element.naturalWidth, height: element.naturalHeight }
  emit('update:modelValue', centeredRect(props.ratio ?? imageRatio.value))
}

function onError() {
  loadError.value = '当前浏览器无法预览此图片，可改用服务端处理或先转换为 JPG'
}

function centeredRect(ratio: number): CropRect {
  const normRatio = imageRatio.value / ratio
  let width = 1
  let height = width * normRatio
  if (height > 1) {
    height = 1
    width = height / normRatio
  }
  return { x: (1 - width) / 2, y: (1 - height) / 2, width, height }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function onPointerDown(event: PointerEvent, handle: Handle) {
  if (props.disabled || loadError.value) return
  event.preventDefault()
  event.stopPropagation()
  const rect = container.value?.getBoundingClientRect()
  if (!rect) return
  dragging.value = handle
  drag = {
    handle,
    startX: event.clientX,
    startY: event.clientY,
    base: { ...props.modelValue },
    boxW: rect.width,
    boxH: rect.height,
  }
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', stopDrag)
}

function stopDrag() {
  dragging.value = null
  drag = null
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', stopDrag)
}

function onPointerMove(event: PointerEvent) {
  if (!drag) return
  const dx = (event.clientX - drag.startX) / drag.boxW
  const dy = (event.clientY - drag.startY) / drag.boxH
  const base = drag.base
  let next: CropRect

  if (drag.handle === 'move') {
    next = {
      ...base,
      x: clamp(base.x + dx, 0, 1 - base.width),
      y: clamp(base.y + dy, 0, 1 - base.height),
    }
  } else {
    next = resizeRect(base, drag.handle, dx, dy)
  }
  emit('update:modelValue', next)
}

function resizeRect(base: CropRect, handle: Handle, dx: number, dy: number): CropRect {
  const left = base.x
  const top = base.y
  const right = base.x + base.width
  const bottom = base.y + base.height
  const minSize = 0.05
  const ratio = normRatio.value

  let newLeft = left
  let newTop = top
  let newRight = right
  let newBottom = bottom

  if (handle === 'nw' || handle === 'sw') newLeft = clamp(left + dx, 0, right - minSize)
  if (handle === 'ne' || handle === 'se') newRight = clamp(right + dx, left + minSize, 1)
  if (handle === 'nw' || handle === 'ne') newTop = clamp(top + dy, 0, bottom - minSize)
  if (handle === 'sw' || handle === 'se') newBottom = clamp(bottom + dy, top + minSize, 1)

  if (ratio) {
    const anchorLeft = handle === 'nw' || handle === 'sw'
    const anchorTop = handle === 'sw' || handle === 'se'
    const maxWidth = anchorLeft ? 1 - left : right
    const maxHeight = anchorTop ? 1 - top : bottom
    const width = Math.max(minSize, Math.min(newRight - newLeft, maxWidth, maxHeight / ratio))
    const height = width * ratio
    newLeft = anchorLeft ? left : right - width
    newRight = anchorLeft ? left + width : right
    newTop = anchorTop ? top : bottom - height
    newBottom = anchorTop ? top + height : bottom
  }

  return {
    x: newLeft,
    y: newTop,
    width: Math.max(minSize, newRight - newLeft),
    height: Math.max(minSize, newBottom - newTop),
  }
}

function reset() {
  emit('update:modelValue', centeredRect(props.ratio ?? imageRatio.value))
}
</script>

<template>
  <div class="crop-editor">
    <div class="crop-toolbar">
      <span class="mono-label">拖动裁剪框 · 四角缩放</span>
      <span class="crop-size mono">{{ cropSize }}</span>
      <button class="text-button" type="button" :disabled="disabled" @click="reset">重置</button>
    </div>
    <div class="crop-canvas" :class="{ 'is-disabled': disabled }">
      <div ref="container" class="crop-stage">
        <img ref="image" :src="url" alt="裁剪预览" @load="onLoad" @error="onError" />
        <div
          v-if="!loadError && natural.width"
          class="crop-box"
          :class="{ 'is-dragging': dragging }"
          :style="boxStyle"
          @pointerdown="onPointerDown($event, 'move')"
        >
          <span class="crop-grid" aria-hidden="true"></span>
          <button class="crop-handle nw" type="button" aria-label="缩放左上角" @pointerdown="onPointerDown($event, 'nw')"></button>
          <button class="crop-handle ne" type="button" aria-label="缩放右上角" @pointerdown="onPointerDown($event, 'ne')"></button>
          <button class="crop-handle sw" type="button" aria-label="缩放左下角" @pointerdown="onPointerDown($event, 'sw')"></button>
          <button class="crop-handle se" type="button" aria-label="缩放右下角" @pointerdown="onPointerDown($event, 'se')"></button>
        </div>
      </div>
      <div v-if="loadError" class="crop-error">
        <AppIcon name="alert" :size="16" />
        <span>{{ loadError }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.crop-editor {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.crop-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--faint);
  font-size: 10px;
}

.crop-toolbar .mono-label {
  font-size: 8.5px;
}

.crop-size {
  margin-left: auto;
  color: var(--muted);
  font-size: 9.5px;
}

.crop-canvas {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 460px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background:
    linear-gradient(45deg, rgba(217, 211, 196, 0.35) 25%, transparent 25%, transparent 75%, rgba(217, 211, 196, 0.35) 75%),
    linear-gradient(45deg, rgba(217, 211, 196, 0.35) 25%, var(--surface-2) 25%, var(--surface-2) 75%, rgba(217, 211, 196, 0.35) 75%);
  background-size: 18px 18px;
  background-position: 0 0, 9px 9px;
  overflow: hidden;
  touch-action: none;
  user-select: none;
}

.crop-canvas.is-disabled {
  opacity: 0.6;
}

.crop-stage {
  position: relative;
  display: inline-block;
  max-width: 100%;
  line-height: 0;
}

.crop-canvas img {
  display: block;
  max-width: 100%;
  max-height: 460px;
  object-fit: contain;
  pointer-events: none;
}

.crop-box {
  position: absolute;
  border: 1.5px solid #fff;
  box-shadow: 0 0 0 9999px rgba(20, 24, 18, 0.48);
  cursor: move;
  touch-action: none;
}

.crop-box.is-dragging {
  border-color: var(--accent);
}

.crop-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.45) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.45) 1px, transparent 1px);
  background-size: 33.333% 33.333%;
  pointer-events: none;
}

.crop-handle {
  position: absolute;
  width: 14px;
  height: 14px;
  padding: 0;
  border: 1.5px solid #fff;
  border-radius: 3px;
  background: var(--accent);
  cursor: nwse-resize;
  touch-action: none;
}

.crop-handle.nw {
  top: -7px;
  left: -7px;
  cursor: nwse-resize;
}

.crop-handle.ne {
  top: -7px;
  right: -7px;
  cursor: nesw-resize;
}

.crop-handle.sw {
  bottom: -7px;
  left: -7px;
  cursor: nesw-resize;
}

.crop-handle.se {
  bottom: -7px;
  right: -7px;
  cursor: nwse-resize;
}

.crop-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 22px;
  color: var(--muted);
  font-size: 11.5px;
  text-align: center;
}
</style>
