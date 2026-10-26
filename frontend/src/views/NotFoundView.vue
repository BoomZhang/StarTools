<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolCard from '@/components/ToolCard.vue'
import { useSite } from '@/composables/useSite'
import type { Tool } from '@/types'

const { payload, load } = useSite()
const query = ref('')

void load()

const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  const tools = payload.value?.tools ?? []
  if (!q) return []
  return tools
    .filter((tool) =>
      [tool.name, tool.code, tool.summary, tool.formats, ...tool.aliases, ...tool.keywords]
        .join(' ')
        .toLowerCase()
        .includes(q),
    )
    .slice(0, 6)
})

const suggestions = computed(() => {
  const tools = payload.value?.tools ?? []
  const preferred = ['image-convert', 'pdf-merge', 'qr-generate', 'text-count']
  const picked = preferred
    .map((slug) => tools.find((tool) => tool.slug === slug))
    .filter((tool): tool is Tool => Boolean(tool))
  return (picked.length ? picked : tools.slice(0, 4)).slice(0, 4)
})
</script>

<template>
  <div class="not-found container">
    <div class="not-found-main">
      <p class="eyebrow">404 / NOT FOUND</p>
      <h1 class="serif">这页工具纸，<br />似乎被抽走了。</h1>
      <p>地址可能拼写有误，或对应的工具已经下线。旧的或拼错的链接不会回退到首页，避免让你误以为链接仍然有效。</p>

      <div class="search-box">
        <AppIcon name="search" :size="18" />
        <input v-model="query" type="search" placeholder="搜索已上线工具，例如「PDF」或「二维码」" aria-label="搜索工具" />
      </div>

      <div v-if="query && results.length" class="search-results">
        <RouterLink v-for="tool in results" :key="tool.code" :to="`/t/${tool.slug}`" class="search-result">
          <span class="mono-label">{{ tool.code }}</span>
          <strong>{{ tool.name }}</strong>
          <AppIcon name="arrow-up-right" :size="13" />
        </RouterLink>
      </div>
      <p v-else-if="query" class="no-match">没有找到匹配工具。可以试试「图片转换」「PDF 合并」「二维码」。</p>

      <div class="not-found-actions">
        <RouterLink to="/" class="button button-ink">
          <AppIcon name="home" :size="15" />
          返回工具目录
        </RouterLink>
        <RouterLink to="/#catalog" class="button button-ghost">浏览全部工具</RouterLink>
      </div>
    </div>

    <section class="popular">
      <p class="eyebrow">POPULAR / 热门工具</p>
      <div class="popular-grid">
        <ToolCard v-for="tool in suggestions" :key="tool.code" :tool="tool" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.not-found {
  padding-top: 60px;
  padding-bottom: 30px;
}

.not-found-main h1 {
  margin: 16px 0 16px;
  font-size: clamp(36px, 5vw, 62px);
  font-weight: 500;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.not-found-main > p:not(.eyebrow):not(.no-match) {
  max-width: 620px;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.85;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 11px;
  width: min(100%, 540px);
  height: 54px;
  margin-top: 26px;
  padding: 0 15px;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  background: var(--surface);
  color: var(--faint);
}

.search-box:focus-within {
  border-color: var(--ink-2);
}

.search-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  outline: none;
  font-size: 13.5px;
}

.search-results {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.search-result {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  font-size: 12px;
}

.search-result .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.search-result strong {
  font-weight: 500;
}

.search-result:hover {
  border-color: var(--ink-2);
}

.no-match {
  margin-top: 13px;
  color: var(--faint);
  font-size: 11.5px;
}

.not-found-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 26px;
}

.popular {
  margin-top: 50px;
  padding-top: 28px;
  border-top: 1px solid var(--line);
}

.popular-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .popular-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .popular-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
