import { ref } from 'vue'

import { copyText } from '@/utils/files'

export function useCopy() {
  const copied = ref(false)
  let timer: number | undefined

  async function copy(value: string): Promise<boolean> {
    const ok = await copyText(value)
    if (ok) {
      copied.value = true
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        copied.value = false
      }, 1600)
    }
    return ok
  }

  return { copied, copy }
}
