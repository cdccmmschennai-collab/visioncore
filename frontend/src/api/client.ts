import { API_V1 } from '@/config'
import type { StagedFile } from '@/utils/upload'
import type {
  AdminStats, AssetTag, Batch, BatchItem, ClaudeUsageSummary, ExtractedImage, ExtractionPayload,
  HistoryRow, OrgCredits, Page, TokenResponse, UploadResponse, User,
} from './types'

const ACCESS_KEY = 'visioncore.access'
const REFRESH_KEY = 'visioncore.refresh'

export const tokenStore = {
  get access() { return localStorage.getItem(ACCESS_KEY) },
  get refresh() { return localStorage.getItem(REFRESH_KEY) },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Broadcast when a refresh fails, so AuthProvider can drop the session. */
export const AUTH_EXPIRED_EVENT = 'visioncore:auth-expired'

/** Broadcast on every API call, so the idle-logout timer counts it as activity. */
export const ACTIVITY_EVENT = 'visioncore:activity'

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    /* fall through to the status-based message */
  }
  if (response.status === 413) return 'Those files are too large to upload at once.'
  if (response.status >= 500) return 'The server ran into a problem. Try again in a moment.'
  return `Request failed (${response.status})`
}

let refreshInFlight: Promise<boolean> | null = null

