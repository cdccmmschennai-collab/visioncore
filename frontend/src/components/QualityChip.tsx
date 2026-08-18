import type { Quality } from '@/api/types'

/**
 * Confirmed / Verify, coloured exactly as the workbooks colour them, so the
 * screen and the exported sheet agree at a glance. A field whose value is
 * "Not present on nameplate" shows a neutral "Data not available" chip
 * instead — there's nothing to confirm or verify.
 */
export default function QualityChip({ quality, missing = false }: { quality: Quality; missing?: boolean }) {
  if (missing) {
    return (
      <span className="chip chip-neutral" title="This field was not present on the nameplate">
        Data not available
      </span>
    )
  }

  const confirmed = quality === 'Confirmed'
  return (
    <span
      className={`chip ${confirmed ? 'chip-confirmed' : 'chip-verify'}`}
      title={
        confirmed
          ? 'Clearly legible and read directly from the nameplate'
          : 'Inferred, worn, or not printed — check in the field'
      }
    >
      {quality}
    </span>
  )
}
