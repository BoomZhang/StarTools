<script setup lang="ts">
import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import ToolWorkbench from '@/components/ToolWorkbench.vue'
import { reportUsage } from '@/api/feedback'
import { useCopy } from '@/composables/useCopy'
import type { Tool } from '@/types'
import { passwordStrength, randomString, randomUuid } from '@/utils/tools'

const props = defineProps<{ tool: Tool }>()
const { copied, copy } = useCopy()

const mode = ref<'uuid' | 'string' | 'password'>('uuid')
const uuidCount = ref(1)
const stringLength = ref(32)
const passwordLength = ref(16)
const options = ref({ upper: true, lower: true, digits: true, symbols: false, excludeAmbiguous: false })
const results = ref<string[]>([])
const error = ref('')
const generated = ref(false)
const startedAt = ref(0)

const canGenerate = computed(() => {
  if (mode.value === 'uuid') return uuidCount.value >= 1 && uuidCount.value <= 100
  if (mode.value === 'string') {
    return (
      stringLength.value >= 1 &&
      stringLength.value <= 256 &&
      (options.value.upper || options.value.lower || options.value.digits || options.value.symbols)
    )
  }
  return (
    passwordLength.value >= 8 &&
    passwordLength.value <= 64 &&
    (options.value.upper || options.value.lower || options.value.digits || options.value.symbols)
  )
})

const strength = computed(() => (mode.value === 'password' && results.value[0] ? passwordStrength(results.value[0]) : null))

