import type { Quality } from '@/api/types'

/**
 * Confirmed / Verify, coloured exactly as the workbooks colour them, so the
 * screen and the exported sheet agree at a glance.
 */
export default function QualityChip({ quality }: { quality: Quality }) {
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
