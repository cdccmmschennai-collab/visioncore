import { parseFilename, parseFolderName, type ParsedName } from './filename'

/**
 * A file staged for upload, plus (when it came from a folder rather than a
 * loose file pick) the name of its immediate parent subfolder.
 *
 * `folder` is what drives tag grouping for folder uploads: every image whose
 * immediate parent directory shares a name is treated as one tag, regardless
 * of how deep that folder sits in the tree the user selected/dropped.
 */
export interface StagedFile {
  file: File
  folder: string | null
}

export function stagedKey(staged: StagedFile): string {
  return `${staged.folder ?? ''}␟${staged.file.name}:${staged.file.size}`
}

/** Resolve the tag-grouping key and parse result for one staged file. */
export function stagedGroup(staged: StagedFile): { key: string; parsed: ParsedName } {
  const parsed = staged.folder !== null ? parseFolderName(staged.folder) : parseFilename(staged.file.name)
  const key = parsed.ok ? parsed.tagNumber : `⚠ ${staged.folder ?? staged.file.name}`
  return { key, parsed }
}

/** Files picked via a plain `<input type="file">` — never folder-sourced. */
export function stagedFromFiles(files: FileList | File[]): StagedFile[] {
  return Array.from(files).map((file) => ({ file, folder: null }))
}

/**
 * Files picked via a `webkitdirectory` input. Each File carries a
 * `webkitRelativePath` like `RootFolder/Sub1/img.jpg`; the immediate parent
 * segment becomes the tag-grouping folder.
 */
export function stagedFromDirectoryInput(files: FileList): StagedFile[] {
  return Array.from(files).map((file) => {
    const relPath = (file as File & { webkitRelativePath?: string }).webkitRelativePath
    if (!relPath) return { file, folder: null }
    const parts = relPath.split('/')
    const folder = parts.length >= 2 ? parts[parts.length - 2] : null
    return { file, folder }
  })
}

interface FileSystemEntryLike {
  isFile: boolean
  isDirectory: boolean
  name: string
  file(success: (file: File) => void, error: (err: unknown) => void): void
  createReader(): {
    readEntries(
      success: (entries: FileSystemEntryLike[]) => void,
      error: (err: unknown) => void,
    ): void
  }
}

async function readAllEntries(reader: {
  readEntries(
    success: (entries: FileSystemEntryLike[]) => void,
    error: (err: unknown) => void,
  ): void
}): Promise<FileSystemEntryLike[]> {
  // The Directory Reader API returns entries in batches (often capped at
  // 100), so it must be drained with repeated calls until one comes back empty.
  const all: FileSystemEntryLike[] = []
  for (;;) {
    const batch = await new Promise<FileSystemEntryLike[]>((resolve, reject) =>
      reader.readEntries(resolve, reject),
    )
    if (batch.length === 0) break
    all.push(...batch)
  }
  return all
}

async function walkEntry(
  entry: FileSystemEntryLike,
  parent: string | null,
  out: StagedFile[],
): Promise<{ ok: boolean }> {
  try {
    if (entry.isFile) {
      const file = await new Promise<File>((resolve, reject) => entry.file(resolve, reject))
      out.push({ file, folder: parent })
      return { ok: true }
    }
    if (entry.isDirectory) {
      const entries = await readAllEntries(entry.createReader())
      const results = await Promise.all(entries.map((child) => walkEntry(child, entry.name, out)))
      return { ok: results.every((r) => r.ok) }
    }
    return { ok: true }
  } catch {
    // Most often a cloud-placeholder file (OneDrive/network-drive "Files On-
    // Demand") that never fully hydrates during a browser drag-drop — the OS
    // file dialog handles this correctly, drag-and-drop doesn't. Report it
    // rather than silently dropping the file.
    return { ok: false }
  }
}

export interface DataTransferResult {
  staged: StagedFile[]
  /** Count of dropped entries that could not be read (see walkEntry). */
  unreadableCount: number
}

/**
 * Resolve a drag-and-drop payload into staged files, recursively walking any
 * dropped folders so a whole directory tree can be dropped at once. Falls
 * back to the flat file list for browsers without the entry API.
 */
export async function stagedFromDataTransfer(dataTransfer: DataTransfer): Promise<DataTransferResult> {
  const items = dataTransfer.items
  if (!items || items.length === 0) {
    return { staged: stagedFromFiles(dataTransfer.files), unreadableCount: 0 }
  }

  const out: StagedFile[] = []
  const tasks: Promise<{ ok: boolean }>[] = []

  for (const item of Array.from(items)) {
    const getAsEntry = (item as DataTransferItem & { webkitGetAsEntry?: () => FileSystemEntryLike | null })
      .webkitGetAsEntry
    const entry = getAsEntry?.call(item)
    if (entry) {
      tasks.push(walkEntry(entry, null, out))
    } else {
      const file = item.getAsFile()
      if (file) out.push({ file, folder: null })
    }
  }

  const results = await Promise.all(tasks)
  const unreadableCount = results.filter((r) => !r.ok).length
  return { staged: out, unreadableCount }
}
