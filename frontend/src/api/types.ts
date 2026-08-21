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
  /** Username of the user who extracted this tag; null if unattributed. */
  username: string | null
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

export interface ExtractedImage {
  id: number
  original_filename: string
  tag_number: string
  batch_reference: string
  status: ItemStatus
  created_at: string
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

/** Dropdown options for the Search page — value is the key the backend expects. */
export const SEARCH_FIELDS: { value: string; label: string }[] = [
  { value: 'TAG NUMBER', label: 'TAG NUMBER' },
  { value: 'EQUIPMENT DESCRIPTION', label: 'EQUIPMENT DESCRIPTION' },
  { value: 'SIZE/DIMENSION', label: 'SIZE/DIMENSION' },
  { value: 'MAKE (ASSET)', label: 'MAKE (ASSET)' },
  { value: 'MODEL', label: 'MODEL' },
  { value: 'SERIAL NO', label: 'SERIAL NO' },
  { value: 'PART NO', label: 'PART NO' },
  { value: 'COUNTRY', label: 'COUNTRY' },
]

export interface SearchResult extends AssetTag {
  batch_id: number | null
  batch_item_id: number | null
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

export interface ClaudeModelUsage {
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
}

export interface ClaudeUsageDaily {
  day: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
}

/** Claude usage/cost, sourced entirely from Anthropic's official Usage &
 * Cost Admin API. When `available` is false, treat `error` as the state —
 * the numeric/list fields are empty, not zero-as-data. */
export interface ClaudeUsageSummary {
  available: boolean
  error: string | null
  generated_at: string
  window_days: number
  configured_model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  total_cost_usd: number
  /** Pure USD -> INR display conversion of total_cost_usd — not data
   * Anthropic returns. Always render it labeled as a conversion. */
  total_cost_inr: number
  usd_to_inr_rate: number
  by_model: ClaudeModelUsage[]
  daily: ClaudeUsageDaily[]
  unavailable_metrics: string[]
  spend_warning_threshold_usd: number
  spend_warning_triggered: boolean
}

/** Estimated Organization Credits: total purchased minus Anthropic's own
 * reported usage, tracked in a ledger so the estimate survives Anthropic's
 * Cost API's ~31-day reporting window. A calculated estimate, never
 * Anthropic's own account balance — no such balance endpoint exists.
 * `estimated_balance_*` are null only when no credits have ever been recorded. */
export interface OrgCredits {
  total_purchased_usd: number
  tracked_usage_usd: number
  estimated_balance_usd: number | null
  estimated_balance_inr: number | null
  usd_to_inr_rate: number
  updated_at: string | null
  /** Set when today's latest Anthropic usage couldn't be fetched — the
   * estimate shown is still the last successfully tracked one. */
  usage_error: string | null
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
