import { useEffect, type ReactNode } from 'react'

interface Props {
  open: boolean
  title: string
  /** Extra content shown in the header, to the left of the close button. */
  titleExtra?: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  width?: number
}

export default function Modal({ open, title, titleExtra, onClose, children, footer, width = 460 }: Props) {
  // Escape closes, and the page behind must not scroll while it's open.
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div
        className="modal"
        style={{ maxWidth: width }}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <h3 className="modal-title">{title}</h3>
          <div className="modal-head-actions">
            {titleExtra}
            <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">×</button>
          </div>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  )
}
