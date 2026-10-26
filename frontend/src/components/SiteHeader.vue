<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { useSite } from '@/composables/useSite'

const { payload, error } = useSite()
const open = ref(false)

const statusText = computed(() => {
  if (error.value) return '服务连接异常'
  if (!payload.value) return '正在读取配置'
  return payload.value.site.server_available ? '站点正常' : '服务端任务暂不可用'
})

const statusClass = computed(() => {
  if (error.value) return 'down'
  if (!payload.value) return 'loading'
  return payload.value.site.server_available ? 'up' : 'warn'
})

function closeMenu() {
  open.value = false
}
</script>

<template>
  <header class="site-header">
    <div class="container header-inner">
      <RouterLink to="/" class="brand" @click="closeMenu">
        <span class="brand-mark serif">{{ payload?.site.logo_text || '随' }}</span>
        <span class="brand-text">
          <strong class="serif">{{ payload?.site.name || '随手工具箱' }}</strong>
          <small class="mono-label">EVERYDAY UTILITIES</small>
        </span>
      </RouterLink>

      <nav class="site-nav" :class="{ 'is-open': open }" aria-label="主导航">
        <RouterLink to="/#catalog" @click="closeMenu">工具目录</RouterLink>
        <RouterLink v-if="payload?.site.privacy_links_enabled" to="/privacy" @click="closeMenu">处理与隐私</RouterLink>
        <RouterLink v-if="payload?.site.feedback_enabled" to="/feedback" @click="closeMenu">问题反馈</RouterLink>
        <span class="mobile-admin">
          <RouterLink to="/admin/login" @click="closeMenu">管理台</RouterLink>
        </span>
      </nav>

      <div class="header-actions">
        <span class="status-pill" :data-state="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
        <button class="menu-button" type="button" aria-label="打开菜单" :aria-expanded="open" @click="open = !open">
          <AppIcon :name="open ? 'x' : 'menu'" :size="20" />
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(244, 241, 232, 0.94);
  border-bottom: 1px solid rgba(193, 186, 168, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  min-height: var(--header-h);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 4px;
  border: 1px solid var(--forest-3);
  background: var(--forest);
  color: var(--paper);
  font-size: 22px;
  line-height: 1;
  box-shadow: inset 0 0 0 3px rgba(244, 241, 232, 0.1);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.brand-text strong {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.brand-text small {
  color: var(--faint);
  font-size: 8px;
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 26px;
  font-size: 13px;
  color: var(--muted);
}

.site-nav a {
  position: relative;
  padding: 6px 0;
  transition: color 0.2s;
}

.site-nav a:hover,
.site-nav a.router-link-active {
  color: var(--ink);
}

.site-nav a.router-link-active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: var(--ink);
}

.mobile-admin {
  display: none;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 11.5px;
  white-space: nowrap;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--faint);
}

.status-pill[data-state='up'] .dot {
  background: var(--success);
  box-shadow: 0 0 0 3px rgba(30, 106, 80, 0.12);
}

.status-pill[data-state='warn'] .dot {
  background: var(--warn);
  box-shadow: 0 0 0 3px rgba(143, 98, 27, 0.12);
}

.status-pill[data-state='down'] .dot {
  background: var(--danger);
  box-shadow: 0 0 0 3px rgba(165, 59, 42, 0.12);
}

.status-pill[data-state='loading'] .dot {
  background: var(--warn);
  animation: blink 1.2s ease-in-out infinite;
}

@keyframes blink {
  50% {
    opacity: 0.3;
  }
}

.menu-button {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: transparent;
}

@media (max-width: 900px) {
  .site-nav {
    position: absolute;
    top: var(--header-h);
    left: 0;
    right: 0;
    display: none;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 12px 20px 20px;
    background: var(--paper);
    border-bottom: 1px solid var(--line);
  }

  .site-nav.is-open {
    display: flex;
  }

  .site-nav a {
    display: block;
    width: 100%;
    padding: 12px 0;
    border-bottom: 1px solid rgba(217, 211, 196, 0.5);
    font-size: 14px;
  }

  .site-nav a.router-link-active::after {
    display: none;
  }

  .mobile-admin {
    display: block;
    width: 100%;
  }

  .menu-button {
    display: inline-flex;
  }
}

@media (max-width: 560px) {
  .status-pill {
    display: none;
  }

  .brand-text small {
    display: none;
  }

  .brand-text strong {
    font-size: 16px;
  }
}
</style>
