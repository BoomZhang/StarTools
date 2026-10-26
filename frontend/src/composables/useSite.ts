import { ref } from 'vue'

import { fetchSite } from '@/api/site'
import { parseApiError } from '@/api/client'
import type { SitePayload, Tool } from '@/types'

const payload = ref<SitePayload | null>(null)
const loading = ref(false)
const error = ref('')
let inFlight: Promise<void> | null = null

async function load(force = false): Promise<void> {
  if (!force && payload.value) return
  if (inFlight) return inFlight
  loading.value = true
  error.value = ''
  inFlight = fetchSite()
    .then((data) => {
      payload.value = data
    })
    .catch((err) => {
      error.value = parseApiError(err).message
    })
    .finally(() => {
      loading.value = false
      inFlight = null
    })
  return inFlight
}

// 管理台配置变更后最多 10 秒同步到访客页面；页面隐藏时暂停请求
if (typeof window !== 'undefined') {
  window.setInterval(() => {
    if (document.visibilityState === 'visible' && payload.value && !inFlight) void load(true)
  }, 10000)
}

export function useSite() {
  function toolBySlug(slug: string): Tool | undefined {
    return payload.value?.tools.find((tool) => tool.slug === slug)
  }

  return { payload, loading, error, load, toolBySlug }
}
