export type Role = 'admin' | 'user'
export type Quality = 'Confirmed' | 'Verify'
export type ItemStatus =
  | 'uploaded' | 'extracting' | 'processing' | 'completed' | 'failed' | 'duplicate'
export type BatchStatus = 'uploaded' | 'processing' | 'completed' | 'failed' | 'partial'

export interface User {
  id: number
  username: string
  email: string | null
  full_name: string | null
  role: Role
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface FieldValue {
  value: string
  quality: Quality
}

export interface ExtractionPayload {
  fields: Record<string, FieldValue>
  remarks: string
  photo_status: string
  qc_comment: string
}

export interface AssetTag {
  id: number
  tag_number: string
  description: string
  ai_payload: ExtractionPayload
  final_payload: ExtractionPayload
  revision: number
  has_ai_excel: boolean
  has_template_excel: boolean
  created_at: string
  updated_at: string
}

export interface TagImage {
  id: number
  original_filename: string
  media_type: string
  size_bytes: number
}

export interface BatchItem {
  id: number
  tag_number: string
  description: string
  status: ItemStatus
  error_message: string | null
  images: TagImage[]
  asset_tag: AssetTag | null
  is_duplicate: boolean
}

export interface Batch {
  id: number
  reference: string
  status: BatchStatus
  total_images: number
  total_tags: number
  created_at: string
  items: BatchItem[]
}

export interface RejectedFile {
  filename: string
  reason: string
}

export interface UploadResponse {
  batch: Batch
  rejected: RejectedFile[]
  duplicates: AssetTag[]
}

export interface HistoryRow {
  id: number
  date: string
  tag_number: string | null
  description: string | null
  action: string
  status: string
  username: string | null
  detail: string | null
  asset_tag_id: number | null
  can_download: boolean
  batch_id: number | null
  batch_item_id: number | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface UsageDaily {
  day: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
  calls: number
}

export interface UsageSummary {
  model: string
  total_calls: number
  successful_calls: number
  failed_calls: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  total_cost_usd: number
  credit_budget_usd: number
  remaining_usd: number
  percent_used: number
  avg_latency_ms: number
  input_price_per_mtok: number
  output_price_per_mtok: number
  daily: UsageDaily[]
}

export interface AdminStats {
  total_users: number
  active_users: number
  total_tags: number
  total_batches: number
  total_uploads: number
  total_downloads: number
}

/** Field order for the editable table — must match the backend's FIELDS. */
export const FIELD_ORDER: { key: string; label: string; multiline?: boolean }[] = [
  { key: 'tag_number', label: 'Tag Number' },
  { key: 'description', label: 'Equipment Description' },
  { key: 'size_dimension', label: 'Size / Dimension' },
  { key: 'make', label: 'Manufacturer / Make' },
  { key: 'model', label: 'Model' },
  { key: 'serial_no', label: 'Serial No.' },
  { key: 'part_no', label: 'Part No.' },
  { key: 'weight', label: 'Weight' },
  { key: 'country', label: 'Country' },
  { key: 'year_of_manufacture', label: 'Year of Manufacture' },
  { key: 'month_of_manufacture', label: 'Month of Manufacture' },
  { key: 'hazardous_classification', label: 'Hazardous Area Classification', multiline: true },
  { key: 'additional_information', label: 'Additional Information', multiline: true },
]

export const NOT_PRESENT = 'Not present on nameplate'
