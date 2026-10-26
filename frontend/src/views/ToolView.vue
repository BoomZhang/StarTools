<script setup lang="ts">
import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolCard from '@/components/ToolCard.vue'
import ToolShell from '@/components/ToolShell.vue'
import { componentFor, LOCAL_SUPPORTED } from '@/components/tools/registry'
import { fetchTool } from '@/api/site'
import { useSite } from '@/composables/useSite'
import { DEFAULT_RULES, TOOL_RULES } from '@/data/toolRules'
import type { CategoryKey, Tool } from '@/types'

interface OfflineInfo {
  name: string
  code: string
  slug: string
  category: string
  category_name: string
  reason?: 'offline' | 'unimplemented'
}

const route = useRoute()
const { payload, load: loadSite } = useSite()

const tool = ref<Tool | null>(null)
const loading = ref(true)
const loadError = ref('')
const missing = ref(false)
const offline = ref<OfflineInfo | null>(null)

const rules = computed(() => (tool.value ? TOOL_RULES[tool.value.code] ?? DEFAULT_RULES : DEFAULT_RULES))

const localUnsupported = computed(
  () =>
    Boolean(tool.value) &&
    tool.value?.engine_type === 'dual' &&
    tool.value?.engine === 'local' &&
    !LOCAL_SUPPORTED.has(tool.value!.code),
)

const offlineSuggestions = computed(() => {
  if (!offline.value) return []
  const category = offline.value.category as CategoryKey
  return (payload.value?.tools ?? []).filter((item) => item.category === category).slice(0, 4)
})

async function loadTool(slug: string) {
  loading.value = true
  loadError.value = ''
  missing.value = false
  offline.value = null
  tool.value = null
  try {
    const data = await fetchTool(slug)
    tool.value = data.tool
    document.title = `${data.tool.name} · ${payload.value?.site.name || '随手工具箱'}`
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 410) {
      const detail = error.response.data?.detail
      const info: OfflineInfo = detail?.tool ?? { name: '该工具', code: '', slug, category: '', category_name: '' }
      if (detail?.reason) info.reason = detail.reason
      offline.value = info
    } else if (axios.isAxiosError(error) && error.response?.status === 404) {
      missing.value = true
    } else {
      loadError.value = '工具配置读取失败，请检查后端服务后重试。'
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.slug,
  (slug) => {
    if (typeof slug === 'string' && slug) void loadTool(slug)
  },
  { immediate: true },
)

if (!payload.value) void loadSite()
</script>

<template>
  <div>
    <div v-if="loading" class="container tool-loading">
      <div class="loading-block"></div>
      <div class="loading-grid">
        <div class="loading-panel"></div>
        <div class="loading-panel"></div>
      </div>
    </div>

    <div v-else-if="missing" class="container state-page">
      <p class="eyebrow">404 / NOT FOUND</p>
      <h1 class="serif">这个工具页不存在。</h1>
      <p>链接可能拼写有误，或对应工具编号已不再使用。旧的或拼错的地址不会回退到首页。</p>
      <div class="state-actions">
        <RouterLink to="/" class="button button-ink">
          <AppIcon name="home" :size="15" />
          返回工具目录
        </RouterLink>
        <RouterLink to="/#catalog" class="button button-ghost">浏览全部工具</RouterLink>
      </div>
    </div>

    <div v-else-if="offline" class="container state-page">
      <p class="eyebrow">TOOL OFFLINE / 未上线</p>
      <h1 class="serif">{{ offline.name }}{{ offline.reason === 'unimplemented' ? ' 尚未上线' : ' 已下线' }}</h1>
      <p>
        {{
          offline.reason === 'unimplemented'
            ? '该工具尚未实现，因此不会出现在首页或推荐中。可以先使用同分类下的其他工具。'
            : '该工具已被维护者关闭。已提交的任务不受影响；可以试试同分类下的其他工具。'
        }}
      </p>
      <div v-if="offlineSuggestions.length" class="offline-grid">
        <ToolCard v-for="item in offlineSuggestions" :key="item.code" :tool="item" />
      </div>
      <RouterLink to="/#catalog" class="button button-ink">
        返回工具目录
        <AppIcon name="arrow-right" :size="15" />
      </RouterLink>
    </div>

    <div v-else-if="loadError" class="container state-page">
      <p class="eyebrow">CONFIG ERROR</p>
      <h1 class="serif">工具配置读取失败</h1>
      <p>{{ loadError }}</p>
      <button class="button button-ink" type="button" @click="typeof route.params.slug === 'string' && loadTool(route.params.slug)">
        <AppIcon name="refresh" :size="15" />
        重新加载
      </button>
    </div>

    <ToolShell v-else-if="tool" :tool="tool" :rules="rules">
      <div v-if="localUnsupported" class="alert alert-warn local-unsupported">
        <AppIcon name="alert" :size="16" />
        <span>
          当前管理台将该工具配置为「前端处理」，但该能力暂无浏览器实现。请联系维护者在管理台切回服务端处理；本页不会静默改用另一种引擎。
        </span>
      </div>
      <component :is="componentFor(tool.code)" v-else :key="tool.code" :tool="tool" />
    </ToolShell>
  </div>
</template>

<style scoped>
.tool-loading {
  padding-top: 40px;
}

.loading-block,
.loading-panel {
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--surface-2), var(--surface), var(--surface-2));
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.loading-block {
  height: 210px;
  margin-bottom: 18px;
}

.loading-grid {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr;
  gap: 18px;
}

.loading-panel {
  height: 420px;
}

@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

.state-page {
  padding-top: 60px;
  padding-bottom: 40px;
  max-width: 900px;
}

.state-page h1 {
  margin: 14px 0 12px;
  font-size: clamp(32px, 4vw, 52px);
  font-weight: 500;
}

.state-page > p:not(.eyebrow) {
  max-width: 620px;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.8;
}

.state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
}

.state-page > .button {
  margin-top: 24px;
}

.offline-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 24px 0;
  max-width: 640px;
}

.local-unsupported {
  margin-top: 18px;
}

@media (max-width: 768px) {
  .loading-grid {
    grid-template-columns: 1fr;
  }

  .offline-grid {
    grid-template-columns: 1fr;
  }
}
</style>
