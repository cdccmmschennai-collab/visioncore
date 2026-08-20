import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Modal from '@/components/Modal'
import Pagination from '@/components/Pagination'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import type { AssetTag, Batch, BatchStatus, ExtractedImage, ItemStatus } from '@/api/types'
import { formatDateTime, formatNumber } from '@/utils/filename'

const DRILLDOWN_PAGE_SIZE = 10

const BATCH_STATUS_CLASS: Record<BatchStatus, string> = {
  completed: 'chip-confirmed',
  processing: 'chip-info',
  uploaded: 'chip-info',
  partial: 'chip-verify',
  failed: 'chip-danger',
}

const BATCH_STATUS_LABEL: Record<BatchStatus, string> = {
  completed: 'Completed',
  processing: 'Processing',
  uploaded: 'Processing',
  partial: 'Partial',
  failed: 'Failed',
}

const ITEM_STATUS_CLASS: Record<ItemStatus, string> = {
  completed: 'chip-confirmed',
  extracting: 'chip-info',
  processing: 'chip-info',
  uploaded: 'chip-info',
  duplicate: 'chip-verify',
  failed: 'chip-danger',
}

const ITEM_STATUS_LABEL: Record<ItemStatus, string> = {
  completed: 'Completed',
  extracting: 'Extracting',
  processing: 'Processing',
  uploaded: 'Uploaded',
  duplicate: 'Duplicate',
  failed: 'Failed',
}

