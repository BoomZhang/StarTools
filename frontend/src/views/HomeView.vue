<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolCard from '@/components/ToolCard.vue'
import { useSite } from '@/composables/useSite'
import type { CategoryKey } from '@/types'

const { payload, loading, error, load } = useSite()

const activeCategory = ref<'all' | CategoryKey>('all')

const onlineTools = computed(() => payload.value?.tools ?? [])

const visibleTools = computed(() =>
  onlineTools.value.filter((tool) => activeCategory.value === 'all' || tool.category === activeCategory.value),
)

const groupedTools = computed(() => {
  if (!payload.value) return []
  return payload.value.categories
    .map((category) => ({
      category,
      tools: visibleTools.value.filter((tool) => tool.category === category.key),
    }))
    .filter((group) => group.tools.length > 0)
})

function setCategory(key: 'all' | CategoryKey) {
  activeCategory.value = key
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="container hero-inner">
        <div class="hero-copy">
          <p class="eyebrow">WORKBENCH / DAILY UTILITIES</p>
          <h1 class="serif">
            小事，<br />
            <em>随手解决。</em>
          </h1>
          <p class="hero-lead">
            图片、PDF、文字、编码、二维码。所有工具打开即用，<br class="desktop-only" />
            不用登录，也不用先花十分钟找网站。
          </p>

          <ul class="trust-points">
            <li><AppIcon name="check" :size="14" /> 处理位置逐工具可见</li>
            <li><AppIcon name="check" :size="14" /> 前端工具内容不出浏览器</li>
            <li><AppIcon name="check" :size="14" /> 结果不加水印</li>
          </ul>
        </div>

        <div class="hero-stage" aria-hidden="true">
          <div class="stage-back">
            <span class="mono-label">WORKBENCH / 2026</span>
            <span class="stage-status"><span class="dot"></span> ALL SYSTEMS NORMAL</span>
          </div>
          <div class="stage-sheet">
            <div class="stage-sheet-head">
              <span class="mono-label">IMG-01 / CONVERT</span>
              <span class="stage-stamp">完成</span>
            </div>
            <div class="stage-title serif">图片格式转换</div>
            <div class="stage-file">
              <span class="file-tag">SOURCE</span>
              <span class="file-name mono">IMG_2048.HEIC</span>
              <span class="file-size mono">4.2 MB</span>
            </div>
            <div class="stage-arrow">
              <span class="rule-line"></span>
              <AppIcon name="arrow-right" :size="16" />
            </div>
            <div class="stage-file is-output">
              <span class="file-tag">OUTPUT</span>
              <span class="file-name mono">IMG_2048.JPG</span>
              <span class="file-size mono">1.1 MB</span>
            </div>
            <div class="stage-foot">
              <span><AppIcon name="check-circle" :size="13" /> 转换完成 · 用时 3.8 秒</span>
              <span class="stage-download">下载</span>
            </div>
          </div>
          <div class="stage-note">
            <span class="mono-label">OPEN / NO LOGIN</span>
            <span>打开即用，不做多余记录。</span>
          </div>
        </div>
      </div>

      <div class="container hero-stats">
        <div><strong>{{ payload?.site.online_tools ?? '—' }}</strong><span>已上线工具</span></div>
        <div><strong>{{ payload?.site.total_tools ?? 39 }}</strong><span>工具总数</span></div>
        <div><strong>0</strong><span>广告</span></div>
        <div><strong>0</strong><span>注册</span></div>
        <p class="hero-stats-note mono-label">NO LOGIN · NO ADS · NO WATERMARK</p>
      </div>
    </section>

    <div class="container">
      <div v-if="error" class="alert alert-danger config-error">
        <AppIcon name="alert" :size="16" />
        <span>{{ error }}，请确认后端服务已启动。</span>
        <button class="text-button" type="button" @click="load(true)">重新加载</button>
      </div>

      <section id="catalog" class="catalog-section" aria-labelledby="catalog-title">
        <div class="section-head">
          <div>
            <p class="eyebrow">THE TOOL DRAWER</p>
            <h2 id="catalog-title" class="section-title serif">需要的东西，就在这里。</h2>
          </div>
          <p class="section-note">
            {{ payload?.site.online_tools ?? '—' }} 个已上线工具，全部打开即用。<br />
            处理位置与限额来自管理台当前配置。
          </p>
        </div>

        <div class="category-bar" role="tablist" aria-label="工具分类">
          <button
            type="button"
            :class="{ 'is-active': activeCategory === 'all' }"
            @click="setCategory('all')"
          >
            全部
            <span class="mono-label">{{ onlineTools.length }}</span>
          </button>
          <button
            v-for="category in payload?.categories ?? []"
            :key="category.key"
            type="button"
            :class="{ 'is-active': activeCategory === category.key }"
            :disabled="!onlineTools.some((tool) => tool.category === category.key)"
            @click="setCategory(category.key)"
          >
            {{ category.name }}
            <span class="mono-label">{{ onlineTools.filter((tool) => tool.category === category.key).length }}</span>
          </button>
        </div>

        <p class="result-count" aria-live="polite">显示 {{ visibleTools.length }} 个工具</p>

        <div v-if="loading && !payload" class="skeleton-grid">
          <div v-for="index in 6" :key="index" class="skeleton-card"></div>
        </div>

        <section
          v-for="(group, index) in groupedTools"
          :key="group.category.key"
          class="tool-group"
          :aria-labelledby="`group-${group.category.key}`"
        >
          <header class="group-head">
            <div class="group-index mono-label">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="group-heading">
              <h3 :id="`group-${group.category.key}`" class="serif">{{ group.category.name }}</h3>
              <span class="group-count mono-label">{{ group.tools.length }} TOOLS</span>
            </div>
            <p class="group-blurb">{{ group.category.blurb }}</p>
          </header>
          <div class="tool-grid">
            <ToolCard v-for="tool in group.tools" :key="tool.code" :tool="tool" />
          </div>
        </section>
      </section>

      <section class="promise-strip">
        <div class="promise-main">
          <AppIcon name="shield" :size="20" />
          <div>
            <h3 class="serif">没有广告，也没有「免费额度」。</h3>
            <p>访客免登录，不设注册，不弹诱导下载，不在结果文件上加站点水印。处理位置逐工具可见。</p>
          </div>
        </div>
        <RouterLink v-if="payload?.site.privacy_links_enabled" to="/privacy" class="promise-link">
          了解处理与隐私
          <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home {
  padding-bottom: 28px;
}

.hero {
  position: relative;
  overflow: hidden;
  border-bottom: 1px solid var(--line-strong);
  background:
    radial-gradient(900px 460px at 82% 18%, rgba(222, 78, 39, 0.08), transparent 60%),
    radial-gradient(700px 500px at 8% 80%, rgba(37, 102, 79, 0.07), transparent 65%),
    var(--paper);
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(193, 186, 168, 0.16) 1px, transparent 1px),
    linear-gradient(90deg, rgba(193, 186, 168, 0.16) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: radial-gradient(circle at 70% 40%, black, transparent 70%);
  pointer-events: none;
}

.hero-inner {
  position: relative;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  align-items: center;
  gap: 56px;
  padding-top: 66px;
  padding-bottom: 54px;
}

.hero-copy h1 {
  margin: 18px 0 20px;
  font-size: clamp(46px, 5.4vw, 76px);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.hero-copy h1 em {
  position: relative;
  font-style: normal;
  color: var(--accent-deep);
}

.hero-copy h1 em::after {
  content: '';
  position: absolute;
  left: 0;
  right: -4px;
  bottom: 2px;
  height: 8px;
  background: var(--accent-soft);
  z-index: -1;
  transform: skewX(-6deg);
}

.hero-lead {
  color: var(--muted);
  font-size: 14.5px;
  line-height: 1.8;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  width: min(100%, 540px);
  height: 58px;
  margin-top: 28px;
  padding: 0 16px;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  color: var(--faint);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-box:focus-within {
  border-color: var(--ink-2);
  box-shadow: 0 0 0 4px rgba(44, 48, 40, 0.07), var(--shadow-sm);
}

.search-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--ink);
  font-size: 14px;
  outline: none;
}

.search-box input::-webkit-search-cancel-button {
  display: none;
}

.search-kbd {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--faint);
  font-size: 10px;
}

