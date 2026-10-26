<script setup lang="ts">
import { computed } from 'vue'

import { useUploadConsent } from '@/composables/useUploadConsent'

const props = defineProps<{ fileCount: number }>()
const { accepted, required, accept, revoke } = useUploadConsent()

const countText = computed(() => (props.fileCount > 0 ? `将上传 ${props.fileCount} 个文件` : '将上传文件'))
</script>

<template>
  <div v-if="required && !accepted" class="consent">
    <div class="consent-main">
      <span class="consent-icon">↑</span>
      <p>
        {{ countText }}至服务器处理，仅维护者可访问，不用于分析或训练。
      </p>
    </div>
    <label class="checkbox">
      <input type="checkbox" @change="accept" />
      <span>我已了解文件会上传到服务器处理</span>
    </label>
  </div>
  <p v-else-if="required" class="consent-accepted">
    <span>已确认上传说明：文件会上传到服务器处理，仅维护者可访问。</span>
    <button type="button" class="text-button" @click="revoke">撤销确认</button>
  </p>
</template>

<style scoped>
.consent {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 13px 14px;
  border: 1px solid rgba(143, 98, 27, 0.25);
  border-radius: 10px;
  background: var(--warn-soft);
}

.consent-main {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.consent-icon {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  flex: none;
  border: 1px solid currentColor;
  border-radius: 50%;
  color: var(--warn);
  font-size: 10px;
  line-height: 1;
}

.consent p {
  color: #6e5320;
  font-size: 11.5px;
  line-height: 1.65;
}

.consent .checkbox {
  align-self: flex-start;
  color: #6e5320;
  font-size: 11.5px;
}

.consent-accepted {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--surface-2);
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.5;
}
</style>
