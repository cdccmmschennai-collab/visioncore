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
  maxTagsPerBatchProcess: 200,
  // A Batch Process run is uploaded as several sequential requests, each
  // capped at whichever of these two limits it hits first (never splitting
  // one tag's own photos across two requests) — see chunkStagedFiles in
  // utils/upload.ts. Keeps a 300-500 image run's per-request payload small
  // and fast to retry instead of one multi-GB request that fails outright
  // on any network blip. Purely an upload strategy — does not change how
  // many tags/images a run may contain (maxTagsPerBatchProcess above) or
  // touch the normal drag-drop upload path at all.
  batchProcessChunkMaxTags: 15,
  batchProcessChunkMaxBytes: 150 * 1024 * 1024,
  // Purely presentational grouping for the progress display ("Batch 2 of
  // 4") — mirrors backend BATCH_PROGRESS_CHUNK_SIZE. Not a processing unit.
  batchProgressChunkSize: 25,
}

export const ACCEPTED_EXTENSIONS = ['.jpg', '.jpeg', '.jfif', '.png', '.webp', '.gif', '.bmp']