.clear-search {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--surface-2);
  color: var(--muted);
}

.quick-terms {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.quick-terms > span {
  color: var(--faint);
  margin-right: 2px;
}

.quick-terms button {
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(252, 251, 247, 0.6);
  color: var(--muted);
  font-size: 11.5px;
  transition: border-color 0.2s, color 0.2s, background-color 0.2s;
}

.quick-terms button:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-deep);
}

.trust-points {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 30px;
  color: var(--muted);
  font-size: 11.5px;
}

.trust-points li {
  display: flex;
  align-items: center;
  gap: 6px;
}

.trust-points svg {
  color: var(--server);
}

.hero-stage {
  position: relative;
  min-height: 390px;
  padding: 22px 0 0 22px;
}

.stage-back {
  position: absolute;
  top: 8px;
  right: 0;
  left: 60px;
  height: 330px;
  padding: 22px 26px;
  border-radius: 6px;
  background: var(--forest);
  color: #aeb5a9;
  transform: rotate(3.2deg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-back .mono-label {
  color: #828c7f;
}

.stage-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: auto;
  color: #8f978a;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
}

.stage-status .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #5eae8b;
}

.stage-sheet {
  position: relative;
  z-index: 2;
  width: calc(100% - 28px);
  padding: 24px 24px 20px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: var(--surface);
  box-shadow: var(--shadow-md);
  transform: rotate(-1.4deg);
}