function generate() {
  error.value = ''
  results.value = []
  generated.value = true
  try {
    if (!canGenerate.value) {
      throw new Error(mode.value === 'uuid' ? 'UUID 数量需在 1–100 之间' : '请至少选择一种字符类型，并检查长度范围')
    }
    if (mode.value === 'uuid') {
      results.value = Array.from({ length: uuidCount.value }, () => randomUuid())
    } else {
      const length = mode.value === 'string' ? stringLength.value : passwordLength.value
      results.value = [randomString(length, options.value)]
    }
    if (!startedAt.value) startedAt.value = performance.now()
    void reportUsage({
      tool_code: props.tool.code,
      result: 'succeeded',
      duration_ms: Math.round(performance.now() - startedAt.value),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    void reportUsage({
      tool_code: props.tool.code,
      result: 'failed',
      duration_ms: Math.round(performance.now() - (startedAt.value || performance.now())),
      error_code: 'E1-400',
    })
  }
}

async function copyAll() {
  await copy(results.value.join('\n'))
}

function toggleOption(key: keyof typeof options.value) {
  options.value = { ...options.value, [key]: !options.value[key] }
}
</script>

<template>
  <ToolWorkbench>
    <section class="panel">
      <div class="panel-body">
        <div class="tool-section-head">
          <div class="title-group">
            <span class="mono-label">01 / TYPE</span>
            <h2>生成类型</h2>
          </div>
        </div>
        <div class="segmented" role="group" aria-label="生成类型">
          <button type="button" :class="{ 'is-active': mode === 'uuid' }" @click="mode = 'uuid'">UUID v4</button>
          <button type="button" :class="{ 'is-active': mode === 'string' }" @click="mode = 'string'">随机字符串</button>
          <button type="button" :class="{ 'is-active': mode === 'password' }" @click="mode = 'password'">密码</button>
        </div>

        <div class="field option-gap">
          <template v-if="mode === 'uuid'">
            <span class="field-label"><strong>生成数量</strong><span>1–100</span></span>
            <div class="input-row">
              <input v-model.number="uuidCount" class="input input-mono" type="number" min="1" max="100" aria-label="UUID 数量" />
              <button class="button button-soft" type="button" @click="uuidCount = 1">重置</button>
            </div>
          </template>

          <template v-else-if="mode === 'string'">
            <span class="field-label"><strong>长度</strong><span>1–256</span></span>
            <div class="range-row">
              <input v-model.number="stringLength" type="range" min="1" max="256" />
              <span class="range-value">{{ stringLength }}</span>
            </div>
          </template>

          <template v-else>
            <span class="field-label"><strong>长度</strong><span>8–64</span></span>
            <div class="range-row">
              <input v-model.number="passwordLength" type="range" min="8" max="64" />
              <span class="range-value">{{ passwordLength }}</span>
            </div>
          </template>
        </div>

        <div v-if="mode !== 'uuid'" class="option-detail option-gap">
          <div class="inline-options">
            <label class="checkbox"><input :checked="options.upper" type="checkbox" @change="toggleOption('upper')" /> 大写 A-Z</label>
            <label class="checkbox"><input :checked="options.lower" type="checkbox" @change="toggleOption('lower')" /> 小写 a-z</label>
            <label class="checkbox"><input :checked="options.digits" type="checkbox" @change="toggleOption('digits')" /> 数字 0-9</label>
            <label class="checkbox"><input :checked="options.symbols" type="checkbox" @change="toggleOption('symbols')" /> 符号</label>
            <label class="checkbox"><input :checked="options.excludeAmbiguous" type="checkbox" @change="toggleOption('excludeAmbiguous')" /> 排除易混淆 0O1lI</label>
          </div>
        </div>

        <div class="run-bar">
          <p class="run-note">使用浏览器安全随机源；生成结果只存在当前页面内存，不写入 URL 或本地存储。</p>
          <div class="run-actions">
            <button class="button button-ink" type="button" :disabled="!canGenerate" @click="generate">
              <AppIcon name="refresh" :size="15" />
              生成 {{ mode === 'uuid' ? 'UUID' : mode === 'string' ? '随机串' : '密码' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <template #result>
      <div class="local-result">
        <div class="local-result-head">
          <span class="mono-label">RESULT / 生成结果</span>
          <span v-if="error" class="badge badge-danger">失败</span>
          <span v-else-if="results.length" class="badge badge-local">完成</span>
          <span v-else class="badge badge-neutral">等待生成</span>
        </div>
        <div class="local-result-body">
          <div v-if="!generated" class="local-empty">
            <span class="local-empty-mark"><AppIcon name="sparkles" :size="21" /></span>
            <strong>等待生成</strong>
            <p>选择类型与参数后点击生成，结果会显示在这里。</p>
          </div>
          <div v-else-if="error" class="mini-alert danger" role="alert">
            <AppIcon name="alert" :size="14" />
            <span>{{ error }}</span>
          </div>
          <template v-else>
            <div v-if="strength" class="strength-line">
              <span>强度提示</span>
              <strong :class="strength.label">{{ strength.label }}</strong>
              <div class="strength-bars">
                <span v-for="index in 5" :key="index" :class="{ filled: index <= strength.score }"></span>
              </div>
            </div>
            <ul class="random-list">
              <li v-for="(value, index) in results" :key="index">
                <code>{{ value }}</code>
                <button type="button" class="mini-copy" aria-label="复制" @click="copy(value)">
                  <AppIcon name="copy" :size="12" />
                </button>
              </li>
            </ul>
            <div class="result-toolbar" style="margin-top: 12px">
              <button class="button button-ghost button-sm" type="button" @click="copyAll">
                <AppIcon name="copy" :size="13" />
                {{ copied ? '已复制' : results.length > 1 ? '复制全部' : '复制结果' }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </template>
  </ToolWorkbench>
</template>

<style scoped>
.option-gap {
  margin-top: 14px;
}

.strength-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: var(--faint);
  font-size: 10.5px;
}

.strength-line strong {
  font-size: 11px;
}

.strength-line strong.弱 {
  color: var(--danger);
}

.strength-line strong.中 {
  color: var(--warn);
}

.strength-line strong.强 {
  color: var(--success);
}

.strength-bars {
  display: flex;
  gap: 3px;
  margin-left: auto;
}

.strength-bars span {
  width: 14px;
  height: 4px;
  border-radius: 999px;
  background: var(--line);
}

.strength-bars span.filled {
  background: var(--ink-2);
}

.random-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 340px;
  overflow: auto;
}

.random-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--surface-2);
}

.random-list code {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--ink-2);
}

.mini-copy {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex: none;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--surface);
  color: var(--faint);
}

.mini-copy:hover {
  border-color: var(--ink-2);
  color: var(--ink);
}
</style>
