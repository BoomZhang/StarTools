<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolBadge from '@/components/ToolBadge.vue'
import { useSite } from '@/composables/useSite'
import type { Tool } from '@/types'

defineProps<{ tool: Tool }>()
const { payload } = useSite()
</script>

<template>
  <RouterLink :to="`/t/${tool.slug}`" class="tool-card">
    <div class="tool-card-top">
      <span class="tool-code mono-label">{{ tool.code }}</span>
      <ToolBadge v-if="payload?.site.show_engine_badge !== false" :engine="tool.engine" />
    </div>
    <div class="tool-card-body">
      <h4>{{ tool.name }}</h4>
      <p>{{ tool.summary }}</p>
    </div>
    <div class="tool-card-foot">
      <span class="tool-formats mono-label">{{ tool.formats }}</span>
      <span class="tool-arrow" aria-hidden="true">
        <AppIcon name="arrow-up-right" :size="15" />
      </span>
    </div>
  </RouterLink>
</template>

<style scoped>
.tool-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 178px;
  padding: 18px 18px 15px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
  transition: transform 0.24s var(--ease-out), border-color 0.24s, box-shadow 0.24s;
  overflow: hidden;
}

.tool-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 18px;
  right: 18px;
  height: 1px;
  background: var(--accent);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s var(--ease-out);
}

.tool-card:hover {
  transform: translateY(-3px);
  border-color: var(--line-strong);
  box-shadow: var(--shadow-md);
}

.tool-card:hover::before {
  transform: scaleX(1);
}

.tool-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.tool-code {
  color: var(--faint);
  font-size: 9px;
}

.tool-card-body {
  flex: 1;
  padding: 18px 0 20px;
}

.tool-card-body h4 {
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.35;
}

.tool-card-body p {
  margin-top: 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tool-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid rgba(217, 211, 196, 0.7);
}

.tool-formats {
  color: var(--faint);
  font-size: 8.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-arrow {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 50%;
  color: var(--muted);
  transition: background-color 0.24s, color 0.24s, border-color 0.24s;
}

.tool-card:hover .tool-arrow {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper);
}
</style>