export default function Home() {
  const navigate = useNavigate()

  const [recentTags, setRecentTags] = useState<AssetTag[]>([])
  const [batches, setBatches] = useState<Batch[]>([])
  const [imagesTotal, setImagesTotal] = useState(0)
  const [completedTotal, setCompletedTotal] = useState(0)
  const [failedTotal, setFailedTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  // Completed/Failed Batch drill-down modal, opened from the KPI cards below.
  const [drilldown, setDrilldown] = useState<'completed' | 'failed' | null>(null)
  const [drilldownPage, setDrilldownPage] = useState(1)
  const [drilldownBatches, setDrilldownBatches] = useState<Batch[]>([])
  const [drilldownTotal, setDrilldownTotal] = useState(0)
  const [drilldownLoading, setDrilldownLoading] = useState(false)

  const openDrilldown = (kind: 'completed' | 'failed') => {
    setDrilldown(kind)
    setDrilldownPage(1)
  }

  useEffect(() => {
    if (!drilldown) return
    let cancelled = false
    setDrilldownLoading(true)
    api
      .listBatchesByStatus(drilldown, drilldownPage, DRILLDOWN_PAGE_SIZE)
      .then((result) => {
        if (cancelled) return
        setDrilldownBatches(result.items)
        setDrilldownTotal(result.total)
      })
      .catch(() => undefined)
      .finally(() => !cancelled && setDrilldownLoading(false))
    return () => { cancelled = true }
  }, [drilldown, drilldownPage])

  // Total Images Extracted drill-down modal.
  const [imagesOpen, setImagesOpen] = useState(false)
  const [imagesPage, setImagesPage] = useState(1)
  const [images, setImages] = useState<ExtractedImage[]>([])
  const [imagesLoading, setImagesLoading] = useState(false)

  const openImages = () => {
    setImagesOpen(true)
    setImagesPage(1)
  }

  useEffect(() => {
    if (!imagesOpen) return
    let cancelled = false
    setImagesLoading(true)
    api
      .listExtractedImages(imagesPage, DRILLDOWN_PAGE_SIZE)
      .then((result) => {
        if (cancelled) return
        setImages(result.items)
        setImagesTotal(result.total)
      })
      .catch(() => undefined)
      .finally(() => !cancelled && setImagesLoading(false))
    return () => { cancelled = true }
  }, [imagesOpen, imagesPage])

  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.listTags('', 1, 6),
      api.listBatches(100),
      // page_size=1: only the accurate DB total is needed here, not the rows.
      api.listBatchesByStatus('completed', 1, 1),
      api.listBatchesByStatus('failed', 1, 1),
      api.listExtractedImages(1, 1),
    ])
      .then(([tagsPage, batchList, completedPage, failedPage, imagesPage]) => {
        if (cancelled) return
        setRecentTags(tagsPage.items)
        setBatches(batchList)
        setCompletedTotal(completedPage.total)
        setFailedTotal(failedPage.total)
        setImagesTotal(imagesPage.total)
      })
      .catch(() => undefined)
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  const recentBatches = batches.slice(0, 6)

  const kpis: { label: string; value: number; tone: string; onClick?: () => void }[] = [
    { label: 'Total Image Extracted', value: imagesTotal, tone: 'info', onClick: openImages },
    { label: 'Completed Batches', value: completedTotal, tone: 'confirmed', onClick: () => openDrilldown('completed') },
    { label: 'Failed Batches', value: failedTotal, tone: 'danger', onClick: () => openDrilldown('failed') },
  ]

  return (
    <div className="page stack gap-24">
      <header className="page-head">
        <div className="stack gap-4">
          
          <h3>Workbook jobs</h3>
          <p>Upload and manage equipment specification workbooks.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/batch')}>
          + New Batch
        </button>
      </header>

      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className={`card kpi-card kpi-card-${kpi.tone}${kpi.onClick ? ' row-clickable' : ''}`}
            onClick={kpi.onClick}
            role={kpi.onClick ? 'button' : undefined}
            tabIndex={kpi.onClick ? 0 : undefined}
            onKeyDown={
              kpi.onClick
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      kpi.onClick?.()
                    }
                  }
                : undefined
            }
          >
            <div className="stack gap-4">
              <span className="kpi-value">{loading ? '—' : formatNumber(kpi.value)}</span>
              <span className="kpi-label">{kpi.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid-cards">
        {/* ── Recent batches ───────────────────────────────────────────── */}
        <section className="card stack gap-16">
          <div className="row gap-12">
            <h3>Recent Batches</h3>
            <span className="spacer" />
            <Link to="/batch" className="btn btn-ghost btn-sm">New batch</Link>
          </div>

          {loading ? (
            <Spinner size={20} label="Loading batches…" />
          ) : recentBatches.length === 0 ? (
            <div className="empty">
              <p className="muted">No batches uploaded yet.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Tags</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {recentBatches.map((batch) => {
                    const { date } = formatDateTime(batch.created_at)
                    return (
                      <tr
                        key={batch.id}
                        className="row-clickable"
                        onClick={() => navigate(`/batch/${batch.id}`)}
                      >
                        <td><span className="tag-code">{batch.reference}</span></td>
                        <td className="muted">{batch.total_tags}</td>
                        <td>
                          <span className={`chip ${BATCH_STATUS_CLASS[batch.status]}`}>
                            {BATCH_STATUS_LABEL[batch.status]}
                          </span>
                        </td>
                        <td className="muted nowrap">{date}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* ── Recently extracted tags ──────────────────────────────────── */}
        <section className="card stack gap-16">
          <div className="row gap-12">
            <h3>Recently Extracted Tags</h3>
            <span className="spacer" />
            <Link to="/history" className="btn btn-ghost btn-sm btn-accent">View all</Link>
          </div>

          {loading ? (
            <Spinner size={20} label="Loading recent tags…" />
          ) : recentTags.length === 0 ? (
            <div className="empty">
              <p className="muted">Upload your first batch of nameplate photos to get started.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Tag Number</th>
                    <th>Description</th>
                    <th>Last updated</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTags.map((tag) => {
                    const { date } = formatDateTime(tag.updated_at)
                    return (
                      <tr
                        key={tag.id}
                        className="row-clickable"
                        onClick={() => navigate(`/history?tag=${encodeURIComponent(tag.tag_number)}`)}
                      >
                        <td><span className="tag-code">{tag.tag_number}</span></td>
                        <td>{tag.description}</td>
                        <td className="muted nowrap">{date}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <Modal
        open={drilldown !== null}
        title={drilldown === 'completed' ? 'Completed Batches' : 'Failed Batches'}
        onClose={() => setDrilldown(null)}
        width={720}
      >
        {drilldownLoading ? (
          <Spinner size={20} label="Loading batches…" />
        ) : drilldownBatches.length === 0 ? (
          <div className="empty">
            <p className="muted">No batches to show.</p>
          </div>
        ) : (
          <div className="stack gap-12">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Tags</th>
                    <th>Images</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {drilldownBatches.map((batch) => {
                    const { date } = formatDateTime(batch.created_at)
                    return (
                      <tr
                        key={batch.id}
                        className="row-clickable"
                        onClick={() => { setDrilldown(null); navigate(`/batch/${batch.id}`) }}
                      >
                        <td><span className="tag-code">{batch.reference}</span></td>
                        <td className="muted">{batch.total_tags}</td>
                        <td className="muted">{batch.total_images}</td>
                        <td>
                          <span className={`chip ${BATCH_STATUS_CLASS[batch.status]}`}>
                            {BATCH_STATUS_LABEL[batch.status]}
                          </span>
                        </td>
                        <td className="muted nowrap">{date}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <Pagination
              page={drilldownPage}
              pageSize={DRILLDOWN_PAGE_SIZE}
              total={drilldownTotal}
              onChange={setDrilldownPage}
            />
          </div>
        )}
      </Modal>

      <Modal
        open={imagesOpen}
        title="Total Images Extracted"
        onClose={() => setImagesOpen(false)}
        width={780}
      >
        {imagesLoading ? (
          <Spinner size={20} label="Loading images…" />
        ) : images.length === 0 ? (
          <div className="empty">
            <p className="muted">No images to show.</p>
          </div>
        ) : (
          <div className="stack gap-12">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Image</th>
                    <th>Tag Number</th>
                    <th>Batch</th>
                    <th>Status</th>
                    <th>Extracted</th>
                  </tr>
                </thead>
                <tbody>
                  {images.map((image) => {
                    const { date } = formatDateTime(image.created_at)
                    return (
                      <tr key={image.id}>
                        <td>{image.original_filename}</td>
                        <td><span className="tag-code">{image.tag_number}</span></td>
                        <td className="muted">{image.batch_reference}</td>
                        <td>
                          <span className={`chip ${ITEM_STATUS_CLASS[image.status]}`}>
                            {ITEM_STATUS_LABEL[image.status]}
                          </span>
                        </td>
                        <td className="muted nowrap">{date}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <Pagination
              page={imagesPage}
              pageSize={DRILLDOWN_PAGE_SIZE}
              total={imagesTotal}
              onChange={setImagesPage}
            />
          </div>
        )}
      </Modal>
    </div>
  )
}
