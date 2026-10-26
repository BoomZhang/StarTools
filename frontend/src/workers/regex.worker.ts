const context = self as unknown as {
  onmessage: ((event: MessageEvent<RegexRequest>) => void) | null
  postMessage: (message: unknown) => void
}

interface RegexRequest {
  pattern: string
  flags: string
  text: string
  replacement: string
}

context.onmessage = (event: MessageEvent<RegexRequest>) => {
  const { pattern, flags, text, replacement } = event.data
  try {
    const matchFlags = flags.includes('g') ? flags : `${flags}g`
    const matcher = new RegExp(pattern, matchFlags)
    const matches: { value: string; index: number; groups: string[] }[] = []
    let match: RegExpExecArray | null
    while ((match = matcher.exec(text)) !== null && matches.length < 500) {
      matches.push({ value: match[0], index: match.index, groups: match.slice(1).map((group) => group ?? '') })
      if (match[0] === '') matcher.lastIndex += 1
    }
    const replaced = text.replace(new RegExp(pattern, flags), replacement)
    context.postMessage({ ok: true, matches, replaced })
  } catch (error) {
    context.postMessage({ ok: false, error: error instanceof Error ? error.message : String(error) })
  }
}
