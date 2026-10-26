<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import {
  fetchAdminSettings,
  updateAdminSettings,
  type SiteSettings,
} from '@/api/admin'
import { parseApiError } from '@/api/client'
import { useSite } from '@/composables/useSite'

const { load: loadSite } = useSite()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const message = ref('')
const original = ref<SiteSettings | null>(null)

const draft = reactive<SiteSettings>({
  site_name: '',
  logo_text: '',
  feedback_enabled: true,
  privacy_links_enabled: true,
  upload_consent_enabled: true,
  show_engine_badge: true,
})

const dirty = computed(() => {
  if (!original.value) return false
  return (Object.keys(draft) as (keyof SiteSettings)[]).some((key) => draft[key] !== original.value![key])
})

const toggles = [
  {
    key: 'show_engine_badge' as const,
    title: '显示处理位置徽章',
    description: '在工具卡片、工具页与结果区展示「前端处理 / 服务端处理」标识。',
  },
  {
    key: 'privacy_links_enabled' as const,
    title: '显示隐私说明入口',
    description: '在页头、页脚、工具页与首页展示「处理与隐私」链接。关闭后仅保留隐私页本身。',
  },
  {
    key: 'upload_consent_enabled' as const,
    title: '上传前确认',
    description: '服务端工具在首次上传前要求访客确认文件会发送到服务器，并展示确认提示。',
  },
  {
    key: 'feedback_enabled' as const,
    title: '开放问题反馈',
    description: '展示页脚、工具失败区与隐私页的反馈入口；已有反馈仍可在管理台查看。',
  },
]

onMounted(() => {
  void load()
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchAdminSettings()
    Object.assign(draft, data)
    original.value = { ...data }
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value) return
  const name = draft.site_name.trim()
  const logo = draft.logo_text.trim()
  if (!name || name.length > 30) {
    error.value = '网站名称需为 1–30 个字符'
    return
  }
  if (!logo || logo.length > 2) {
    error.value = 'Logo 文字需为 1–2 个字符'
    return
  }
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    const updated = await updateAdminSettings({
      site_name: name,
      logo_text: logo,
      feedback_enabled: draft.feedback_enabled,
      privacy_links_enabled: draft.privacy_links_enabled,
      upload_consent_enabled: draft.upload_consent_enabled,
      show_engine_badge: draft.show_engine_badge,
    })
    Object.assign(draft, updated)
    original.value = { ...updated }
    message.value = '站点设置已保存，访客页面会在 10 秒内同步。'
    await loadSite(true)
  } catch (err) {
    error.value = parseApiError(err).message
  } finally {
    saving.value = false
  }
}

function reset() {
  if (!original.value) return
  Object.assign(draft, original.value)
  error.value = ''
  message.value = ''
}
</script>

<template>
  <div class="settings-admin">
    <div class="page-toolbar">
      <div>
        <p class="mono-label">SITE / SETTINGS</p>
        <h2 class="serif">站点外观与模块开关。</h2>
        <p class="toolbar-note">
          名称与 Logo 会同步到页头、页脚、管理台与浏览器标题；模块开关立即影响访客页面。
        </p>
      </div>
      <button class="button button-ghost button-sm" type="button" :disabled="loading" @click="load">
        <AppIcon name="refresh" :size="13" />
        重新读取
      </button>
    </div>

    <div v-if="error" class="alert alert-danger">
      <AppIcon name="alert" :size="15" />
      <span>{{ error }}</span>
    </div>
    <div v-if="message" class="alert alert-info">
      <AppIcon name="check-circle" :size="15" />
      <span>{{ message }}</span>
    </div>

    <section class="panel settings-panel">
      <header class="panel-head">
        <div>
          <p class="mono-label">BRAND</p>
          <h3 class="serif">品牌</h3>
        </div>
        <span class="mono-label">HEADER · FOOTER · ADMIN</span>
      </header>
      <div class="panel-body">
        <div class="brand-preview">
          <span class="preview-mark serif">{{ draft.logo_text || '随' }}</span>
          <div>
            <strong class="serif">{{ draft.site_name || '随手工具箱' }}</strong>
            <span class="mono-label">EVERYDAY UTILITIES</span>
          </div>
        </div>

        <div class="settings-grid">
          <label class="field">
            <span class="field-label"><strong>网站名称</strong><span>1–30 个字符</span></span>
            <input v-model="draft.site_name" class="input" maxlength="30" placeholder="随手工具箱" />
          </label>
          <label class="field">
            <span class="field-label"><strong>Logo 文字</strong><span>1–2 个字符</span></span>
            <input v-model="draft.logo_text" class="input" maxlength="2" placeholder="随" />
          </label>
        </div>
      </div>
    </section>

    <section class="panel settings-panel">
      <header class="panel-head">
        <div>
          <p class="mono-label">MODULES</p>
          <h3 class="serif">展示模块</h3>
        </div>
        <span class="mono-label">VISITOR PAGES</span>
      </header>
      <div class="panel-body toggle-list">
        <div v-for="item in toggles" :key="item.key" class="toggle-row">
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
          </div>
          <label class="switch">
            <input v-model="draft[item.key]" type="checkbox" />
            <span></span>
          </label>
        </div>
      </div>
    </section>

    <div class="settings-actions">
      <button class="button button-ghost button-sm" type="button" :disabled="!dirty || saving" @click="reset">
        放弃修改
      </button>
      <button class="button button-ink" type="button" :disabled="!dirty || saving" @click="save">
        <AppIcon name="check" :size="14" />
        {{ saving ? '保存中…' : '保存设置' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.settings-panel {
  margin-top: 18px;
}

.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
}

.panel-head h3 {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 600;
}

.panel-head .mono-label {
  color: var(--faint);
  font-size: 9px;
}

.brand-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
  background: var(--surface-2);
}

.preview-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 4px;
  background: var(--forest);
  color: var(--paper);
  font-size: 22px;
}

.brand-preview div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-preview strong {
  font-size: 18px;
  font-weight: 600;
}

.brand-preview .mono-label {
  color: var(--faint);
  font-size: 8px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.toggle-list {
  display: flex;
  flex-direction: column;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 16px 0;
  border-bottom: 1px solid var(--line);
}

.toggle-row:last-child {
  border-bottom: 0;
}

.toggle-row strong {
  font-size: 13.5px;
}

.toggle-row p {
  max-width: 620px;
  margin-top: 4px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

@media (max-width: 720px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .toggle-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
}
</style>
