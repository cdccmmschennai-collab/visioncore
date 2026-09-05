import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import BatchImagesModal from '@/components/BatchImagesModal'
import Dropzone, { type DropzoneHandle } from '@/components/Dropzone'
import EditableTable from '@/components/EditableTable'
import Modal from '@/components/Modal'
import Spinner from '@/components/Spinner'
import StatusRail from '@/components/StatusRail'
import { api } from '@/api/client'
import type { AssetTag, Batch, BatchItem, ExtractionPayload, ItemStatus, RejectedFile } from '@/api/types'
import { LIMITS } from '@/config'
import {
  isFolderAccessSupported,
  nextRevisionFilename,
  pickBatchProcessFolder,
  scanTagFolders,
  writeFileToFolder,
  type FSDirectoryHandle,
} from '@/utils/folderAccess'
import { pushExtractedWorkbooks, pushTemplateRevision } from '@/services/localHelper'
import { formatFileSize } from '@/utils/filename'
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
  const location = useLocation()
  const { batchId: batchIdParam } = useParams()
  const viewingExisting = Boolean(batchIdParam)
  // Set only by the "New Batch" button, so a blank screen is opt-in — every
  // other way of landing on /batch (nav tab, browser back, a bookmark)
  // should default to showing the latest extraction instead.
  const cameFresh = Boolean((location.state as { fresh?: boolean } | null)?.fresh)
  const [files, setFiles] = useState<StagedFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [loadingBatch, setLoadingBatch] = useState(viewingExisting || !cameFresh)
  const [batch, setBatch] = useState<Batch | null>(null)
  const [rejected, setRejected] = useState<RejectedFile[]>([])
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())
  const [viewingBatchId, setViewingBatchId] = useState<number | null>(null)
  const [viewingItemId, setViewingItemId] = useState<number | null>(null)
  const [retryingIds, setRetryingIds] = useState<Set<number>>(new Set())
  const pollRef = useRef<number | null>(null)
  const dropzoneRef = useRef<DropzoneHandle>(null)
  // Batch items already auto-saved to the local helper this session, so a
  // freshly-completed tag is pushed exactly once — not on every poll tick,
  // and not again for a tag that was already completed before this page
  // was opened (see the "load existing batch" effect below, which seeds this).
  const autoSavedRef = useRef<Set<number>>(new Set())
  // Holds the batch id while — and only while — that batch was started by
  // this page's own "Batch Process" click, so the completion popup below
  // fires for that one batch and never for a normal upload or a batch
  // reopened from History (whose id will never match).
  const [batchProcessing, setBatchProcessing] = useState(false)
  const batchProcessRunRef = useRef<number | null>(null)
  // The local folder the current (or most recently completed) Batch Process
  // run was picked from, and which batch id it belongs to — kept around
  // across a retry (not cleared once the batch first reaches a terminal
  // state) so a re-extracted tag's AI Extraction copy and the consolidated
  // workbook keep getting written back into it. See folderAccess.ts.
  const batchProcessDirRef = useRef<{ dir: FSDirectoryHandle; batchId: number } | null>(null)
  const writeBackWarnedRef = useRef(false)
  const [batchProcessSummary, setBatchProcessSummary] = useState<
    { total: number; completed: number; failed: number } | null
  >(null)

  // Auto-save folder for the plain "Upload and extract" / drag-and-drop
  // workflow — entirely separate from batchProcessDirRef above, so it never
  // applies to (and is never touched by) a Batch Process run. Picked once via
  // the button in the dropzone section below and then reused for every batch
  // this page creates for the rest of the session — see writeDragDropAutoSave.
  const dragDropDirRef = useRef<FSDirectoryHandle | null>(null)
  const [dragDropDirName, setDragDropDirName] = useState<string | null>(null)
  const dragDropSaveWarnedRef = useRef(false)

  const warnWriteBackFailure = useCallback((context: string, err: unknown) => {
    // Logged unconditionally (even after the first toast) so a real repro
    // gives us the actual cause instead of another silent no-op.
    console.error(`[Batch Process] local folder write failed — ${context}`, err)
    if (writeBackWarnedRef.current) return
    writeBackWarnedRef.current = true
    toast.warn(
      "Could not write results into the AI Extraction / Consolidate file folders — the Download buttons still work normally.",
    )
  }, [toast])

  /** Copies one just-completed tag's AI Output workbook into
   * `<picked folder>/AI Extraction/`, mirroring what the server used to do
   * for a local-only deployment. Best-effort — never blocks or fails the
   * extraction itself. */
  const writeAiExtractionCopy = useCallback(
    async (dir: FSDirectoryHandle, item: BatchItem) => {
      if (!item.asset_tag) return
      try {
        const blob = await api.fetchAiBlob(item.asset_tag)
        await writeFileToFolder(
          dir, 'AI Extraction', `AI Extraction_${item.tag_number}-${item.description}.xlsx`, blob,
        )
      } catch (err) {
        warnWriteBackFailure(`AI Extraction copy for ${item.tag_number}`, err)
      }
    },
    [warnWriteBackFailure],
  )

  /** (Re)writes the one consolidated workbook for this Batch Process run
   * into `<picked folder>/Consolidate file/`, overwriting the same file each
   * time — same "one file per batch, always current" behaviour the server
   * used to give. */
  const writeConsolidatedCopy = useCallback(
    async (dir: FSDirectoryHandle, reference: string, tagNumbers: string[]) => {
      try {
        const blob = await api.fetchConsolidatedBlob(tagNumbers)
        await writeFileToFolder(dir, 'Consolidate file', `Consolidated_${reference}.xlsx`, blob)
      } catch (err) {
        warnWriteBackFailure(`consolidated workbook for ${reference}`, err)
      }
    },
    [warnWriteBackFailure],
  )

  /** Saves one just-completed drag-and-drop tag's AI Output + Template Output
   * into `<picked folder>/<TAG NUMBER>-<DESCRIPTION>/`, creating both the
   * folder and the subfolder as needed (see writeFileToFolder in
   * utils/folderAccess.ts). Entirely separate from the Batch Process
   * write-back above — different ref, different folder layout (one subfolder
   * per tag here vs. shared "AI Extraction"/"Consolidate file" folders
   * there) — and from the optional Local Helper push (pushExtractedWorkbooks),
   * which keeps running in parallel regardless of whether this folder is set. */
  const writeDragDropAutoSave = useCallback(
    async (dir: FSDirectoryHandle, item: BatchItem) => {
      if (!item.asset_tag) return
      const subfolder = `${item.tag_number}-${item.description}`
      try {
        const [aiBlob, templateBlob] = await Promise.all([
          api.fetchAiBlob(item.asset_tag),
          api.fetchTemplateBlob(item.asset_tag),
        ])
        await Promise.all([
          writeFileToFolder(dir, subfolder, 'AI Output.xlsx', aiBlob),
          writeFileToFolder(dir, subfolder, 'Template Output.xlsx', templateBlob),
        ])
      } catch (err) {
        // Always logged (not just the one-time toast below) so a failure
        // that starts happening later in the session — permission revoked,
        // the folder moved/deleted, disk full — leaves a real trail.
        console.error('[New Batch auto-save] File save failed', {
          source: `${item.tag_number} workbooks`,
          destination: `${dragDropDirName ?? 'chosen folder'}\\${subfolder}\\`,
          error: err instanceof Error ? err.message : err,
        })
        if (!dragDropSaveWarnedRef.current) {
          dragDropSaveWarnedRef.current = true
          toast.warn(
            `Could not auto-save ${item.tag_number} to the chosen folder — the Download buttons still work normally.`,
          )
        }
      }
    },
    [dragDropDirName, toast],
  )

  /** Adds a new "Template Output Revision N.xlsx" into the drag-and-drop
   * auto-save folder whenever an already-extracted tag is edited and saved —
   * mirrors the Local Helper's own revisioning (pushTemplateRevision /
   * next_revision_path) but inside the picked folder instead. The base
   * "Template Output.xlsx" written by writeDragDropAutoSave above is never
   * touched again. */
  const writeDragDropTemplateRevision = useCallback(
    async (dir: FSDirectoryHandle, tag: AssetTag) => {
      const subfolder = `${tag.tag_number}-${tag.description}`
      try {
        const blob = await api.fetchTemplateBlob(tag)
        const filename = await nextRevisionFilename(dir, subfolder, 'Template Output')
        await writeFileToFolder(dir, subfolder, filename, blob)
      } catch (err) {
        console.error('[New Batch auto-save] Revision save failed', {
          source: `${tag.tag_number} template revision`,
          destination: `${dragDropDirName ?? 'chosen folder'}\\${subfolder}\\`,
          error: err instanceof Error ? err.message : err,
        })
        if (!dragDropSaveWarnedRef.current) {
          dragDropSaveWarnedRef.current = true
          toast.warn(
            `Could not save a revision for ${tag.tag_number} to the chosen folder — the Download buttons still work normally.`,
          )
        }
      }
    },
    [dragDropDirName, toast],
  )

  /** Adds a new "Consolidated_<reference> Revision N.xlsx" into the Batch
   * Process folder whenever an already-extracted tag from that run is
   * edited and saved later. Deliberately does NOT touch the per-tag
   * "AI Extraction" copy (writeAiExtractionCopy) or the original
   * "Consolidated_<reference>.xlsx" from extraction time
   * (writeConsolidatedCopy, unchanged, above) — per the requirement, only
   * the consolidated file gets revisioned for a Batch Process run. */
  const writeConsolidatedRevision = useCallback(
    async (dir: FSDirectoryHandle, currentBatch: Batch) => {
      const tagNumbers = currentBatch.items
        .filter((item) => (item.status === 'completed' || item.status === 'duplicate') && item.asset_tag)
        .map((item) => item.tag_number)
      if (tagNumbers.length === 0) return
      try {
        const blob = await api.fetchConsolidatedBlob(tagNumbers)
        const filename = await nextRevisionFilename(dir, 'Consolidate file', `Consolidated_${currentBatch.reference}`)
        await writeFileToFolder(dir, 'Consolidate file', filename, blob)
      } catch (err) {
        warnWriteBackFailure(`consolidated revision for ${currentBatch.reference}`, err)
      }
    },
    [warnWriteBackFailure],
  )

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
          const dirState = batchProcessDirRef.current
          const dirForThisBatch = dirState && dirState.batchId === fresh.id ? dirState.dir : null
          // Auto-save AI Output + Template Output to the local helper, and —
          // for a Batch Process run — the AI Extraction copy into the picked
          // folder, the moment a tag's extraction completes (or resolves as
          // an already-extracted duplicate). Once per item, ever.
          fresh.items.forEach((item) => {
            const justResolved = (item.status === 'completed' || item.status === 'duplicate')
              && item.asset_tag && !autoSavedRef.current.has(item.id)
            if (!justResolved) return
            autoSavedRef.current.add(item.id)
            if (item.status === 'completed') void pushExtractedWorkbooks(item.asset_tag!)
            if (dirForThisBatch) void writeAiExtractionCopy(dirForThisBatch, item)
            // Drag-and-drop's own auto-save folder — only for a batch that
            // isn't the active Batch Process run (dirForThisBatch is only
            // ever set for that one), so the two never write into each other's
            // folders even if both have been picked in the same session.
            if (!dirForThisBatch && item.status === 'completed' && dragDropDirRef.current) {
              void writeDragDropAutoSave(dragDropDirRef.current, item)
            }
          })
          // A retried item is done once it leaves the active pipeline states.
          setRetryingIds((prev) => {
            if (prev.size === 0) return prev
            const stillActive = new Set(
              fresh.items
                .filter((item) => item.status === 'uploaded' || item.status === 'extracting' || item.status === 'processing')
                .map((item) => item.id),
            )
            const next = new Set([...prev].filter((id) => stillActive.has(id)))
            return next.size === prev.size ? prev : next
          })
          if (TERMINAL.has(fresh.status)) {
            stopPolling()
            const failures = fresh.items.filter((item) => item.status === 'failed').length
            // Refresh the one consolidated workbook for this run every time it
            // reaches a terminal state — including after a retry — same as
            // the AI Extraction copies above.
            if (dirForThisBatch) {
              const tagNumbers = fresh.items
                .filter((item) => (item.status === 'completed' || item.status === 'duplicate') && item.asset_tag)
                .map((item) => item.tag_number)
              if (tagNumbers.length > 0) void writeConsolidatedCopy(dirForThisBatch, fresh.reference, tagNumbers)
            }
            // A Batch Process run gets the "File Extraction Completed" summary
            // popup instead of a toast — everything else (normal upload,
            // reopening a batch from History) keeps the existing toast.
            if (batchProcessRunRef.current === fresh.id) {
              batchProcessRunRef.current = null
              setBatchProcessSummary({
                total: fresh.items.length,
                completed: fresh.items.length - failures,
                failed: failures,
              })
            } else if (failures === 0) toast.success('Extraction complete.')
            else if (failures === fresh.items.length) toast.error('Extraction failed for every tag.')
            else toast.warn(`Extraction finished with ${failures} failed tag(s).`)
          }
        } catch {
          stopPolling()
        }
      }, POLL_MS)
    },
    [stopPolling, toast, writeAiExtractionCopy, writeConsolidatedCopy, writeDragDropAutoSave],
  )

  /** Re-run extraction for one failed tag only — the rest of the batch is untouched. */
  const retryTag = async (itemId: number) => {
    if (!batch) return
    setRetryingIds((prev) => new Set(prev).add(itemId))
    try {
      await api.retryItem(batch.id, itemId)
      startPolling(batch.id)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not retry that tag.')
      setRetryingIds((prev) => {
        const next = new Set(prev)
        next.delete(itemId)
        return next
      })
    }
  }

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
        // Already-resolved items belong to a past session — mark them seen
        // so re-opening this batch from History doesn't re-trigger a push.
        fetched.items.forEach((item) => {
          if ((item.status === 'completed' || item.status === 'duplicate') && item.asset_tag) {
            autoSavedRef.current.add(item.id)
          }
        })
        if (!TERMINAL.has(fetched.status)) startPolling(fetched.id)
      })
      .catch(() => { if (!cancelled) toast.error('Could not load that batch.') })
      .finally(() => !cancelled && setLoadingBatch(false))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchIdParam])

  // Bare /batch, landed on normally (not via "New Batch"): default to the
  // most recent extraction so it survives navigating away and back.
  useEffect(() => {
    if (batchIdParam || cameFresh) return
    let cancelled = false
    setLoadingBatch(true)
    api
      .listBatches(1)
      .then((latest) => {
        if (cancelled) return
        if (latest.length > 0) navigate(`/batch/${latest[0].id}`, { replace: true })
      })
      .catch(() => undefined)
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
      // Move the URL to this batch's own address so it's what "New Batch"
      // shows by default on the next visit — not just held in local state.
      navigate(`/batch/${response.batch.id}`, { replace: true })
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  /** One-time folder pick for the drag-and-drop auto-save above — a browser
   * can't silently write to an arbitrary path like C:\Asset photo data
   * capturing tool without this explicit, user-driven grant (the same
   * constraint Batch Process's own folder pick already works within). Once
   * granted, every tag this page extracts from here on writes there
   * automatically with no further prompts, for the rest of the session. */
  const chooseDragDropFolder = async () => {
    if (!isFolderAccessSupported()) {
      toast.error('Auto-save needs a Chromium browser (Chrome or Edge) to open a local folder.')
      return
    }
    try {
      const dir = await pickBatchProcessFolder()
      dragDropDirRef.current = dir
      dragDropSaveWarnedRef.current = false
      setDragDropDirName(dir.name)
      toast.success(`Auto-saving extracted workbooks into "${dir.name}".`)
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      toast.error(caught instanceof Error ? caught.message : 'Could not set the auto-save folder.')
    }
  }

  /** Let the user pick a local folder, scan it right here in the browser for
   * tag subfolders/files, and extract every tag found through the same
   * pipeline a normal upload uses. Reading (and, once extraction lands,
   * writing the AI Extraction / Consolidate file outputs back) happens
   * entirely client-side via the File System Access API — see
   * utils/folderAccess.ts — so this works the same whether the backend is
   * running locally or on a remote deployment. Stays on this page (no
   * navigation) so the whole run is watched right here, same as a normal
   * upload's progress already is. */
  const runBatchProcess = async () => {
    if (!isFolderAccessSupported()) {
      toast.error('Batch Process needs a Chromium browser (Chrome or Edge) to open a local folder.')
      return
    }

    setBatchProcessing(true)
    setBatchProcessSummary(null)
    try {
      const dir = await pickBatchProcessFolder()
      const staged = await scanTagFolders(dir)
      if (staged.length === 0) {
        toast.error('No tag folders with images were found in that folder.')
        return
      }

      writeBackWarnedRef.current = false
      const response = await api.batchProcess(staged)
      batchProcessRunRef.current = response.batch.id
      batchProcessDirRef.current = { dir, batchId: response.batch.id }
      setBatch(response.batch)
      setRejected(response.rejected)
      setFiles([])

      if (response.rejected.length > 0) {
        toast.warn(`${response.rejected.length} file(s) couldn't be read and were skipped.`)
      }
      toast.success(
        `Batch Process started — extracting ${response.batch.total_tags} tag${response.batch.total_tags === 1 ? '' : 's'}…`,
      )
      startPolling(response.batch.id)
    } catch (caught) {
      // The user closing the folder picker without choosing anything is not
      // an error worth surfacing.
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      toast.error(caught instanceof Error ? caught.message : 'Could not start Batch Process.')
    } finally {
      setBatchProcessing(false)
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
      const updated = await api.saveTag(tag.id, payload)
      await refreshBatch()
      toast.success(`Saved ${tag.tag_number}. Both workbooks have been rebuilt.`)
      void pushTemplateRevision(updated)
      // Which picked folder (if any) this tag belongs to determines what
      // gets revisioned — a Batch Process batch only ever revisions its one
      // consolidated file; a drag-and-drop batch revisions this tag's own
      // Template Output. Neither applies if no folder was ever picked for
      // this session (pushTemplateRevision above is unaffected either way).
      const dirState = batchProcessDirRef.current
      if (batch && dirState && dirState.batchId === batch.id) {
        void writeConsolidatedRevision(dirState.dir, batch)
      } else if (dragDropDirRef.current) {
        void writeDragDropTemplateRevision(dragDropDirRef.current, updated)
      }
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
    batchProcessRunRef.current = null
    batchProcessDirRef.current = null
    setBatchProcessSummary(null)
    navigate('/batch', { replace: true, state: { fresh: true } })
  }

  const busy = batch !== null && !TERMINAL.has(batch.status)

  // Tags that have reached a per-item terminal state (finished either way),
  // e.g. "10/50 completed" — same idea as the progress ring, just as a count.
  const finishedCount = batch
    ? batch.items.filter((item) => item.status === 'completed' || item.status === 'failed' || item.status === 'duplicate').length
    : 0

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
        <div className="row gap-12 wrap">
          {batch && <span className="chip chip-neutral">{batch.reference}</span>}
          <button
            type="button"
            className="btn btn-primary"
            onClick={runBatchProcess}
            disabled={batchProcessing}
            title="Pick a local folder and extract every tag folder inside it"
          >
            {batchProcessing ? <Spinner size={14} /> : null}
            {batchProcessing ? 'Scanning…' : 'Batch Process'}
          </button>
          <button type="button" className="btn btn-primary" onClick={startOver}>
            New Batch
          </button>
        </div>
      </header>

      {loadingBatch && (
        <div className="card"><Spinner size={22} label="Loading batch…" /></div>
      )}

      {!batch && !viewingExisting && !loadingBatch && (
        <section className="card stack gap-16">
          <Dropzone ref={dropzoneRef} files={files} onChange={setFiles} disabled={uploading} />
          <div className="row gap-12 wrap" style={{ alignItems: 'center' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={chooseDragDropFolder}>
              {dragDropDirName ? `Auto-save folder: ${dragDropDirName} (change)` : 'Choose Auto-Save Folder'}
            </button>
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
              {finishedCount}/{batch.total_tags} tag{batch.total_tags === 1 ? '' : 's'} completed ·{' '}
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
                    {' • '}
                    {formatFileSize(item.images.reduce((sum, image) => sum + image.size_bytes, 0))}
                  </span>
                  {item.status === 'failed'
                    && !(item.error_message ?? '').startsWith('Excel generation failed') && (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => retryTag(item.id)}
                      disabled={retryingIds.has(item.id)}
                    >
                      {retryingIds.has(item.id) ? <Spinner size={14} /> : null}
                      {retryingIds.has(item.id) ? 'Re-Extracting…' : 'Re-Extract'}
                    </button>
                  )}
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
                        onViewPhoto={() => { setViewingBatchId(batch.id); setViewingItemId(item.id) }}
                      />
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <BatchImagesModal
        batchId={viewingBatchId}
        itemId={viewingItemId}
        onClose={() => { setViewingBatchId(null); setViewingItemId(null) }}
      />

      <Modal
        open={batchProcessSummary !== null}
        title="File Extraction Completed"
        onClose={() => setBatchProcessSummary(null)}
        footer={
          <button type="button" className="btn btn-primary" onClick={() => setBatchProcessSummary(null)}>
            Close
          </button>
        }
      >
        {batchProcessSummary && (
          <div className="stack gap-8">
            <p>Total Tags: {batchProcessSummary.total}</p>
            <p>Completed: {batchProcessSummary.completed}</p>
            <p>Failed: {batchProcessSummary.failed}</p>
            {batchProcessSummary.failed > 0 && (
              <p className="muted">Please use the &quot;Re-extract&quot; button for the failed tags.</p>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