.stage-sheet::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 27px,
    rgba(217, 211, 196, 0.22) 27px,
    rgba(217, 211, 196, 0.22) 28px
  );
  pointer-events: none;
}

.stage-sheet-head {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--faint);
}

.stage-stamp {
  padding: 3px 10px;
  border: 1.5px solid var(--accent);
  border-radius: 3px;
  color: var(--accent);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  transform: rotate(4deg);
}

.stage-title {
  position: relative;
  margin: 20px 0 18px;
  font-size: 26px;
  font-weight: 600;
}

.stage-file {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(247, 244, 236, 0.75);
  font-size: 12px;
}

.stage-file.is-output {
  border-color: rgba(37, 102, 79, 0.35);
  background: var(--server-soft);
}

.file-tag {
  color: var(--faint);
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.08em;
}

.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11.5px;
}

.file-size {
  color: var(--faint);
  font-size: 10px;
}

.stage-arrow {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  color: var(--faint);
}

.stage-arrow .rule-line {
  flex: 1;
  height: 1px;
  border-top: 1px dashed var(--line-strong);
}

.stage-foot {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 18px;
  color: var(--muted);
  font-size: 11px;
}

.stage-foot span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.stage-foot svg {
  color: var(--server);
}

.stage-download {
  padding: 6px 12px;
  border-radius: 4px;
  background: var(--ink);
  color: var(--paper);
  font-size: 10px;
}

.stage-note {
  position: absolute;
  right: 4px;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--faint);
  font-size: 10px;
  transform: rotate(-2deg);
}

.stage-note .mono-label {
  color: var(--accent-deep);
  font-size: 8px;
}

.hero-stats {
  position: relative;
  display: flex;
  align-items: center;
  gap: 44px;
  padding: 18px 0 20px;
  border-top: 1px dashed var(--line-strong);
}

.hero-stats > div {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.hero-stats strong {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
}

.hero-stats span {
  color: var(--muted);
  font-size: 11.5px;
}

.hero-stats-note {
  margin-left: auto;
  color: var(--faint);
  font-size: 8.5px;
}

.config-error {
  margin-top: 26px;
  align-items: center;
}

.catalog-section {
  padding-top: 54px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 24px;
}

.section-title {
  margin-top: 10px;
  font-size: clamp(28px, 3.2vw, 40px);
  font-weight: 500;
  letter-spacing: -0.01em;
  line-height: 1.25;
}

.section-note {
  max-width: 330px;
  color: var(--faint);
  font-size: 11.5px;
  line-height: 1.8;
  text-align: right;
}

.recent-list {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.recent-chip {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 40px;
  padding: 0 13px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--ink-2);
  font-size: 12.5px;
  transition: border-color 0.2s, background-color 0.2s;
}

.recent-chip:hover {
  border-color: var(--ink-2);
  background: #fff;
}

.recent-code {
  color: var(--faint);
  font-size: 8.5px;
}

.category-bar {
  position: sticky;
  top: var(--header-h);
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 14px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(252, 251, 247, 0.94);
  backdrop-filter: blur(12px);
  overflow-x: auto;
  scrollbar-width: none;
}

.category-bar::-webkit-scrollbar {
  display: none;
}

.category-bar button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 13px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 12.5px;
  white-space: nowrap;
  transition: background-color 0.2s, color 0.2s;
}

