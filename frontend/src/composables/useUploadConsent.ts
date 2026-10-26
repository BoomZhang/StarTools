import { computed, ref } from 'vue'

import { useSite } from '@/composables/useSite'

const KEY = 'startools:upload-consent:v1'
const MAX_AGE = 180 * 24 * 60 * 60 * 1000

function read(): boolean {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return false
    const parsed = JSON.parse(raw) as { at?: number }
    return Boolean(parsed.at && Date.now() - parsed.at < MAX_AGE)
  } catch {
    return false
  }
}

const stored = ref(read())
const { payload } = useSite()
const required = computed(() => payload.value?.site.upload_consent_enabled !== false)
const accepted = computed(() => !required.value || stored.value)

export function useUploadConsent() {
  function accept(): void {
    stored.value = true
    try {
      localStorage.setItem(KEY, JSON.stringify({ at: Date.now() }))
    } catch {
      // 忽略存储异常
    }
  }

  function revoke(): void {
    stored.value = false
    try {
      localStorage.removeItem(KEY)
    } catch {
      // 忽略存储异常
    }
  }

  return { accepted, required, accept, revoke }
}

export function clearLocalPreferences(): void {
  stored.value = false
  try {
    localStorage.removeItem(KEY)
  } catch {
    // 忽略存储异常
  }
}
