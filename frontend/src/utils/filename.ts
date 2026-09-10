/**
 * Client-side mirror of the backend's filename parser.
 *
 * It exists so the dropzone can group and validate before an upload is sent —
 * the server re-parses everything and its answer is the one that counts.
 */
const SUPPORTED = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.jfif']
const COPY_SUFFIX = /\s*(?:\(\d+\)|[-_ ]cop(?:y|ie)\d*)\s*$/i
// A space, comma or underscore directly after a digit is acting as the
// boundary between the tag number's numeric tail and the description (e.g.
// "1067 FIRE...", "1001,TEMPERATURE ELEMENT" or "1001_ELECTRONIC..."), so
// treat it as a segment break there, same as a hyphen. Elsewhere a comma is
// literal punctuation inside the description ("VALVE,GATE") and an
// underscore is a plain space substitute ("BALL_VALVE") — both left alone;
// a plain space elsewhere is already description-internal word-spacing
// ("BALL VALVE") and needs no special handling.
const TAG_BOUNDARY_SEP = /(?<=\d)[,_ ]\s*/g

export interface ParsedName {
  tagNumber: string
  description: string
  ok: boolean
  reason?: string
  /**
   * True when `ok` was granted provisionally: no description was given and
   * this tag's equipment code isn't in the small list this file knows
   * about. The server checks it against every previously extracted tag's
   * accepted description (see backend/app/services/equipment_codes.py) and
   * is the one that actually decides — if it can't resolve it either, the
   * upload response's `rejected` list reports it back, same as any other
   * unreadable name.
   */
  pending?: boolean
}

/**
 * A description segment reads as words, not as a tag code. Only a segment
 * containing a space, comma or slash counts here — a bare alphabetic segment
 * ("lJBF", "TIT") is still a plausible tag code no matter how long it is, so
 * it's only ever treated as a description when it's the *last* segment (see
 * the fallback below). Otherwise a 4+ letter tag code sitting mid-sequence
 * would be misread as the start of the description.
 */
function looksLikeDescription(segment: string): boolean {
  const s = segment.trim()
  if (!s) return false
  return s.includes(' ') || s.includes(',') || s.includes('/')
}

// ISA-style equipment-code segments a tag number carries in place of a
// written-out description (e.g. the "BV" in "22-4203-BV-0119"), mapped to
// the plain equipment name to use as the description when no separate
// description segment was supplied at all. Mirrors
// backend/app/services/filename_parser.py's EQUIPMENT_CODE_DESCRIPTIONS —
// keep the two in sync.
const EQUIPMENT_CODE_DESCRIPTIONS: Record<string, string> = {
  BV: 'BALL VALVE',
  GV: 'GATE VALVE',
  GLV: 'GLOBE VALVE',
  BFV: 'BUTTERFLY VALVE',
  PMP: 'PUMP',
  MTR: 'MOTOR',
  CMP: 'COMPRESSOR',
  PG: 'PRESSURE GAUGE',
}

/**
 * Find a known equipment-code segment among a tag's own segments. Used only
 * as a last resort, when the tag carries no separate description segment at
 * all, so a tag-only name like "22-4203-BV-0119.jpg" can still resolve to a
 * description ("BALL VALVE") instead of failing outright.
 */
function equipmentCodeDescription(segments: string[]): string | null {
  for (const segment of segments) {
    const description = EQUIPMENT_CODE_DESCRIPTIONS[segment.trim().toUpperCase()]
    if (description) return description
  }
  return null
}

function splitTagDescription(stem: string, example: string): ParsedName {
  const cleaned = stem
    .replace(TAG_BOUNDARY_SEP, '-')
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
  // Last resort: no description segment at all, e.g. "22-4203-BV-0119" —
  // the whole stem is the tag number, and its embedded equipment code
  // ("BV") supplies the description instead.
  if (splitAt === -1) {
    const codeDescription = equipmentCodeDescription(segments)
    if (codeDescription) {
      return { tagNumber: segments.join('-').toUpperCase(), description: codeDescription, ok: true }
    }
    // Not one of the handful of codes this file knows about — don't block
    // the upload over it. The server also checks every previously
    // extracted tag's accepted description for this code (a much bigger,
    // constantly-growing list than this static one), so let it have the
    // final say instead of rejecting a tag it might actually recognize.
    return {
      tagNumber: segments.join('-').toUpperCase(), description: '', ok: true, pending: true,
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

/** Adaptive KB/MB/GB display for an actual byte count — never estimated. */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`
}
