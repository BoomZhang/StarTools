<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { clearLocalPreferences } from '@/composables/useUploadConsent'
import { useSite } from '@/composables/useSite'

const { payload } = useSite()
const cleared = ref(false)

const popular = computed(() => {
  const slugs = ['image-convert', 'pdf-merge', 'qr-generate', 'text-count']
  return (payload.value?.tools ?? []).filter((tool) => slugs.includes(tool.slug)).slice(0, 4)
})

const siteName = computed(() => payload.value?.site.name || '随手工具箱')
const logoText = computed(() => payload.value?.site.logo_text || '随')

function clearLocal() {
  clearLocalPreferences()
  cleared.value = true
  window.setTimeout(() => {
    cleared.value = false
  }, 2200)
}
</script>

<template>
  <footer class="site-footer">
    <div class="container">
      <section class="footer-cta">
        <div>
          <p class="mono-label">NO LOGIN · NO ADS · NO WATERMARK</p>
          <h2 class="serif">常用的小工具，<br />不该这么难找。</h2>
          <p class="cta-lead">图片、PDF、文字、编码、二维码。处理位置逐工具可见，文件不会被用来做别的事。</p>
        </div>
        <div class="popular">
          <p class="mono-label">常用工具</p>
          <div class="popular-list">
            <RouterLink v-for="tool in popular" :key="tool.code" :to="`/t/${tool.slug}`">
              {{ tool.name }}
              <span class="mono-label">{{ tool.code }}</span>
            </RouterLink>
            <RouterLink to="/#catalog" class="all-tools">全部 {{ payload?.site.online_tools ?? '' }} 个已上线工具</RouterLink>
          </div>
        </div>
      </section>

      <div class="footer-grid">
        <div class="footer-brand">
          <div class="mini-brand">
            <span class="brand-mark serif">{{ logoText }}</span>
            <strong class="serif">{{ siteName }}</strong>
          </div>
          <p>访客免登录，无广告，无注册。前端工具的内容留在浏览器；服务端处理的文件仅维护者可访问。</p>
          <p class="mono-label trust-line">NO TRACKING · NO ADS · NO REGISTRATION</p>
        </div>

        <div class="footer-column">
          <p class="column-title">站点</p>
          <RouterLink v-if="payload?.site.privacy_links_enabled" to="/privacy">处理与隐私</RouterLink>
          <RouterLink v-if="payload?.site.feedback_enabled" to="/feedback">问题反馈</RouterLink>
          <button type="button" class="clear-button" @click="clearLocal">
            {{ cleared ? '已清除本机数据' : '清除本机数据' }}
          </button>
        </div>

        <div class="footer-column">
          <p class="column-title">当前状态</p>
          <span class="status-line">
            <span class="dot" :class="payload?.site.server_available ? 'up' : 'warn'"></span>
            {{ payload?.site.server_available === false ? '服务端任务暂不可用，前端工具正常' : '站点与服务正常' }}
          </span>
        </div>

        <div class="footer-column">
          <p class="column-title">导航</p>
          <RouterLink to="/#catalog">全部工具</RouterLink>
          <RouterLink to="/admin/login" class="admin-entry">管理</RouterLink>
        </div>
      </div>

      <div class="footer-bottom">
        <span>© {{ new Date().getFullYear() }} {{ siteName }} · 个人自用与小范围分享</span>
        <span class="mono-label">PAGE / {{ payload?.site.total_tools ?? 39 }} TOOLS</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  margin-top: 72px;
  border-top: 1px solid var(--line-strong);
  background: var(--forest);
  color: #d8d3c5;
}

.footer-cta {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 40px;
  padding: 56px 0 44px;
  border-bottom: 1px solid rgba(217, 211, 196, 0.16);
}

.footer-cta .mono-label {
  color: #8f978a;
}

.footer-cta h2 {
  margin: 14px 0 14px;
  color: #f4f1e8;
  font-size: clamp(30px, 4vw, 46px);
  font-weight: 500;
  line-height: 1.22;
  letter-spacing: -0.01em;
}

.cta-lead {
  max-width: 460px;
  color: #a7ac9f;
  font-size: 13px;
  line-height: 1.7;
}

.popular {
  width: min(100%, 360px);
  flex: none;
}

.popular > .mono-label {
  margin-bottom: 14px;
  color: #8f978a;
}

.popular-list {
  display: flex;
  flex-direction: column;
}

.popular-list a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(217, 211, 196, 0.14);
  color: #e9e4d8;
  font-size: 13px;
  transition: color 0.2s;
}

.popular-list a:hover {
  color: #fff;
}

.popular-list .mono-label {
  color: #7f887c;
  font-size: 9px;
}

.popular-list .all-tools {
  margin-top: 12px;
  color: var(--accent);
  font-size: 12px;
  border-bottom: 0;
  padding-bottom: 0;
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr 1fr 1fr;
  gap: 36px;
  padding: 38px 0 34px;
}

.footer-brand p {
  max-width: 380px;
  margin-top: 12px;
  color: #a7ac9f;
  font-size: 12.5px;
  line-height: 1.75;
}

.mini-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #f4f1e8;
}

.mini-brand .brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(244, 241, 232, 0.25);
  border-radius: 3px;
  font-size: 17px;
}

.trust-line {
  color: #7f887c !important;
  font-size: 9px !important;
}

.footer-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  color: #a7ac9f;
  font-size: 12.5px;
}

.column-title {
  margin-bottom: 4px;
  color: #f4f1e8;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.footer-column a:hover,
.clear-button:hover {
  color: #f4f1e8;
}

.clear-button {
  padding: 0;
  border: 0;
  background: none;
  color: #a7ac9f;
  font-size: 12.5px;
  text-decoration: underline;
  text-underline-offset: 3px;
  text-decoration-color: rgba(167, 172, 159, 0.4);
}

.status-line {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--warn);
}

.dot.up {
  background: #5eae8b;
}

.admin-entry {
  margin-top: 8px;
  color: #6f786d;
  font-size: 10px;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 0 26px;
  border-top: 1px solid rgba(217, 211, 196, 0.16);
  color: #7f887c;
  font-size: 10.5px;
}

@media (max-width: 900px) {
  .footer-cta {
    flex-direction: column;
    align-items: flex-start;
  }

  .popular {
    width: 100%;
  }

  .footer-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 560px) {
  .footer-grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .footer-bottom {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
