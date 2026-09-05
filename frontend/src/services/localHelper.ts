/**
 * Talks to the optional VisionCore Local Helper — a tiny app the user runs on
 * their own Windows PC (see local-helper/README.md) so the generated
 * workbooks can be saved straight to
 * `C:\Asset photo data capturing tool\<TAG NAME>\` without the browser
 * needing filesystem access it doesn't have.
 *
 * Best-effort only: if the helper isn't running, every call here fails
 * silently (after one console warning) and the rest of the app — extraction,
 * editing, manual download — is completely unaffected. The helper itself
 * decides file names: it never overwrites "AI Output.xlsx" or
 * "Template Output.xlsx" once they exist, and always adds the next
 * "Template Output Revision N.xlsx" rather than overwriting a prior one.
 */
import { api } from '@/api/client'
import type { AssetTag } from '@/api/types'

const HELPER_URL = 'http://127.0.0.1:5577'
// Must match SHARED_TOKEN in local-helper/visioncore_local_helper.py.
const HELPER_TOKEN = 'visioncore-local-helper'
const HELPER_TIMEOUT_MS = 4000

let warned = false

function warnOnce(message: string, err: unknown): void {
  if (warned) return
  warned = true
  console.warn(`[VisionCore Local Helper] ${message}`, err)
}

/** Matches backend excel_basename() — the same "<TAG>-<DESCRIPTION>" stem
 * every exported workbook is already named after. */
function tagFolderName(tag: AssetTag): string {
  return `${tag.tag_number}-${tag.description}`
}

async function post(
  kind: 'ai' | 'template_base' | 'template_revision',
  tagFolder: string,
  blob: Blob,
): Promise<void> {
  const source = `${kind} workbook for ${tagFolder}`
  const destination = `C:\\Asset photo data capturing tool\\${tagFolder}\\ (kind=${kind})`
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), HELPER_TIMEOUT_MS)
  try {
    const url = `${HELPER_URL}/save?tag_folder=${encodeURIComponent(tagFolder)}&kind=${kind}`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'X-VisionCore-Token': HELPER_TOKEN, 'Content-Type': 'application/octet-stream' },
      body: blob,
      signal: controller.signal,
    })
    if (!response.ok) {
      const body = await response.text().catch(() => '')
      throw new Error(`Local helper responded ${response.status}${body ? `: ${body}` : ''}`)
    }
  } catch (err) {
    // Always logged (unlike the one-time warning below) so a save that
    // starts failing after the helper was previously reachable — a
    // permission error, a locked file, the helper crashing — never goes by
    // completely unnoticed the way a single suppressed warning would.
    console.error('[VisionCore Local Helper] File save failed', {
      source,
      destination,
      error: err instanceof Error ? err.message : err,
    })
    warnOnce(
      'Not reachable at 127.0.0.1:5577 — workbooks were not auto-saved to this PC. '
      + 'Manual download still works normally. See local-helper/README.md.',
      err,
    )
  } finally {
    window.clearTimeout(timer)
  }
}

/** Called once, right after a tag's extraction completes. */
export async function pushExtractedWorkbooks(tag: AssetTag): Promise<void> {
  try {
    const folder = tagFolderName(tag)
    const [aiBlob, templateBlob] = await Promise.all([
      api.fetchAiBlob(tag),
      api.fetchTemplateBlob(tag),
    ])
    await Promise.all([
      post('ai', folder, aiBlob),
      post('template_base', folder, templateBlob),
    ])
  } catch (err) {
    warnOnce(`Could not fetch generated workbooks for ${tag.tag_number}.`, err)
  }
}

/** Called every time an edited tag is saved — adds a new revision file,
 * never touches "Template Output.xlsx" or an earlier revision. */
export async function pushTemplateRevision(tag: AssetTag): Promise<void> {
  try {
    const folder = tagFolderName(tag)
    const blob = await api.fetchTemplateBlob(tag)
    await post('template_revision', folder, blob)
  } catch (err) {
    warnOnce(`Could not fetch the updated Template workbook for ${tag.tag_number}.`, err)
  }
}
