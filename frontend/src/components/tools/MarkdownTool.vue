<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import type { Tool } from '@/types'
import { downloadText } from '@/utils/files'

const props = defineProps<{ tool: Tool }>()

const text = ref('')
const startedAt = ref(0)
const exported = ref(false)

const rendered = computed(() => {
  if (!text.value.trim()) return ''
  const html = marked.parse(text.value, { gfm: true, breaks: false }) as string
  return DOMPurify.sanitize(html, {
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  })
})

const bytes = computed(() => new TextEncoder().encode(text.value).length)

function fillExample() {
  text.value = `# 随手工具箱

一个**访客免登录**的日常工具站。

| 工具 | 处理位置 |
| --- | --- |
| 图片压缩 | 服务端 |
| JSON 格式化 | 前端 |

\`\`\`js
const answer = 42
console.log(answer)
\`\`\`

> 文件应该有明确的去处，结果应该明确地到手里。
`
}

function exportHtml() {
  if (!rendered.value) return
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Markdown 导出</title>
<style>
  body { margin: 0; background: #f4f1e8; color: #191c17; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.75; }
  main { max-width: 780px; margin: 40px auto; padding: 32px; background: #fcfbf7; border: 1px solid #d9d3c4; border-radius: 12px; }
  h1, h2, h3 { font-family: "Songti SC", serif; font-weight: 600; line-height: 1.35; }
  code { font-family: ui-monospace, monospace; background: #f7f4ec; padding: 2px 5px; border-radius: 4px; }
  pre { background: #101613; color: #d7ded4; padding: 14px; border-radius: 8px; overflow: auto; }
  pre code { background: transparent; padding: 0; }
  table { width: 100%; border-collapse: collapse; }
  th, td { border: 1px solid #d9d3c4; padding: 8px 10px; text-align: left; }
  blockquote { margin: 16px 0; padding-left: 12px; border-left: 3px solid #de4e27; color: #62665b; }
  a { color: #a93215; }
</style>
</head>
<body><main>${rendered.value}</main></body>
</html>`
  downloadText('markdown-preview.html', html, 'text/html;charset=utf-8')
  exported.value = true
  void reportUsage({
    tool_code: props.tool.code,
    result: 'succeeded',
    duration_ms: Math.round(performance.now() - (startedAt.value || performance.now())),
  })
  window.setTimeout(() => {
    exported.value = false
  }, 1800)
}

function onInput() {
  if (!startedAt.value) startedAt.value = performance.now()
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / MARKDOWN</span>
            <h2>编写内容</h2>
          </div>
          <span class="section-aside">{{ (bytes / 1024).toFixed(1) }} KB / 2048 KB</span>
        </div>
        <textarea
          v-model="text"
          class="textarea textarea-tall markdown-input"
          placeholder="# 标题&#10;&#10;支持 GFM 表格、代码块与引用…"
          spellcheck="false"
          @input="onInput"
        ></textarea>
        <div class="markdown-actions">
          <button class="text-button" type="button" @click="fillExample">填入示例</button>
          <span class="tool-tip">实时预览在右侧；脚本、事件属性与外部嵌入会被清理。</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">02 / EXPORT</span>
            <h2>导出</h2>
          </div>
        </div>
        <p class="tool-tip">导出 HTML 使用内联样式，不加载远程样式或字体；内容已做安全清理。</p>
        <div class="run-bar">
          <p class="run-note">Markdown 只在浏览器内渲染，不上传文本。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!rendered" @click="exportHtml">
              <AppIcon name="download" :size="15" />
              {{ exported ? '已导出' : '导出 HTML' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">PREVIEW / 实时预览</span>
          <span v-if="rendered" class="badge badge-local">前端</span>
          <span v-else class="badge badge-neutral">等待输入</span>
        </div>
        <div class="local-result-body preview-body">
          <div v-if="!rendered" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="file" :size="21" /></span>
            <strong>等待输入</strong>
            <p>输入 Markdown 后，右侧会实时渲染。</p>
          </div>
          <article v-else class="markdown-body" v-html="rendered"></article>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.markdown-input {
  min-height: 460px;
  font-family: var(--font-mono);
  font-size: 12.5px;
  line-height: 1.75;
}

.markdown-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 9px;
}

.preview-body {
  max-height: 720px;
  overflow-y: auto;
}

.markdown-body {
  color: var(--ink-2);
  font-size: 12.5px;
  line-height: 1.85;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 1.1em 0 0.55em;
  font-family: var(--font-display);
  font-weight: 600;
  line-height: 1.35;
}

.markdown-body :deep(h1) {
  font-size: 24px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 8px;
}

.markdown-body :deep(h2) {
  font-size: 20px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
}

.markdown-body :deep(p) {
  margin: 0.65em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.65em 0;
  padding-left: 1.4em;
  list-style: disc;
}

.markdown-body :deep(ol) {
  list-style: decimal;
}

.markdown-body :deep(li) {
  margin: 0.25em 0;
}

.markdown-body :deep(code) {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--surface-2);
  font-family: var(--font-mono);
  font-size: 11px;
}

.markdown-body :deep(pre) {
  margin: 0.9em 0;
  padding: 12px;
  border-radius: 8px;
  background: #101613;
  color: #d7ded4;
  overflow: auto;
  font-size: 11px;
  line-height: 1.65;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
  font-size: inherit;
}

.markdown-body :deep(table) {
  width: 100%;
  margin: 0.9em 0;
  border-collapse: collapse;
  font-size: 11.5px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--line);
  padding: 7px 9px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--surface-2);
}

.markdown-body :deep(blockquote) {
  margin: 0.9em 0;
  padding-left: 12px;
  border-left: 3px solid var(--accent);
  color: var(--muted);
}

.markdown-body :deep(a) {
  color: var(--accent-deep);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

.markdown-body :deep(hr) {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 1.2em 0;
}
</style>
