import Modal from '@/components/Modal'
import Spinner from '@/components/Spinner'

interface Props {
  open: boolean
  title: string
  message: string
  busy?: boolean
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
}

/** Generic "are you sure?" step for a destructive action — wraps the
 * existing Modal component rather than a browser confirm(), matching the
 * modal-based UX every other flow in this app already uses. */
export default function ConfirmDialog({
  open, title, message, busy = false, confirmLabel = 'Delete', onConfirm, onCancel,
}: Props) {
  return (
    <Modal open={open} title={title} onClose={onCancel}>
      <div className="stack gap-16">
        <p className="muted" style={{ margin: 0 }}>{message}</p>
        <div className="row gap-8">
          <span className="spacer" />
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={busy}>
            {busy ? <Spinner size={14} /> : null}
            {busy ? 'Deleting…' : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  )
}
