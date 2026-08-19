import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import type { AssetTag, Batch, BatchStatus } from '@/api/types'
import { formatDateTime, formatNumber } from '@/utils/filename'

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

export default function Home() {
  const navigate = useNavigate()

  const [tagsTotal, setTagsTotal] = useState(0)
  const [recentTags, setRecentTags] = useState<AssetTag[]>([])
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.listTags('', 1, 6),
      api.listBatches(100),
    ])
      .then(([tagsPage, batchList]) => {
        if (cancelled) return
        setTagsTotal(tagsPage.total)
        setRecentTags(tagsPage.items)
        setBatches(batchList)
      })
      .catch(() => undefined)
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  const completedBatches = batches.filter((b) => b.status === 'completed').length
  const failedBatches = batches.filter((b) => b.status === 'failed' || b.status === 'partial').length
  const recentBatches = batches.slice(0, 6)

  const kpis = [
    { label: 'Total Image Extracted', value: tagsTotal, tone: 'info' },
    { label: 'Completed Batches', value: completedBatches, tone: 'confirmed' },
    { label: 'Failed Batches', value: failedBatches, tone: 'danger' },
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
          <div key={kpi.label} className={`card kpi-card kpi-card-${kpi.tone}`}>
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
    </div>
  )
}
