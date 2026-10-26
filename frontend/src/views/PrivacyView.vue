<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { useSite } from '@/composables/useSite'

const { payload } = useSite()
const retention = computed(() => payload.value?.site.retention)

const sections = [
  { id: 'privacy-engine', label: '处理位置' },
  { id: 'privacy-recorded', label: '记录什么' },
  { id: 'privacy-lifecycle', label: '保留与删除' },
  { id: 'privacy-feedback', label: '问题反馈' },
  { id: 'privacy-third-party', label: '第三方能力' },
  { id: 'privacy-control', label: '你的控制' },
]
</script>

<template>
  <div class="privacy container">
    <header class="privacy-hero">
      <p class="eyebrow">PRIVACY / 处理与隐私</p>
      <h1 class="serif">文件应该有明确的去处，<br />结果应该明确地到手里。</h1>
      <p class="hero-lead">
        这里不要求登录，不投放广告，也不在结果文件上加站点水印。每个工具都会在卡片、标题区与结果区标注当前处理位置；
        前端工具的内容不会离开浏览器，服务端处理的文件按固定规则保留与删除。
      </p>
      <div class="hero-metrics">
        <div><strong>{{ retention?.raw_days ?? 30 }} 天</strong><span>服务端原始文件</span></div>
        <div><strong>{{ retention?.result_minutes ?? 60 }} 分钟</strong><span>结果文件</span></div>
        <div><strong>{{ retention?.record_days ?? 90 }} 天</strong><span>使用与反馈记录</span></div>
      </div>
    </header>

    <div class="privacy-layout">
      <nav class="privacy-toc" aria-label="隐私说明目录">
        <p class="mono-label">CONTENTS</p>
        <a v-for="(item, index) in sections" :key="item.id" :href="`#${item.id}`">
          <span class="mono-label">{{ String(index + 1).padStart(2, '0') }}</span>
          {{ item.label }}
        </a>
      </nav>

      <article class="privacy-body">
        <section id="privacy-engine" class="privacy-section">
          <p class="eyebrow">01 / PROCESSING</p>
          <h2 class="serif">处理位置透明，不静默切换</h2>
          <p>
            每个工具只有一种当前处理位置，由管理台逐工具配置。双端工具默认在服务端处理，维护者可以切为前端；
            仅前端与仅服务端工具的引擎开关在管理台锁定，不能操作。
          </p>
          <div class="engine-cards">
            <div class="engine-card local">
              <span class="badge badge-local"><AppIcon name="monitor" :size="12" /> 前端</span>
              <h3>内容不出浏览器</h3>
              <p>文件与文本只在当前页面内存中处理，不上传。任务结束后只上报一条不含文件名与内容的使用记录。</p>
            </div>
            <div class="engine-card server">
              <span class="badge badge-server"><AppIcon name="server" :size="12" /> 服务端</span>
              <h3>上传前明确告知</h3>
              <p>只接收当前任务必需的文件；上传前显示文件数量与用途，并说明文件会上传到服务器处理。</p>
            </div>
          </div>
          <p class="privacy-note">
            处理失败不会自动改用另一种引擎。双端工具会提供显式的「改用前端 / 服务端重试」动作，由你确认。
          </p>
        </section>

        <section id="privacy-recorded" class="privacy-section">
          <p class="eyebrow">02 / RECORDS</p>
          <h2 class="serif">使用记录不含内容</h2>
          <p>每次成功创建任务会记录一条使用记录，用于统计与限流排查。记录字段固定，不包含文件内容。</p>
          <div class="record-grid">
            <div>
              <h4>会记录</h4>
              <ul>
                <li>时间、工具编号与名称</li>
                <li>结果、处理引擎、耗时</li>
                <li>IP、文件数量与总大小</li>
                <li>错误编号、是否重试</li>
              </ul>
            </div>
            <div>
              <h4>不会记录</h4>
              <ul>
                <li>文件名与文件内容</li>
                <li>输入文本、识别结果</li>
                <li>密码、哈希值与剪贴板内容</li>
                <li>任何用于画像或营销的信息</li>
              </ul>
            </div>
          </div>
          <p class="privacy-note">IP 只用于统计与限流，只有已登录维护者可见，不用于访客画像。</p>
        </section>

        <section id="privacy-lifecycle" class="privacy-section">
          <p class="eyebrow">03 / LIFECYCLE</p>
          <h2 class="serif">保留与删除规则</h2>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr><th>对象</th><th>保留时长</th><th>能否提前删除</th></tr>
              </thead>
              <tbody>
                <tr><td>原始文件（仅服务端处理）</td><td class="mono-cell">30 天</td><td>访客不能；维护者可删除</td></tr>
                <tr><td>结果文件（仅服务端处理）</td><td class="mono-cell">1 小时</td><td>访客可删除结果，不影响原始文件</td></tr>
                <tr><td>使用记录</td><td class="mono-cell">90 天</td><td>不提供单条删除</td></tr>
                <tr><td>问题反馈</td><td class="mono-cell">90 天</td><td>不提供删除与导出</td></tr>
                <tr><td>管理操作记录</td><td class="mono-cell">90 天</td><td>不提供单条删除</td></tr>
              </tbody>
            </table>
          </div>
          <p class="privacy-note">
            到期自动删除，不进入回收站，不提供恢复。结果删除或过期不影响原始文件；原始文件仅限已登录维护者查看与下载，并写入操作记录。
          </p>
        </section>

        <section id="privacy-feedback" class="privacy-section">
          <p class="eyebrow">04 / FEEDBACK</p>
          <h2 class="serif">反馈只对维护者可见</h2>
          <p>
            反馈是独立于工具任务的提交，不进入处理链路，不产生结果文件。提交时会附带当前页面、工具 / 任务 / 错误编号、
            浏览器与视口信息，用于排查问题；不包含文件名、文件内容、输入文本或识别结果。
          </p>
          <p class="privacy-note">反馈不生成公开页面，不提供进度查询与站内回复；记录保留 90 天。</p>
        </section>

        <section id="privacy-third-party" class="privacy-section">
          <p class="eyebrow">05 / THIRD PARTY</p>
          <h2 class="serif">第三方能力披露</h2>
          <p>
            OCR 使用部署在本站的 Tesseract 引擎，语音识别使用本地 Whisper 模型，Office 转换使用本地 LibreOffice，
            音视频转码使用本地 ffmpeg；文件不会发送给外部服务。未来若接入第三方能力，工具页必须列出服务商名称、
            处理地区与保留政策；未完成披露前对应工具不会上线。
          </p>
          <p class="privacy-note">当前没有广告、统计脚本、社交插件或远程字体请求。</p>
        </section>

        <section id="privacy-control" class="privacy-section">
          <p class="eyebrow">06 / CONTROL</p>
          <h2 class="serif">你可以在本机清除什么</h2>
          <p>
            服务端上传确认状态与当前标签页的任务编号保存在本机浏览器。
            页脚的「清除本机数据」会重置这些偏好，不影响已提交的服务端任务或已提交的反馈。
          </p>
          <p class="privacy-note">
            任务编号只写入会话存储，关闭标签页即失效；不生成跨设备或跨浏览器的恢复凭据。
          </p>
          <div class="privacy-actions">
            <RouterLink to="/#catalog" class="button button-ink">回到工具目录</RouterLink>
            <RouterLink v-if="payload?.site.feedback_enabled" to="/feedback" class="button button-ghost">提交问题反馈</RouterLink>
          </div>
        </section>
      </article>
    </div>
  </div>
