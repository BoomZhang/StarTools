export type EngineType = 'dual' | 'server' | 'local'
export type Engine = 'server' | 'local'
export type Priority = 'P0' | 'P1'
export type CategoryKey = 'image' | 'document' | 'text' | 'encoding' | 'qr' | 'ocr' | 'av'

export interface Tool {
  code: string
  slug: string
  name: string
  category: CategoryKey
  category_name: string
  engine_type: EngineType
  engine: Engine
  priority: Priority
  summary: string
  formats: string
  pinyin: string
  aliases: string[]
  keywords: string[]
  default_max_file_mb: number | null
  default_max_count: number
  implemented: boolean
  accepts_files: boolean
  online: boolean
  server_enabled: boolean
  max_file_mb: number | null
  max_count: number
  available: boolean
  unavailable_reason: string | null
}

export interface Category {
  key: CategoryKey
  name: string
  order: number
  blurb: string
  total: number
}

export interface SiteInfo {
  name: string
  logo_text: string
  feedback_enabled: boolean
  privacy_links_enabled: boolean
  upload_consent_enabled: boolean
  show_engine_badge: boolean
  announcement: string
  total_tools: number
  online_tools: number
  server_available: boolean
  disk_percent: number
  retention: {
    raw_days: number
    result_minutes: number
    record_days: number
  }
  capabilities: {
    image_output_formats: string[]
    ocr_available: boolean
  }
}

export interface SitePayload {
  site: SiteInfo
  categories: Category[]
  tools: Tool[]
}

export interface CropRect {
  x: number
  y: number
  width: number
  height: number
}

export interface TaskResult {
  id: string
  filename: string
  size: number
  content_type: string
  kind: 'file' | 'text'
  text: string | null
  meta: Record<string, unknown>
  expires_at: string
  download_url: string
  preview_url?: string | null
}

export interface TaskFailure {
  filename: string
  code: string
  message: string
}

export interface ServerTask {
  task_id: string
  tool_code: string
  status: 'processing' | 'succeeded' | 'partial' | 'failed' | 'canceled' | 'expired'
  engine: 'server'
  file_count: number
  total_size: number
  duration_ms: number
  created_at: string
  expires_at: string | null
  error_code: string | null
  error_message: string | null
  notes: string[]
  failures: TaskFailure[]
  results: TaskResult[]
}

export interface FeedbackReceipt {
  number: string
  created_at: string
  message: string
}

export interface AdminUser {
  username: string
}
