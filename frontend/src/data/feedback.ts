export const FEEDBACK_TYPES = [
  { key: 'bug', label: '功能异常' },
  { key: 'wrong_result', label: '结果不正确' },
  { key: 'page', label: '页面或操作异常' },
  { key: 'copy', label: '文案或内容错误' },
  { key: 'tool_request', label: '希望增加其他工具' },
  { key: 'other', label: '其他' },
] as const

export const FEEDBACK_STATUSES = [
  { key: 'pending', label: '待处理' },
  { key: 'processing', label: '处理中' },
  { key: 'resolved', label: '已解决' },
  { key: 'ignored', label: '已忽略' },
] as const

export const FEEDBACK_STATUS_LABEL: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略',
}
