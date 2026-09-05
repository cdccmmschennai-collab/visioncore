/**
 * Browser-side local folder access for the "Batch Process" button (File
 * System Access API — Chrome/Edge only).
 *
 * The backend used to scan a hardcoded local path directly on its own disk
 * (`C:\Asset photo-Tag extraction`), which only worked when the backend
 * happened to run on the same PC as that folder. That breaks the moment the
 * app is deployed to a server that isn't this machine. Doing the scan (and
 * the AI Extraction / Consolidate file write-back) here in the browser
 * instead means the same folder is always read and written locally,
 * regardless of where the backend runs — same fix as
 * `frontend/src/services/localHelper.ts` applies to per-tag workbook
 * auto-save, just via the browser's own filesystem API instead of a
 * separate local helper process.
 */
import { ACCEPTED_EXTENSIONS } from '@/config'
import type { StagedFile } from './upload'

/** Minimal shape of the File System Access API types this module uses —
 * declared locally (rather than relying on lib.dom.d.ts, which doesn't
 * reliably ship these across TypeScript versions) so this compiles
 * regardless of the configured `lib`. */
export interface FSFileHandle {
  kind: 'file'
  name: string
  getFile(): Promise<File>
  createWritable(): Promise<FSWritableFileStream>
}

export interface FSDirectoryHandle {
  kind: 'directory'
  name: string
  values(): AsyncIterableIterator<FSFileHandle | FSDirectoryHandle>
  getDirectoryHandle(name: string, options?: { create?: boolean }): Promise<FSDirectoryHandle>
  getFileHandle(name: string, options?: { create?: boolean }): Promise<FSFileHandle>
}

export interface FSWritableFileStream {
  write(data: Blob): Promise<void>
  close(): Promise<void>
}

interface DirectoryPickerWindow {
  showDirectoryPicker(options?: { mode?: 'read' | 'readwrite' }): Promise<FSDirectoryHandle>
}

// Same reserved subfolder names the old server-side scan skipped — these
// are output folders, never a tag to extract.
const RESERVED_DIR_NAMES = new Set(['ai extraction', 'consolidate file'])

export function isFolderAccessSupported(): boolean {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window
}

/** Opens the OS folder picker with read+write access. Rejects with
 * `AbortError` if the user cancels — callers should swallow that silently. */
export function pickBatchProcessFolder(): Promise<FSDirectoryHandle> {
  return (window as unknown as DirectoryPickerWindow).showDirectoryPicker({ mode: 'readwrite' })
}

function hasSupportedExtension(name: string): boolean {
  const dot = name.lastIndexOf('.')
  const ext = dot === -1 ? '' : name.slice(dot).toLowerCase()
  return ACCEPTED_EXTENSIONS.includes(ext)
}

/**
 * Client-side mirror of the backend's old `scan_tag_folders()`: each
 * immediate subfolder is one tag (`<TAG>-<DESCRIPTION>\*.jpg`), and loose
 * `<TAG>-<DESCRIPTION>.jpg` files dropped directly in the root are also
 * accepted — same two ways a normal folder/file upload already works.
 *
 * Deliberately does not validate the `<TAG>-<DESCRIPTION>` naming itself —
 * every image found is staged and sent up, and the server (same
 * `parse_folder_name`/`parse_filename` a normal upload uses) reports back
 * anything unparsable via the batch's `rejected` list, exactly like a normal
 * folder upload's rejections.
 */
export async function scanTagFolders(dir: FSDirectoryHandle): Promise<StagedFile[]> {
  const staged: StagedFile[] = []

  for await (const entry of dir.values()) {
    if (entry.kind === 'directory') {
      if (RESERVED_DIR_NAMES.has(entry.name.trim().toLowerCase())) continue

      for await (const child of entry.values()) {
        if (child.kind !== 'file' || !hasSupportedExtension(child.name)) continue
        const file = await (child as FSFileHandle).getFile()
        staged.push({ file, folder: entry.name })
      }
      continue
    }

    if (entry.kind === 'file' && hasSupportedExtension(entry.name)) {
      const file = await (entry as FSFileHandle).getFile()
      staged.push({ file, folder: null })
    }
  }

  return staged
}

/** Mirrors the backend's `safe_filename()` (app/services/filename_parser.py)
 * so a subfolder or file name written back to disk can't break on a
 * Windows-invalid character. */
export function safeFilename(name: string): string {
  const cleaned = name.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').trim().replace(/[ .]+$/, '')
  return cleaned || 'download'
}

/** Writes `blob` to `<dir>/<subfolder>/<filename>`, creating the subfolder
 * and file as needed. */
export async function writeFileToFolder(
  dir: FSDirectoryHandle,
  subfolder: string,
  filename: string,
  blob: Blob,
): Promise<void> {
  const subDir = await dir.getDirectoryHandle(subfolder, { create: true })
  const fileHandle = await subDir.getFileHandle(safeFilename(filename), { create: true })
  const writable = await fileHandle.createWritable()
  await writable.write(blob)
  await writable.close()
}

const _REVISION_NAME = /Revision (\d+)\.xlsx$/i

/** Next "<prefix> Revision N.xlsx" name not already present in
 * `<dir>/<subfolder>` — mirrors the Local Helper's own
 * `next_revision_path()` (local-helper/visioncore_local_helper.py) so a
 * revision here is never reused/overwritten either. */
export async function nextRevisionFilename(
  dir: FSDirectoryHandle,
  subfolder: string,
  prefix: string,
): Promise<string> {
  const subDir = await dir.getDirectoryHandle(subfolder, { create: true })
  let highest = 0
  for await (const entry of subDir.values()) {
    if (entry.kind !== 'file' || !entry.name.startsWith(prefix)) continue
    const match = entry.name.match(_REVISION_NAME)
    if (match) highest = Math.max(highest, Number(match[1]))
  }
  return `${prefix} Revision ${highest + 1}.xlsx`
}
