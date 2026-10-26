<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { parseApiError } from '@/api/client'
import { adminLogin } from '@/api/admin'
import { useSite } from '@/composables/useSite'

const router = useRouter()
const route = useRoute()
const { payload, load: loadSite } = useSite()

void loadSite()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const error = ref('')

async function submit() {
  if (submitting.value) return
  error.value = ''
  submitting.value = true
  try {
    await adminLogin(username.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/admin'
    await router.replace(redirect)
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <aside class="login-aside">
      <div class="aside-brand">
        <span class="brand-mark serif">{{ payload?.site.logo_text || '随' }}</span>
        <div>
          <strong class="serif">{{ payload?.site.name || '随手工具箱' }}</strong>
          <span class="mono-label">ADMIN / MAINTAINER</span>
        </div>
      </div>
      <div class="aside-copy">
        <p class="mono-label">SINGLE MAINTAINER · NO PUBLIC SIGNUP</p>
        <h1 class="serif">工具背后，<br />也需要一把钥匙。</h1>
        <p>
          管理台用于工具上线、处理引擎、文件限额、使用记录、原始数据与问题反馈。
          所有管理操作都会写入操作记录，保留 90 天。
        </p>
      </div>
      <div class="aside-foot">
        <span><AppIcon name="lock" :size="14" /> 8 小时无操作自动退出</span>
        <span><AppIcon name="shield" :size="14" /> 连续失败 5 次锁定 10 分钟</span>
      </div>
    </aside>

    <main class="login-main">
      <div class="login-card">
        <p class="eyebrow">ADMIN LOGIN</p>
        <h2 class="serif">维护者登录</h2>
        <p class="login-lead">账号在部署时配置，不提供公开注册、邀请或找回密码。</p>

        <form class="login-form" @submit.prevent="submit">
          <div class="field">
            <span class="field-label"><strong>账号</strong></span>
            <input
              v-model="username"
              class="input"
              type="text"
              autocomplete="username"
              placeholder="维护者账号"
              required
            />
          </div>
          <div class="field">
            <span class="field-label"><strong>密码</strong></span>
            <div class="password-field">
              <input
                v-model="password"
                class="input"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="密码"
                required
              />
              <button
                class="reveal"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <AppIcon :name="showPassword ? 'eye' : 'lock'" :size="15" />
              </button>
            </div>
          </div>

          <div v-if="error" class="alert alert-danger" role="alert">
            <AppIcon name="alert" :size="15" />
            <span>{{ error }}</span>
          </div>

          <button class="button button-ink button-block" type="submit" :disabled="submitting || !username || !password">
            <AppIcon name="lock" :size="15" />
            {{ submitting ? '正在登录…' : '登录管理台' }}
          </button>
        </form>

        <p class="login-note">
          密码遗失需通过部署配置或维护命令重置，不通过网页自助找回。
          <RouterLink to="/" class="inline-link">返回访客站点</RouterLink>
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  min-height: 100vh;
  background: var(--paper);
}

.login-aside {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 40px 46px;
  background:
    radial-gradient(600px 420px at 10% 90%, rgba(222, 78, 39, 0.16), transparent 60%),
    var(--forest);
  color: #d8d3c5;
}

.aside-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(244, 241, 232, 0.25);
  border-radius: 3px;
  color: #f4f1e8;
  font-size: 20px;
}

.aside-brand strong {
  display: block;
  color: #f4f1e8;
  font-size: 16px;
}

.aside-brand .mono-label {
  display: block;
  margin-top: 2px;
  color: #7f887c;
  font-size: 7.5px;
}

.aside-copy {
  max-width: 430px;
  padding: 40px 0;
}

.aside-copy .mono-label {
  color: #7f887c;
  font-size: 8.5px;
}

.aside-copy h1 {
  margin: 20px 0 20px;
  color: #f4f1e8;
  font-size: clamp(34px, 4vw, 52px);
  font-weight: 500;
  line-height: 1.25;
}

.aside-copy p:not(.mono-label) {
  color: #a7ac9f;
  font-size: 13px;
  line-height: 1.85;
}

.aside-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(217, 211, 196, 0.14);
}

.aside-foot span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #7f887c;
  font-size: 10px;
}

.login-main {
  display: grid;
  place-items: center;
  padding: 40px;
}

.login-card {
  width: min(100%, 420px);
}

.login-card h2 {
  margin: 14px 0 8px;
  font-size: 36px;
  font-weight: 500;
}

.login-lead {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 26px;
}

.password-field {
  position: relative;
}

.password-field .input {
  padding-right: 44px;
}

.reveal {
  position: absolute;
  top: 50%;
  right: 8px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--faint);
  transform: translateY(-50%);
}

.reveal:hover {
  background: var(--surface-2);
  color: var(--ink);
}

.login-note {
  margin-top: 22px;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.75;
}

@media (max-width: 860px) {
  .login-page {
    grid-template-columns: minmax(0, 1fr);
  }

  .login-aside {
    padding: 26px 24px;
    gap: 20px;
  }

  .aside-copy {
    padding: 16px 0;
  }

  .aside-copy h1 {
    font-size: 34px;
    margin: 12px 0;
  }

  .aside-copy p:not(.mono-label),
  .aside-foot {
    display: none;
  }

  .login-main {
    padding: 30px 22px 50px;
    place-items: start center;
  }
}
</style>