/** Refresh once even if several requests hit 401 at the same time. */
async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight

  refreshInFlight = (async () => {
    const refresh = tokenStore.refresh
    if (!refresh) return false
    try {
      const response = await fetch(`${API_V1}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (!response.ok) return false
      const data: TokenResponse = await response.json()
      tokenStore.set(data.access_token, data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

interface RequestOptions {
  method?: string
  body?: unknown
  formData?: FormData
  raw?: boolean
  signal?: AbortSignal
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, formData, raw = false, signal } = options
  window.dispatchEvent(new Event(ACTIVITY_EVENT))

  const send = async (): Promise<Response> => {
    const headers: Record<string, string> = {}
    const access = tokenStore.access
    if (access) headers.Authorization = `Bearer ${access}`
    // Never set Content-Type for FormData — the browser must add the boundary.
    if (body !== undefined && !formData) headers['Content-Type'] = 'application/json'

    return fetch(`${API_V1}${path}`, {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    })
  }

  let response = await send()

  if (response.status === 401 && tokenStore.refresh) {
    if (await refreshAccessToken()) {
      response = await send()
    } else {
      tokenStore.clear()
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
      throw new ApiError(401, 'Your session has expired. Sign in again.')
    }
  }

  if (!response.ok) throw new ApiError(response.status, await readError(response))
  if (raw) return response as unknown as T
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

/** Read the filename the server set, so downloads keep their real name. */
function filenameFrom(response: Response, fallback: string): string {
  const header = response.headers.get('Content-Disposition') ?? ''
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utf8) return decodeURIComponent(utf8[1])
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain ? plain[1] : fallback
}

async function download(path: string, fallbackName: string): Promise<string> {
  const response = await request<Response>(path, { raw: true })
  const blob = await response.blob()
  const name = filenameFrom(response, fallbackName)

  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  // Revoke on the next tick; revoking synchronously cancels the download in Safari.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return name
}

/** Fetch an authenticated file as a blob: URL, for inline `<img>` preview. */
async function blobUrl(path: string): Promise<string> {
  const response = await request<Response>(path, { raw: true })
  return URL.createObjectURL(await response.blob())
}

export const api = {
  // ── auth ────────────────────────────────────────────────────────────────
  login: (username: string, password: string, remember_me: boolean) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: { username, password, remember_me },
    }),
  me: () => request<User>('/auth/me'),
  forgotPassword: (identifier: string) =>
    request<{ message: string }>('/auth/forgot-password', {
      method: 'POST',
      body: { identifier },
    }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ message: string }>('/auth/change-password', {
      method: 'POST',
      body: { current_password, new_password },
    }),

  // ── batches ─────────────────────────────────────────────────────────────
  upload: (staged: StagedFile[]) => {
    const form = new FormData()
    // `folders` is positionally parallel to `files`: empty string for a file
    // picked without a folder, or its immediate parent subfolder's name —
    // the server groups by that instead of re-parsing the filename.
    staged.forEach(({ file, folder }) => {
      form.append('files', file, file.name)
      form.append('folders', folder ?? '')
    })
    return request<UploadResponse>('/batches/upload', { method: 'POST', formData: form })
  },
  getBatch: (id: number, signal?: AbortSignal) =>
    request<Batch>(`/batches/${id}`, { signal }),
  listBatches: (limit = 20) => request<Batch[]>(`/batches?limit=${limit}`),
  listBatchesByStatus: (statusFilter: 'completed' | 'failed', page = 1, pageSize = 10) =>
    request<Page<Batch>>(
      `/batches/by-status?status=${statusFilter}&page=${page}&page_size=${pageSize}`,
    ),
  listExtractedImages: (page = 1, pageSize = 10) =>
    request<Page<ExtractedImage>>(`/batches/images/extracted?page=${page}&page_size=${pageSize}`),
  batchImageUrl: (batchId: number, imageId: number) =>
    blobUrl(`/batches/${batchId}/images/${imageId}`),
  retryItem: (batchId: number, itemId: number) =>
    request<BatchItem>(`/batches/${batchId}/items/${itemId}/retry`, { method: 'POST' }),

  // ── tags ────────────────────────────────────────────────────────────────
  listTags: (search = '', page = 1, pageSize = 25) =>
    request<Page<AssetTag>>(
      `/tags?search=${encodeURIComponent(search)}&page=${page}&page_size=${pageSize}`,
    ),
  getTag: (id: number) => request<AssetTag>(`/tags/${id}`),
  getTagByNumber: (tagNumber: string) =>
    request<AssetTag>(`/tags/by-number/${encodeURIComponent(tagNumber)}`),
  saveTag: (id: number, payload: ExtractionPayload) =>
    request<AssetTag>(`/tags/${id}`, { method: 'PUT', body: { payload } }),
  downloadAi: (tag: AssetTag) =>
    download(`/tags/${tag.id}/download/ai`,
      `AI Output-${tag.tag_number}-${tag.description}.xlsx`),
  downloadTemplate: (tag: AssetTag) =>
    download(`/tags/${tag.id}/download/template`,
      `${tag.tag_number}-${tag.description}-Template.xlsx`),
  downloadAllTemplates: () =>
    download('/tags/download-all/template', 'All-Tags-Template.xlsx'),

  // ── history ─────────────────────────────────────────────────────────────
  history: (params: {
    search?: string; action?: string; mineOnly?: boolean
    page?: number; pageSize?: number
  } = {}) => {
    const query = new URLSearchParams({
      search: params.search ?? '',
      action: params.action ?? '',
      mine_only: String(params.mineOnly ?? false),
      page: String(params.page ?? 1),
      page_size: String(params.pageSize ?? 25),
    })
    return request<Page<HistoryRow>>(`/history?${query}`)
  },

  // ── admin ───────────────────────────────────────────────────────────────
  listUsers: () => request<User[]>('/admin/users'),
  createUser: (body: {
    username: string; password: string; email?: string | null
    full_name?: string | null; role: 'admin' | 'user'
  }) => request<User>('/admin/users', { method: 'POST', body }),
  updateUser: (id: number, body: Partial<Pick<User, 'email' | 'full_name' | 'role' | 'is_active'>>) =>
    request<User>(`/admin/users/${id}`, { method: 'PATCH', body }),
  resetUserPassword: (id: number, new_password: string) =>
    request<{ message: string }>(`/admin/users/${id}/reset-password`, {
      method: 'POST',
      body: { new_password },
    }),
  deactivateUser: (id: number) =>
    request<{ message: string }>(`/admin/users/${id}`, { method: 'DELETE' }),
  usage: (days = 30) => request<ClaudeUsageSummary>(`/admin/usage?days=${days}`),
  orgCredits: () => request<OrgCredits>('/admin/org-credits'),
  setOrgCredits: (amount_usd: number) =>
    request<OrgCredits>('/admin/org-credits', { method: 'PATCH', body: { amount_usd } }),
  stats: () => request<AdminStats>('/admin/stats'),
}
