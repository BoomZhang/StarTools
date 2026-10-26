<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{ page: number; pages: number; total: number }>()
const emit = defineEmits<{ (event: 'change', page: number): void }>()

function go(page: number) {
  if (page < 1 || page > props.pages || page === props.page) return
  emit('change', page)
}
</script>

<template>
  <div class="pagination">
    <span>共 {{ total }} 条 · 第 {{ page }} / {{ pages }} 页</span>
    <div class="pagination-actions">
      <button class="button button-ghost button-sm" type="button" :disabled="page <= 1" @click="go(page - 1)">
        <AppIcon name="chevron-left" :size="13" />
        上一页
      </button>
      <button class="button button-ghost button-sm" type="button" :disabled="page >= pages" @click="go(page + 1)">
        下一页
        <AppIcon name="chevron-right" :size="13" />
      </button>
    </div>
  </div>
</template>