</template>

<style scoped>
.privacy {
  padding-top: 48px;
  padding-bottom: 36px;
}

.privacy-hero {
  max-width: 880px;
  padding-bottom: 40px;
  border-bottom: 1px solid var(--line-strong);
}

.privacy-hero h1 {
  margin: 16px 0 20px;
  font-size: clamp(32px, 4.6vw, 56px);
  font-weight: 500;
  line-height: 1.24;
  letter-spacing: -0.015em;
}

.hero-lead {
  max-width: 700px;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.85;
}

.hero-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 36px;
  margin-top: 28px;
}

.hero-metrics > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.hero-metrics strong {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 600;
}

.hero-metrics span {
  color: var(--faint);
  font-size: 10.5px;
}

.privacy-layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 56px;
  margin-top: 40px;
}

.privacy-toc {
  position: sticky;
  top: calc(var(--header-h) + 24px);
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.privacy-toc > .mono-label {
  margin-bottom: 10px;
  color: var(--faint);
  font-size: 8.5px;
}

.privacy-toc a {
  display: flex;
  align-items: baseline;
  gap: 9px;
  padding: 8px 0;
  color: var(--muted);
  font-size: 12px;
  border-bottom: 1px solid transparent;
}

.privacy-toc a:hover {
  color: var(--ink);
}

.privacy-toc .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.privacy-body {
  max-width: 780px;
}

.privacy-section {
  padding: 0 0 38px;
  margin-bottom: 38px;
  border-bottom: 1px solid var(--line);
  scroll-margin-top: 100px;
}

.privacy-section:last-child {
  border-bottom: 0;
  margin-bottom: 0;
}

.privacy-section h2 {
  margin: 12px 0 16px;
  font-size: clamp(24px, 3vw, 32px);
  font-weight: 500;
  line-height: 1.35;
}

.privacy-section p {
  color: var(--ink-2);
  font-size: 13.5px;
  line-height: 1.9;
}

.privacy-section p + p {
  margin-top: 10px;
}

.privacy-note {
  margin-top: 14px;
  padding-left: 12px;
  border-left: 2px solid var(--accent-soft);
  color: var(--faint) !important;
  font-size: 11.5px !important;
  line-height: 1.8 !important;
}

.engine-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 20px;
}

.engine-card {
  padding: 17px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
}

.engine-card h3 {
  margin: 11px 0 6px;
  font-size: 13.5px;
}

.engine-card p {
  font-size: 11.5px !important;
  line-height: 1.75 !important;
  color: var(--muted) !important;
}

.record-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.record-grid > div {
  padding: 15px 17px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
}

.record-grid h4 {
  margin-bottom: 9px;
  font-size: 12px;
}

.record-grid ul {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: var(--muted);
  font-size: 11.5px;
}

.record-grid li::before {
  content: '·';
  margin-right: 6px;
  color: var(--faint);
}

.table-wrap {
  margin-top: 18px;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: auto;
  background: var(--surface);
}

.table td {
  color: var(--muted);
  font-size: 11.5px;
}

.privacy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

@media (max-width: 900px) {
  .privacy-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
  }

  .privacy-toc {
    position: static;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--line);
  }

  .privacy-toc > .mono-label {
    display: none;
  }

  .privacy-toc a {
    padding: 5px 9px;
    border: 1px solid var(--line);
    border-radius: 999px;
    font-size: 11px;
  }
}

@media (max-width: 620px) {
  .engine-cards,
  .record-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-metrics {
    gap: 22px;
  }
}
</style>
