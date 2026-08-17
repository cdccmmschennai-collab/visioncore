import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Dropzone, { type DropzoneHandle } from '@/components/Dropzone'
import EditableTable from '@/components/EditableTable'
import Spinner from '@/components/Spinner'
import StatusRail from '@/components/StatusRail'
import { api } from '@/api/client'
import type { AssetTag, Batch, ExtractionPayload, ItemStatus, RejectedFile } from '@/api/types'
import { LIMITS } from '@/config'
import { stagedGroup, type StagedFile } from '@/utils/upload'
import { useToast } from '@/store/ToastContext'

const POLL_MS = 2500
const TERMINAL = new Set(['completed', 'failed', 'partial'])

// How far through the pipeline each per-tag stage counts as, so the batch
// progress bar reflects real work done rather than a generic spinner.
const STAGE_FRACTION: Record<ItemStatus, number> = {
  uploaded: 0,
  extracting: 1 / 3,
  processing: 2 / 3,
  completed: 1,
  failed: 1,
  duplicate: 1,
}

export default function NewBatch() {
  const toast = useToast()
  const navigate = useNavigate()
  const { batchId: batchIdParam } = useParams()
  const viewingExisting = Boolean(batchIdParam)
  const [files, setFiles] = useState<StagedFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [loadingBatch, setLoadingBatch] = useState(viewingExisting)
  const [batch, setBatch] = useState<Batch | null>(null)
  const [rejected, setRejected] = useState<RejectedFile[]>([])
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())
  const pollRef = useRef<number | null>(null)
  const dropzoneRef = useRef<DropzoneHandle>(null)

  const toggleDetails = (itemId: number) => {
    setExpandedItems((prev) => {
      const next = new Set(prev)
      if (next.has(itemId)) next.delete(itemId)
      else next.add(itemId)
      return next
    })
  }

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => stopPolling, [stopPolling])

  /** Poll until every tag reaches a terminal state, then stop. */
  const startPolling = useCallback(
    (batchId: number) => {
      stopPolling()
      pollRef.current = window.setInterval(async () => {
        try {
          const fresh = await api.getBatch(batchId)
          setBatch(fresh)
          if (TERMINAL.has(fresh.status)) {
            stopPolling()
            const failures = fresh.items.filter((item) => item.status === 'failed').length
            if (failures === 0) toast.success('Extraction complete.')
            else if (failures === fresh.items.length) toast.error('Extraction failed for every tag.')
            else toast.warn(`Extraction finished with ${failures} failed tag(s).`)
          }
        } catch {
          stopPolling()
        }
      }, POLL_MS)
    },
    [stopPolling, toast],
  )

  // Opened from a Recent Batches row (/batch/:batchId) — load that batch's
  // details instead of showing the upload dropzone.
  useEffect(() => {
    if (!batchIdParam) return
    let cancelled = false
    setLoadingBatch(true)
    api
      .getBatch(Number(batchIdParam))
      .then((fetched) => {
        if (cancelled) return
        setBatch(fetched)
        if (!TERMINAL.has(fetched.status)) startPolling(fetched.id)
      })
      .catch(() => { if (!cancelled) toast.error('Could not load that batch.') })
      .finally(() => !cancelled && setLoadingBatch(false))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchIdParam])

  const validTagCount = new Set(
    files.map((staged) => stagedGroup(staged).parsed).filter((p) => p.ok).map((p) => p.tagNumber),
  ).size

  const blocked =
    files.length === 0 ||
    files.length > LIMITS.maxImagesPerBatch ||
    validTagCount === 0 ||
    validTagCount > LIMITS.maxTagsPerBatch

  const upload = async () => {
    setUploading(true)
    setRejected([])
    try {
      const response = await api.upload(files)
      setBatch(response.batch)
      setRejected(response.rejected)
      setFiles([])

      const duplicates = response.duplicates.length
      const pending = response.batch.items.filter((i) => i.status !== 'duplicate').length

      if (duplicates > 0) {
        toast.warn(
          `${duplicates} tag${duplicates === 1 ? '' : 's'} already extracted — showing the existing record${duplicates === 1 ? '' : 's'}.`,
        )
      }
      if (response.rejected.length > 0) {
        toast.warn(`${response.rejected.length} file(s) couldn't be read and were skipped.`)
      }
      if (pending > 0) {
        toast.success(`Uploaded. Extracting ${pending} tag${pending === 1 ? '' : 's'}…`)
        startPolling(response.batch.id)
      }
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const refreshBatch = useCallback(async () => {
    if (!batch) return
    try {
      setBatch(await api.getBatch(batch.id))
    } catch {
      /* keep whatever is on screen */
    }
  }, [batch])

  const saveTag = async (tag: AssetTag, payload: ExtractionPayload) => {
    try {
      await api.saveTag(tag.id, payload)
      await refreshBatch()
      toast.success(`Saved ${tag.tag_number}. Both workbooks have been rebuilt.`)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not save the tag.')
      throw caught
    }
  }

  const download = async (tag: AssetTag, kind: 'ai' | 'template') => {
    try {
      const name = await (kind === 'ai' ? api.downloadAi(tag) : api.downloadTemplate(tag))
      toast.success(`Downloaded ${name}`)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Download failed.')
    }
  }

  const startOver = () => {
    stopPolling()
    setBatch(null)
    setRejected([])
    setFiles([])
  }

  const busy = batch !== null && !TERMINAL.has(batch.status)

  const progressPercent = batch && batch.items.length > 0
    ? Math.round(
        (batch.items.reduce((sum, item) => sum + STAGE_FRACTION[item.status], 0) /
          batch.items.length) * 100,
      )
    : 0
  const progressState =
    batch?.status === 'completed' ? 'success' :
    batch?.status === 'failed' ? 'failed' :
    batch?.status === 'partial' ? 'partial' : null

  return (
    <div className="page stack gap-24">
      <header className="page-head">
        <div className="stack gap-4">
          <span className="eyebrow">{viewingExisting ? 'History' : 'Extraction'}</span>
          <h1>{viewingExisting ? 'Batch Details' : 'New Batch'}</h1>
        </div>
        {batch && (
          <div className="row gap-12 wrap">
            <span className="chip chip-neutral">{batch.reference}</span>
            <button
              type="button"
              className="btn"
              onClick={() => (viewingExisting ? navigate('/batch') : startOver())}
              disabled={busy}
            >
              {viewingExisting ? 'New batch' : 'Start another batch'}
            </button>
          </div>
        )}
      </header>

      {loadingBatch && (
        <div className="card"><Spinner size={22} label="Loading batch…" /></div>
      )}

      {!batch && !viewingExisting && (
        <section className="card stack gap-16">
          <Dropzone ref={dropzoneRef} files={files} onChange={setFiles} disabled={uploading} />
          <div className="row gap-12 wrap">

            <span className="spacer" />
            <button
              type="button"
              className="btn btn-primary"
              onClick={upload}
              disabled={blocked || uploading}
            >
              {uploading ? <Spinner size={14} /> : null}
              {uploading
                ? 'Uploading…'
                : `Upload and extract${validTagCount ? ` (${validTagCount} tag${validTagCount === 1 ? '' : 's'})` : ''}`}
            </button>
          </div>
        </section>
      )}

      {rejected.length > 0 && (
        <div className="alert alert-warn">
          <span aria-hidden="true">▲</span>
          <div className="stack gap-4">
            <strong>These files were skipped</strong>
            <ul className="reject-list">
              {rejected.map((item) => (
                <li key={item.filename}>
                  <code>{item.filename}</code> — {item.reason}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {batch && (
        <section className="stack gap-16">
          <div className="row gap-12 wrap">
            <h3>Progress</h3>
            {(busy || progressState) && (
              <span className="row gap-8" style={{ alignItems: 'center' }}>
                <span
                  className={`progress-ring${progressState ? ` progress-ring-${progressState}` : ''}`}
                  style={{ '--percent': progressPercent } as React.CSSProperties}
                  role="status"
                  aria-label={
                    progressState === 'success' ? 'Success' :
                    progressState === 'failed' ? 'Failed' :
                    progressState === 'partial' ? 'Completed with issues' :
                    `Extracting, ${progressPercent}%`
                  }
                >
                  <span className="progress-ring-value" aria-hidden="true">
                    {progressState === 'success' ? '✓' :
                      progressState === 'failed' ? '✕' :
                      progressState === 'partial' ? '!' :
                      `${progressPercent}%`}
                  </span>
                </span>
                <span className="muted">
                  {progressState === 'success' ? 'Success' :
                    progressState === 'failed' ? 'Failed' :
                    progressState === 'partial' ? 'Completed with issues' :
                    'Extracting…'}
                </span>
              </span>
            )}
            <span className="spacer" />
            <span className="muted">
              {batch.total_tags} tag{batch.total_tags === 1 ? '' : 's'} ·{' '}
              {batch.total_images} image{batch.total_images === 1 ? '' : 's'}
            </span>
          </div>

          <div className="stack gap-12">
            {batch.items.map((item) => (
              <div key={item.id} className="card progress-row">
                <div className="progress-row-head">
                  <div className="stack gap-4">
                    <span className="tag-code">{item.tag_number}</span>
                    <span className="muted">{item.description}</span>
                  </div>
                  <span className="spacer" />
                  <span className="muted nowrap">
                    {item.images.length} photo{item.images.length === 1 ? '' : 's'}
                  </span>
                </div>

                <StatusRail status={item.status} />

                {item.status === 'duplicate' && (
                  <div className="alert alert-warn">
                    <span aria-hidden="true">▲</span>
                    <span>
                      <strong>Tag already extracted.</strong> This tag number is already in
                      the database, so no duplicate record was created. Its saved values and
                      workbooks are shown below.
                    </span>
                  </div>
                )}

                {item.status === 'failed' && item.error_message && (
                  <div className="alert alert-error">
                    <span aria-hidden="true">!</span>
                    <span>{item.error_message}</span>
                  </div>
                )}

                {item.asset_tag && (
                  <>
                    <div className="row gap-12 wrap" style={{ alignItems: 'center' }}>
                      <span className={`chip ${item.status === 'duplicate' ? 'chip-verify' : 'chip-confirmed'}`}>
                        {item.status === 'duplicate' ? 'Duplicate' : 'Completed'}
                      </span>
                      <span className="spacer" />
                      <button type="button" className="btn btn-sm" onClick={() => toggleDetails(item.id)}>
                        {expandedItems.has(item.id) ? 'Hide Details' : 'View Details'}
                      </button>
                    </div>

                    {expandedItems.has(item.id) && (
                      <EditableTable
                        tag={item.asset_tag}
                        onSave={(payload) => saveTag(item.asset_tag!, payload)}
                        onDownloadAi={() => download(item.asset_tag!, 'ai')}
                        onDownloadTemplate={() => download(item.asset_tag!, 'template')}
                      />
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