.category-bar button:hover:not(:disabled) {
  background: var(--surface-2);
  color: var(--ink);
}

.category-bar button.is-active {
  background: var(--ink);
  color: var(--paper);
}

.category-bar button.is-active .mono-label {
  color: rgba(244, 241, 232, 0.6);
}

.category-bar button:disabled {
  opacity: 0.36;
  cursor: not-allowed;
}

.category-bar .mono-label {
  font-size: 8.5px;
  color: var(--faint);
}

.result-count {
  margin: 0 0 18px 4px;
  color: var(--faint);
  font-size: 11px;
  font-family: var(--font-mono);
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.skeleton-card {
  height: 180px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--surface-2), var(--surface), var(--surface-2));
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

.tool-group {
  padding: 26px 0 8px;
  border-top: 1px solid var(--line);
}

.tool-group:first-of-type {
  border-top: 0;
}

.group-head {
  display: grid;
  grid-template-columns: 42px minmax(0, auto) 1fr;
  align-items: baseline;
  gap: 18px;
  margin-bottom: 20px;
}

.group-index {
  color: var(--accent);
  font-size: 12px;
  letter-spacing: 0.04em;
}

.group-heading {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.group-heading h3 {
  font-size: 24px;
  font-weight: 600;
}

.group-count {
  color: var(--faint);
  font-size: 8.5px;
}

.group-blurb {
  justify-self: end;
  color: var(--faint);
  font-size: 11.5px;
  text-align: right;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.no-results {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 36px;
  align-items: start;
  padding: 28px;
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-md);
  background: rgba(252, 251, 247, 0.55);
}

.no-results-copy h3 {
  margin: 14px 0 10px;
  font-size: 26px;
  font-weight: 500;
}

.no-results-copy p {
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.7;
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.suggestion-chips button {
  padding: 6px 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 11.5px;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.suggestion-grid :deep(.tool-card) {
  min-height: 160px;
}

.promise-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  margin-top: 54px;
  padding: 26px 28px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.promise-main {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.promise-main > svg {
  color: var(--server);
  margin-top: 3px;
}

.promise-main h3 {
  font-size: 20px;
  font-weight: 600;
}

.promise-main p {
  max-width: 680px;
  margin-top: 7px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.promise-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: none;
  color: var(--accent-deep);
  font-size: 12.5px;
}

@media (max-width: 1080px) {
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 36px;
  }

  .hero-stage {
    max-width: 520px;
  }

  .hero-stats-note {
    display: none;
  }

  .tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .no-results {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-inner {
    padding-top: 42px;
  }

  .hero-stage {
    display: none;
  }

  .hero-copy h1 {
    font-size: 46px;
  }

  .desktop-only {
    display: none;
  }

  .section-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .section-note {
    text-align: left;
  }

  .group-head {
    grid-template-columns: 34px 1fr;
    gap: 10px;
  }

  .group-blurb {
    grid-column: 2;
    justify-self: start;
    text-align: left;
  }

  .tool-grid,
  .skeleton-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .suggestion-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .promise-strip {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-stats {
    gap: 22px;
    flex-wrap: wrap;
  }

  .category-bar {
    top: 68px;
  }
}

@media (max-width: 480px) {
  .hero-copy h1 {
    font-size: 40px;
  }

  .hero-lead {
    font-size: 13px;
  }

  .trust-points {
    flex-direction: column;
    gap: 8px;
  }

  .search-kbd {
    display: none;
  }

  .hero-stats > div {
    min-width: 68px;
  }
}
</style>
