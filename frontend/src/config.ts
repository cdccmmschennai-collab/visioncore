/**
 * Branding and client-side limits.
 * Change COMPANY_NAME here and it updates the header, login page and title.
 */
export const COMPANY_NAME = 'Visioncore'
export const APP_TITLE = 'NAMEPLATE DATA MIGRATION'
export const TAGLINE = 'Transform Nameplate Images into Structured Data with AI.'

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'
export const API_V1 = `${API_BASE}/v1`

/** Mirrors the backend's limits; the server enforces them regardless. */
export const LIMITS = {
  maxImagesPerBatch: 20,
  maxTagsPerBatch: 10,
  maxImagesPerTag: 5,
  maxImageSizeMb: 15,
  // Batch Process (browser-scanned local folder) covers far more tags than
  // a normal drag-drop batch — see backend MAX_TAGS_PER_BATCH_PROCESS.
  maxTagsPerBatchProcess: 50,
}

export const ACCEPTED_EXTENSIONS = ['.jpg', '.jpeg', '.jfif', '.png', '.webp', '.gif', '.bmp']
