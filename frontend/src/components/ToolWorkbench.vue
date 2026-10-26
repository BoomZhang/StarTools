<script setup lang="ts">
defineProps<{ title?: string; note?: string }>()
</script>

<template>
  <div class="workbench">
    <section class="workbench-main" :aria-label="title || '输入与参数'">
      <slot />
    </section>
    <aside class="workbench-side" aria-label="处理结果">
      <slot name="result" />
    </aside>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.42fr) minmax(0, 0.78fr);
  gap: 18px;
  align-items: start;
  margin-top: 18px;
}

.workbench-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.workbench-side {
  position: sticky;
  top: calc(var(--header-h) + 16px);
  min-width: 0;
}

@media (max-width: 980px) {
  .workbench {
    grid-template-columns: minmax(0, 1fr);
  }

  .workbench-side {
    position: static;
  }
}
</style>
