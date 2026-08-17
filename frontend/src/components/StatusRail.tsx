import type { ItemStatus } from '@/api/types'

/**
 * The processing pipeline, drawn as a segmented rail.
 *
 * This is the one place the interface gets to be expressive, and it earns it:
 * the four stages are a real sequence with real duration, so showing position
 * along a run tells the user something a spinner cannot — which stage is slow,
 * and how much is left.
 */
const STAGES = ['Uploaded', 'Extracting', 'Processing', 'Completed'] as const

const STAGE_INDEX: Record<ItemStatus, number> = {
  uploaded: 0,
  extracting: 1,
  processing: 2,
  completed: 3,
  failed: -1,
  duplicate: -1,
}

interface Props {
  status: ItemStatus
  compact?: boolean
}

export default function StatusRail({ status, compact = false }: Props) {
  const failed = status === 'failed'
  const duplicate = status === 'duplicate'
  const active = STAGE_INDEX[status]

  if (failed || duplicate) {
    return (
      <div className={`rail rail-${failed ? 'failed' : 'duplicate'}`} role="status">
        <span className="chip chip-danger" style={duplicate ? { color: 'var(--vc-verify)', borderColor: 'var(--vc-verify)', background: 'var(--vc-verify-wash)' } : undefined}>
          {failed ? 'Failed' : 'Tag already extracted'}
        </span>
      </div>
    )
  }

  return (
    <div
      className={`rail${compact ? ' rail-compact' : ''}`}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={STAGES.length}
      aria-valuenow={active + 1}
      aria-label={`Processing stage: ${STAGES[Math.max(0, active)]}`}
    >
      {STAGES.map((stage, index) => {
        const state =
          index < active ? 'done' : index === active ? 'current' : 'pending'
        return (
          <div key={stage} className={`rail-seg rail-${state}`}>
            <span className="rail-marker" aria-hidden="true">
              {state === 'done' ? '✓' : index + 1}
            </span>
            {!compact && <span className="rail-label">{stage}</span>}
            {index < STAGES.length - 1 && <span className="rail-link" aria-hidden="true" />}
          </div>
        )
      })}
    </div>
  )
}
