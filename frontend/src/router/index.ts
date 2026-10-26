import { createRouter, createWebHistory } from 'vue-router'

import { api } from '@/api/client'
import { useSite } from '@/composables/useSite'

const { payload } = useSite()
let homeScroll = 0

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth', top: 92 }
    if (to.name === 'home' && from && from.name !== 'home' && homeScroll > 0) {
      return { top: homeScroll }
    }
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/PublicLayout.vue'),
      children: [
        { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '工具目录' } },
        { path: 't/:slug', name: 'tool', component: () => import('@/views/ToolView.vue'), meta: { title: '工具' } },
        { path: 'privacy', name: 'privacy', component: () => import('@/views/PrivacyView.vue'), meta: { title: '处理与隐私' } },
        { path: 'feedback', name: 'feedback', component: () => import('@/views/FeedbackView.vue'), meta: { title: '问题反馈' } },
        { path: ':pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue'), meta: { title: '页面不存在' } },
      ],
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/admin/LoginView.vue'),
      meta: { title: '管理台登录' },
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'admin-overview', component: () => import('@/views/admin/OverviewView.vue'), meta: { title: '概览', requiresAuth: true } },
        { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/SettingsView.vue'), meta: { title: '站点设置', requiresAuth: true } },
        { path: 'tools', name: 'admin-tools', component: () => import('@/views/admin/ToolsView.vue'), meta: { title: '工具配置', requiresAuth: true } },
        { path: 'usage', name: 'admin-usage', component: () => import('@/views/admin/UsageView.vue'), meta: { title: '使用记录', requiresAuth: true } },
        { path: 'feedback', name: 'admin-feedback', component: () => import('@/views/admin/FeedbackView.vue'), meta: { title: '问题反馈', requiresAuth: true } },
        { path: 'raw', name: 'admin-raw', component: () => import('@/views/admin/RawView.vue'), meta: { title: '原始数据', requiresAuth: true } },
        { path: 'audit', name: 'admin-audit', component: () => import('@/views/admin/AuditView.vue'), meta: { title: '操作记录', requiresAuth: true } },
      ],
    },
  ],
})

router.beforeEach(async (to, from) => {
  if (from.name === 'home' && to.name !== 'home') homeScroll = window.scrollY
  const brand = payload.value?.site.name || '随手工具箱'
  document.title = to.meta.title ? `${to.meta.title} · ${brand}` : brand
  if (!to.meta.requiresAuth) return true
  try {
    await api.get('/admin/me')
    return true
  } catch {
    return { name: 'admin-login', query: { redirect: to.fullPath } }
  }
})

router.afterEach((to) => {
  let robots = document.querySelector('meta[name="robots"]')
  if (to.path.startsWith('/admin')) {
    if (!robots) {
      robots = document.createElement('meta')
      robots.setAttribute('name', 'robots')
      document.head.appendChild(robots)
    }
    robots.setAttribute('content', 'noindex, nofollow')
  } else if (robots) {
    robots.remove()
  }
})

if (typeof window !== 'undefined' && 'scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual'
}

export default router
