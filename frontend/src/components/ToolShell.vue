<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolBadge from '@/components/ToolBadge.vue'
import ToolRules from '@/components/ToolRules.vue'
import { useSite } from '@/composables/useSite'
import type { Tool } from '@/types'

const props = defineProps<{ tool: Tool; rules: string[] }>()
const { payload } = useSite()

const limitText = computed(() => {
  if (!props.tool.accepts_files) return '无需上传文件'
  const size = props.tool.max_file_mb ? `单文件 ≤ ${props.tool.max_file_mb} MB` : '单文件限额未设置'
  const count = props.tool.max_count > 1 ? ` · 单次 ≤ ${props.tool.max_count} 个` : ' · 单次 1 个'
  return size + count
})

const batchText = computed(() => {
  if (!props.tool.accepts_files || !props.tool.max_file_mb) return null
  if (props.tool.max_count <= 1) return null
  return `批量总量 ${props.tool.max_file_mb * props.tool.max_count} MB`
})

const engineNote = computed(() =>
  props.tool.engine === 'server'
    ? '文件会上传到站点服务器处理，仅维护者可访问。'
    : '文件与文本只在当前浏览器内处理，不会上传到服务器。',
)
</script>

<template>
  <div class="tool-page container">
    <nav class="breadcrumbs" aria-label="面包屑">
      <RouterLink to="/">工具目录</RouterLink>
      <AppIcon name="chevron-right" :size="12" />
      <RouterLink to="/#catalog">{{ tool.category_name }}</RouterLink>
      <AppIcon name="chevron-right" :size="12" />
      <span>{{ tool.name }}</span>
    </nav>

    <header class="tool-head">
      <div class="tool-head-main">
        <div class="tool-kicker">
          <span class="mono-label">{{ tool.code }}</span>
          <span class="kicker-sep"></span>
          <span class="mono-label">{{ tool.category_name }}</span>
          <span class="badge badge-neutral">{{ tool.priority }}</span>
        </div>
        <h1 class="serif">{{ tool.name }}</h1>
        <p class="tool-summary">{{ tool.summary }}</p>
        <div class="tool-badges">
          <ToolBadge v-if="payload?.site.show_engine_badge !== false" :engine="tool.engine" />
          <span class="badge badge-neutral">
            <AppIcon name="file" :size="12" />
            {{ tool.formats }}
          </span>
          <span v-if="!tool.available" class="badge badge-warn">
            <AppIcon name="alert" :size="12" />
            暂不可用
          </span>
        </div>
      </div>

      <aside class="tool-meta">
        <div class="meta-row">
          <span class="mono-label">LIMITS</span>
          <span>{{ limitText }}</span>
        </div>
        <div v-if="batchText" class="meta-row">
          <span class="mono-label">BATCH</span>
          <span>{{ batchText }}</span>
        </div>
        <div class="meta-row">
          <span class="mono-label">ENGINE</span>
          <span>{{ engineNote }}</span>
        </div>
        <RouterLink v-if="payload?.site.privacy_links_enabled" to="/privacy" class="privacy-link">
          <AppIcon name="shield" :size="13" />
          处理与隐私说明
          <AppIcon name="arrow-up-right" :size="12" />
        </RouterLink>
      </aside>
    </header>

    <div v-if="!tool.available" class="alert alert-warn unavailable">
      <AppIcon name="alert" :size="16" />
      <span>{{ tool.unavailable_reason || '该工具当前不可用。' }}</span>
    </div>

    <slot />

    <ToolRules :tool="tool" :items="rules" />
  </div>
</template>

<style scoped>
.tool-page {
  padding-top: 26px;
  padding-bottom: 24px;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  color: var(--faint);
  font-size: 11.5px;
}

.breadcrumbs a:hover {
  color: var(--ink);
}

.breadcrumbs svg {
  color: var(--line-strong);
}

.breadcrumbs span {
  color: var(--muted);
}

.tool-head {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(0, 0.75fr);
  gap: 36px;
  margin-top: 22px;
  padding: 30px 32px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background:
    radial-gradient(600px 240px at 100% 0%, rgba(222, 78, 39, 0.05), transparent 60%),
    var(--surface);
  box-shadow: var(--shadow-sm);
}

.tool-kicker {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--faint);
}

.tool-kicker .mono-label {
  font-size: 9.5px;
  color: var(--faint);
}

.kicker-sep {
  width: 18px;
  height: 1px;
  background: var(--line-strong);
}

.tool-head h1 {
  margin: 12px 0 10px;
  font-size: clamp(30px, 3.4vw, 42px);
  font-weight: 500;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.tool-summary {
  max-width: 620px;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.75;
}

.tool-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.tool-meta {
  display: flex;
  flex-direction: column;
  gap: 11px;
  align-self: center;
  padding-left: 28px;
  border-left: 1px dashed var(--line-strong);
}

.meta-row {
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 10px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.6;
}

.meta-row .mono-label {
  color: var(--faint);
  font-size: 8.5px;
  padding-top: 3px;
}

.privacy-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
  color: var(--accent-deep);
  font-size: 11.5px;
  text-decoration: underline;
  text-underline-offset: 3px;
  text-decoration-color: rgba(222, 78, 39, 0.3);
}

.unavailable {
  margin-top: 18px;
}

@media (max-width: 900px) {
  .tool-head {
    grid-template-columns: 1fr;
    gap: 22px;
    padding: 24px;
  }

  .tool-meta {
    padding-left: 0;
    padding-top: 18px;
    border-left: 0;
    border-top: 1px dashed var(--line-strong);
  }
}

@media (max-width: 560px) {
  .tool-page {
    padding-top: 18px;
  }

  .tool-head {
    padding: 20px;
  }
}
</style>
