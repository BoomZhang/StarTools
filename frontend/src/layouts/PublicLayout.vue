<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import SiteFooter from '@/components/SiteFooter.vue'
import SiteHeader from '@/components/SiteHeader.vue'
import { useSite } from '@/composables/useSite'

const { payload, load } = useSite()
const route = useRoute()

watch(
  payload,
  (value) => {
    const brand = value?.site.name || '随手工具箱'
    document.title = route.meta.title ? `${route.meta.title} · ${brand}` : brand
  },
  { immediate: true },
)

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="public-layout">
    <a class="skip-link" href="#main-content">跳转到主要内容</a>
    <SiteHeader />
    <main id="main-content" class="public-main">
      <RouterView />
    </main>
    <SiteFooter />
  </div>
</template>

<style scoped>
.public-layout {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
}

.public-main {
  flex: 1;
}

.skip-link {
  position: fixed;
  top: 8px;
  left: 8px;
  z-index: 500;
  padding: 10px 16px;
  border-radius: 8px;
  background: var(--ink);
  color: var(--paper);
  font-size: 13px;
  transform: translateY(-140%);
  transition: transform 0.2s var(--ease-out);
}

.skip-link:focus {
  transform: translateY(0);
}
</style>
