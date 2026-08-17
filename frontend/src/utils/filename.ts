/**
 * Client-side mirror of the backend's filename parser.
 *
 * It exists so the dropzone can group and validate before an upload is sent —
 * the server re-parses everything and its answer is the one that counts.
 */
const SUPPORTED = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.jfif']
const COPY_SUFFIX = /\s*(?:\(\d+\)|[-_ ]cop(?:y|ie)\d*)\s*$/i

export interface ParsedName {
  tagNumber: string
  description: string
  ok: boolean
  reason?: string
}

function looksLikeDescription(segment: string): boolean {
  const s = segment.trim()
  if (!s) return false
  if (s.includes(' ') || s.includes(',') || s.includes('/')) return true
  return /^[A-Za-z]+$/.test(s) && s.length >= 4
}

function splitTagDescription(stem: string, example: string): ParsedName {
  const cleaned = stem
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(COPY_SUFFIX, '')

  const segments = cleaned.split('-').map((s) => s.trim())
  if (segments.length < 2 || segments.some((s) => !s)) {
    return {
      tagNumber: '', description: '', ok: false,
      reason: `Expected <TAG>-<DESCRIPTION>, e.g. ${example}`,
    }
  }

  let splitAt = -1
  for (let i = 1; i < segments.length; i += 1) {
    if (looksLikeDescription(segments[i])) { splitAt = i; break }
  }
  if (splitAt === -1 && /^[A-Za-z]+$/.test(segments[segments.length - 1])) {
    splitAt = segments.length - 1
  }
  if (splitAt === -1) {
    return {
      tagNumber: '', description: '', ok: false,
      reason: "Couldn't tell where the tag number ends and the description begins",
    }
  }

  return {
    tagNumber: segments.slice(0, splitAt).join('-').toUpperCase(),
    description: segments.slice(splitAt).join('-').toUpperCase(),
    ok: true,
  }
}

export function parseFilename(filename: string): ParsedName {
  const base = filename.split(/[\\/]/).pop() ?? filename
  const dot = base.lastIndexOf('.')
  const extension = dot === -1 ? '' : base.slice(dot).toLowerCase()

  if (!SUPPORTED.includes(extension)) {
    return {
      tagNumber: '', description: '', ok: false,
      reason: `Unsupported file type ${extension || '(none)'}`,
    }
  }

  const stem = dot === -1 ? base : base.slice(0, dot)
  return splitTagDescription(stem, '12-4020-BV-0074-BALL VALVE.jpg')
}

/**
 * Same `<TAG>-<DESCRIPTION>` convention, applied to a subfolder's name.
 * Used when a user selects/drops a folder tree: each leaf subfolder is
 * treated as one tag, and its name is parsed the same way a filename would be.
 */
export function parseFolderName(folderName: string): ParsedName {
  const base = folderName.split(/[\\/]/).filter(Boolean).pop() ?? folderName
  return splitTagDescription(base, '12-4020-BV-0074-BALL VALVE')
}

export function formatDateTime(iso: string): { date: string; time: string } {
  const value = new Date(iso)
  return {
    date: value.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' }),
    time: value.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
  }
}

export function formatNumber(value: number): string {
  return value.toLocaleString()
}
