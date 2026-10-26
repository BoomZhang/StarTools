import { api, API_BASE_URL } from './client'

export interface AdminMe {
  username: string
}

export interface LoginResult {
  username: string
  expires_in: number
}

export async function adminLogin(username: string, password: string): Promise<LoginResult> {
  const { data } = await api.post<LoginResult>('/admin/login', { username, password })
  return data
}

export async function adminLogout(): Promise<void> {
  await api.post('/admin/logout')
}

export async function fetchAdminMe(): Promise<AdminMe> {
  const { data } = await api.get<AdminMe>('/admin/me')
  return data
}

export interface OverviewData {
  days: number
  metrics: {
    today: number
    total: number
    online_tools: number
    total_tools: number
    server_tasks: number
    server_ratio: number
    raw_bytes: number
    disk: { percent: number; free: number; total: number }
    pending_feedback: number
  }
  daily: { date: string; count: number }[]
  ranking: { code: string; name: string; count: number; ratio: number }[]
  engine_split: { server: number; local: number }
  tool_table: {
    code: string
    name: string
    category: string
    priority: string
    implemented: boolean
    total: number
    succeeded: number
    partial: number
    failed: number
    canceled: number
    last_used: string | null
    last_ip: string | null
  }[]
  feedback_counts: Record<string, number>
}

export async function fetchOverview(days: number): Promise<OverviewData> {
  const { data } = await api.get<OverviewData>('/admin/overview', { params: { days } })
  return data
}

export interface AdminTool {
  code: string
  name: string
  slug: string
  category: string
  category_name: string
  priority: string
  engine_type: 'dual' | 'server' | 'local'
  summary: string
  implemented: boolean
  accepts_files: boolean
  online: boolean
  server_enabled: boolean
  max_file_mb: number | null
  max_count: number
  hard_limit_mb: number
  fixed_count: boolean
  available: boolean
  unavailable_reason: string | null
  status: 'live' | 'offline' | 'unimplemented'
  updated_at: string | null
  updated_by: string | null
}

export interface AdminToolGroup {
  key: string
  name: string
  blurb: string
  tools: AdminTool[]
}

export async function fetchAdminTools(): Promise<AdminToolGroup[]> {
  const { data } = await api.get<{ groups: AdminToolGroup[] }>('/admin/tools')
  return data.groups
}

export interface ToolPatch {
  online?: boolean
  server_enabled?: boolean
  max_file_mb?: number
  max_count?: number
}

export async function updateAdminTool(code: string, patch: ToolPatch): Promise<AdminTool> {
  const { data } = await api.patch<{ tool: AdminTool }>(`/admin/tools/${code}`, patch)
  return data.tool
}

export interface UsageItem {
  id: number
  created_at: string
  tool_code: string
  tool_name: string
  result: string
  engine: string
  duration_ms: number
  ip: string
  file_count: number
  total_size: number
  error_code: string | null
  is_retry: boolean
}

export interface UsageResponse {
  total: number
  page: number
  pages: number
  items: UsageItem[]
}

export interface UsageQuery {
  days: number
  tool?: string
  result?: string
  engine?: string
  ip?: string
  page?: number
}

export async function fetchUsage(query: UsageQuery): Promise<UsageResponse> {
  const { data } = await api.get<UsageResponse>('/admin/usage', { params: query })
  return data
}

export interface FeedbackSummary {
  id: number
  number: string
  created_at: string
  updated_at: string
  type: string
  type_name: string
  tool_code: string | null
  tool_name: string | null
  description: string
  status: string
  status_name: string
  ip: string
}

export interface FeedbackEvent {
  id: number
  kind: 'status' | 'note'
  from_status: string | null
  to_status: string | null
  note: string | null
  actor: string
  created_at: string
}

export interface FeedbackDetail {
  id: number
  number: string
  created_at: string
  updated_at: string
  type: string
  type_name: string
  tool_code: string | null
  tool_name: string | null
  description: string
  expected: string | null
  contact: string | null
  context: Record<string, unknown>
  ip: string
  status: string
  status_name: string
  events: FeedbackEvent[]
}

export interface FeedbackListResponse {
  total: number
  page: number
  pages: number
  counts: Record<string, number>
  items: FeedbackSummary[]
}

export interface FeedbackQuery {
  status?: string
  type?: string
  tool?: string
  days?: number
  q?: string
  page?: number
}

export async function fetchFeedbackList(query: FeedbackQuery): Promise<FeedbackListResponse> {
  const { data } = await api.get<FeedbackListResponse>('/admin/feedback', { params: query })
  return data
}

export async function fetchFeedbackDetail(id: number): Promise<FeedbackDetail> {
  const { data } = await api.get<FeedbackDetail>(`/admin/feedback/${id}`)
  return data
}

export async function updateFeedbackStatus(id: number, status: string): Promise<FeedbackDetail> {
  const { data } = await api.patch<FeedbackDetail>(`/admin/feedback/${id}/status`, { status })
  return data
}

export async function addFeedbackNote(id: number, content: string): Promise<FeedbackDetail> {
  const { data } = await api.post<FeedbackDetail>(`/admin/feedback/${id}/notes`, { content })
  return data
}

export interface SiteSettings {
  site_name: string
  logo_text: string
  feedback_enabled: boolean
  privacy_links_enabled: boolean
  upload_consent_enabled: boolean
  show_engine_badge: boolean
}

export async function fetchAdminSettings(): Promise<SiteSettings> {
  const { data } = await api.get<SiteSettings>('/admin/settings')
  return data
}

export async function updateAdminSettings(patch: Partial<SiteSettings>): Promise<SiteSettings> {
  const { data } = await api.patch<SiteSettings>('/admin/settings', patch)
  return data
}

export async function toggleFeedback(enabled: boolean): Promise<SiteSettings> {
  const { data } = await api.patch<SiteSettings>('/admin/settings/feedback', { enabled })
  return data
}

export interface RawFileItem {
  id: string
  task_id: string
  tool_code: string
  tool_name: string
  filename: string
  content_type: string
  size: number
  ip: string
  created_at: string
  expires_at: string
}

export interface RawResponse {
  total: number
  page: number
  pages: number
  total_bytes: number
  items: RawFileItem[]
}

export interface RawQuery {
  days?: number
  tool?: string
  ip?: string
  page?: number
}

export async function fetchRawFiles(query: RawQuery): Promise<RawResponse> {
  const { data } = await api.get<RawResponse>('/admin/raw', { params: query })
  return data
}

export function rawPreviewUrl(id: string): string {
  return `${API_BASE_URL}/admin/raw/${id}/preview`
}

export function rawDownloadUrl(id: string): string {
  return `${API_BASE_URL}/admin/raw/${id}/download`
}

export async function deleteRawFile(id: string): Promise<void> {
  await api.delete(`/admin/raw/${id}`)
}

export interface AuditItem {
  id: number
  created_at: string
  actor: string
  action: string
  target: string
  detail: Record<string, unknown>
  ip: string
}

export interface AuditResponse {
  total: number
  page: number
  pages: number
  items: AuditItem[]
}

export async function fetchAudit(days: number, page: number): Promise<AuditResponse> {
  const { data } = await api.get<AuditResponse>('/admin/audit', { params: { days, page } })
  return data
}

export async function manualCleanup(): Promise<Record<string, number>> {
  const { data } = await api.post<{ counts: Record<string, number> }>('/admin/cleanup')
  return data.counts
}
