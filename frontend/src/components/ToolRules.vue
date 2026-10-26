<script setup lang="ts">
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import ToolBadge from '@/components/ToolBadge.vue'
import { useSite } from '@/composables/useSite'
import type { Tool } from '@/types'
import { setFeedbackPrefill } from '@/utils/feedbackPrefill'

const props = defineProps<{ tool: Tool; items: string[] }>()
const router = useRouter()
const { payload } = useSite()

function goFeedback() {
  setFeedbackPrefill({ toolCode: props.tool.code, path: `/t/${props.tool.slug}` })
  void router.push('/feedback')
}
</script>

<template>
  <details class="rules-section">
    <summary>
      <span class="rules-summary-main">
        <span class="mono-label">RULES / 规则</span>
        <span class="rules-title">支持格式、边界规则与常见失败原因</span>
      </span>
      <span class="rules-toggle">
        展开
        <AppIcon name="chevron-down" :size="14" />
      </span>
    </summary>
    <div class="rules-content">
      <div class="rules-engine">
        <ToolBadge v-if="payload?.site.show_engine_badge !== false" :engine="tool.engine" />
        <span>
          {{
            tool.engine === 'server'
              ? '当前由服务端处理：文件会上传到站点服务器，仅维护者可访问。已提交任务按提交时的配置继续。'
              : '当前由浏览器前端处理：文件与文本不上传，结果只存在当前页面内存，刷新即丢失。'
          }}
        </span>
      </div>
      <ul class="rules-list">
        <li v-for="(item, index) in items" :key="index">
          <span class="rule-index mono-label">{{ String(index + 1).padStart(2, '0') }}</span>
          <span>{{ item }}</span>
        </li>
      </ul>
      <p v-if="payload?.site.feedback_enabled !== false" class="rules-foot">
        失败时保留输入与参数。需要帮助时
        <button class="text-button feedback-link" type="button" @click="goFeedback">反馈此问题</button>。
      </p>
    </div>
  </details>
</template>

<style scoped>
.rules-section {
  margin-top: 26px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.rules-section summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  cursor: pointer;
  list-style: none;
}

.rules-section summary::-webkit-details-marker {
  display: none;
}

.rules-summary-main {
  display: flex;
  align-items: baseline;
  gap: 14px;
  min-width: 0;
}

.rules-summary-main .mono-label {
  color: var(--faint);
  font-size: 8.5px;
  flex: none;
}

.rules-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-2);
}

.rules-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex: none;
  color: var(--faint);
  font-size: 11px;
}

.rules-section[open] .rules-toggle svg {
  transform: rotate(180deg);
}

.rules-content {
  padding: 0 22px 22px;
  border-top: 1px dashed var(--line);
}

.rules-engine {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 9px;
  background: var(--surface-2);
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
}

.rules-engine .badge {
  margin-top: 1px;
  flex: none;
}

.rules-list {
  display: flex;
  flex-direction: column;
  margin-top: 16px;
}

.rules-list li {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(217, 211, 196, 0.5);
  color: var(--ink-2);
  font-size: 12.5px;
  line-height: 1.7;
}

.rule-index {
  color: var(--accent);
  font-size: 9px;
  padding-top: 3px;
}

.rules-foot {
  margin-top: 14px;
  color: var(--faint);
  font-size: 11px;
  line-height: 1.7;
}

.feedback-link {
  font-size: 11px;
}

@media (max-width: 560px) {
  .rules-summary-main {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
