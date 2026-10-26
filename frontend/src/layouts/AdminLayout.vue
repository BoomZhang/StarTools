<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { adminLogout, fetchAdminMe, fetchFeedbackList } from '@/api/admin'
import { useSite } from '@/composables/useSite'

const route = useRoute()
const router = useRouter()
const { payload, load: loadSite } = useSite()
const username = ref('')
const pending = ref(0)
const menuOpen = ref(false)

const navigation = [
  { name: 'admin-overview', label: '概览', icon: 'chart' },
  { name: 'admin-settings', label: '站点设置', icon: 'sliders' },
  { name: 'admin-tools', label: '工具配置', icon: 'monitor' },
  { name: 'admin-usage', label: '使用记录', icon: 'database' },
  { name: 'admin-feedback', label: '问题反馈', icon: 'message' },
  { name: 'admin-raw', label: '原始数据', icon: 'folder' },
  { name: 'admin-audit', label: '操作记录', icon: 'shield' },
]

const pageTitle = computed(() => String(route.meta.title || '管理台'))

watch(
  [payload, pageTitle],
  ([value, title]) => {
    const brand = value?.site.name || '随手工具箱'
    document.title = `${title} · ${brand}`
  },
  { immediate: true },
)

onMounted(async () => {
  if (!payload.value) void loadSite()
  try {
    const me = await fetchAdminMe()
    username.value = me.username
    const feedback = await fetchFeedbackList({ status: 'pending', days: 90, page: 1 })
    pending.value = feedback.total
  } catch {
    // 路由守卫会处理登录失效
  }
})

async function logout() {
  try {
    await adminLogout()
  } finally {
    await router.push({ name: 'admin-login' })
  }
}

function navigate() {
  menuOpen.value = false
}
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar" :class="{ 'is-open': menuOpen }">
      <div class="admin-brand">
        <span class="brand-mark serif">{{ payload?.site.logo_text || '随' }}</span>
        <div>
          <strong class="serif">{{ payload?.site.name || '随手工具箱' }}</strong>
          <span class="mono-label">ADMIN / 管理台</span>
        </div>
      </div>

      <nav class="admin-nav" aria-label="管理台导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          :to="{ name: item.name }"
          class="admin-nav-item"
          @click="navigate"
        >
          <AppIcon :name="item.icon" :size="16" />
          <span>{{ item.label }}</span>
          <span v-if="item.name === 'admin-feedback' && pending" class="nav-badge">{{ pending }}</span>
        </RouterLink>
      </nav>

      <div class="admin-sidebar-foot">
        <RouterLink to="/" class="back-site">
          <AppIcon name="external" :size="13" />
          返回访客站点
        </RouterLink>
        <span class="mono-label">v0.4 · SINGLE ACCOUNT</span>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-topbar">
        <div class="topbar-left">
          <button class="menu-button" type="button" aria-label="打开导航" @click="menuOpen = !menuOpen">
            <AppIcon :name="menuOpen ? 'x' : 'menu'" :size="18" />
          </button>
          <div>
            <span class="mono-label">STARTOOLS / ADMIN</span>
            <h1 class="serif">{{ pageTitle }}</h1>
          </div>
        </div>
        <div class="topbar-actions">
          <span class="admin-user">
            <AppIcon name="lock" :size="12" />
            {{ username || '维护者' }}
          </span>
          <button class="button button-ghost button-sm" type="button" @click="logout">
            <AppIcon name="logout" :size="13" />
            退出
          </button>
        </div>
      </header>

      <main class="admin-content">
        <RouterView />
      </main>
    </div>

    <div v-if="menuOpen" class="sidebar-backdrop" @click="menuOpen = false"></div>
  </div>
</template>

<style scoped>
.admin-shell {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  min-height: 100vh;
  background: var(--paper-deep);
}

.admin-sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 22px 16px;
  background: var(--forest);
  color: #cfd3c8;
  z-index: 40;
}

.admin-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 6px 22px;
  border-bottom: 1px solid rgba(217, 211, 196, 0.14);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border: 1px solid rgba(244, 241, 232, 0.25);
  border-radius: 3px;
  color: #f4f1e8;
  font-size: 18px;
}

.admin-brand strong {
  display: block;
  color: #f4f1e8;
  font-size: 15px;
  font-weight: 600;
}

.admin-brand .mono-label {
  display: block;
  margin-top: 2px;
  color: #7f887c;
  font-size: 7.5px;
}

.admin-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 18px;
}

.admin-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 10px;
  border-radius: 7px;
  color: #a7ac9f;
  font-size: 12.5px;
  transition: background-color 0.2s, color 0.2s;
}

.admin-nav-item:hover {
  background: rgba(244, 241, 232, 0.06);
  color: #e9e4d8;
}

.admin-nav-item.router-link-active {
  background: rgba(244, 241, 232, 0.1);
  color: #f4f1e8;
}

.nav-badge {
  margin-left: auto;
  min-width: 18px;
  padding: 1px 5px;
  border-radius: 999px;
  background: var(--accent);
  color: #fff6f2;
  font-family: var(--font-mono);
  font-size: 9px;
  text-align: center;
}

.admin-sidebar-foot {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
  padding: 16px 6px 0;
  border-top: 1px solid rgba(217, 211, 196, 0.14);
}

.back-site {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #a7ac9f;
  font-size: 11px;
}

.back-site:hover {
  color: #f4f1e8;
}

.admin-sidebar-foot .mono-label {
  color: #6f786d;
  font-size: 7px;
}

.admin-main {
  min-width: 0;
}

.admin-topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 76px;
  padding: 0 28px;
  border-bottom: 1px solid var(--line);
  background: rgba(244, 241, 232, 0.94);
  backdrop-filter: blur(14px);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.topbar-left .mono-label {
  display: block;
  color: var(--faint);
  font-size: 7.5px;
}

.topbar-left h1 {
  margin-top: 2px;
  font-size: 21px;
  font-weight: 600;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-user {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 11.5px;
}

.menu-button {
  display: none;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
}

.admin-content {
  padding: 24px 28px 40px;
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 900px) {
  .admin-shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .admin-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: 240px;
    transform: translateX(-100%);
    transition: transform 0.25s var(--ease-out);
  }

  .admin-sidebar.is-open {
    transform: translateX(0);
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 35;
    background: rgba(12, 20, 16, 0.4);
  }

  .menu-button {
    display: inline-flex;
  }

  .admin-topbar {
    padding: 0 16px;
  }

  .admin-content {
    padding: 18px 16px 32px;
  }

  .admin-user {
    display: none;
  }
}
</style>
