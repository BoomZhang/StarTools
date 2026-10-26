<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import type { Tool } from '@/types'

defineProps<{ tool: Tool }>()
</script>

<template>
  <div class="placeholder panel">
    <AppIcon name="info" :size="20" />
    <div>
      <h2>该工具的页面实现尚未接入</h2>
      <p>{{ tool.name }}（{{ tool.code }}）当前不在可提交状态，请返回工具目录或联系维护者。</p>
    </div>
  </div>
</template>

<style scoped>
.placeholder {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-top: 18px;
  padding: 24px;
}

.placeholder h2 {
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 600;
}

.placeholder p {
  margin-top: 7px;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.7;
}
</style>
