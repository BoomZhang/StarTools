<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{ engine: 'server' | 'local' }>()
const label = computed(() => (props.engine === 'server' ? '服务端' : '前端'))
</script>

<template>
  <span class="badge" :class="engine === 'server' ? 'badge-server' : 'badge-local'">
    <AppIcon :name="engine === 'server' ? 'server' : 'monitor'" :size="12" />
    {{ label }}
  </span>
</template>
