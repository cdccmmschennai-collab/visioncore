import { useCallback, useEffect, useState } from 'react'
import BatchImagesModal from '@/components/BatchImagesModal'
import EditableTable from '@/components/EditableTable'
import Modal from '@/components/Modal'
import Pagination from '@/components/Pagination'
import QualityChip from '@/components/QualityChip'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import { FIELD_ORDER, NOT_PRESENT, SEARCH_FIELDS } from '@/api/types'
import type { AssetTag, ExtractionPayload, SearchResult } from '@/api/types'
import { useToast } from '@/store/ToastContext'

const PAGE_SIZE = 12

interface Query {
  field: string
  value: string
}

export default function Search() {
  const toast = useToast()

  const [field, setField] = useState(SEARCH_FIELDS[0].value)
  const [value, setValue] = useState('')
  const [query, setQuery] = useState<Query | null>(null)
  const [page, setPage] = useState(1)

  const [rows, setRows] = useState<SearchResult[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const [selected, setSelected] = useState<AssetTag | null>(null)
  const [loadingTag, setLoadingTag] = useState(false)
  const [viewingBatchId, setViewingBatchId] = useState<number | null>(null)
  const [viewingItemId, setViewingItemId] = useState<number | null>(null)
  const [payloadView, setPayloadView] = useState<
    { title: string; payload: ExtractionPayload; variant: 'ai' | 'final' } | null
  >(null)

  const load = useCallback(async () => {
    if (!query) return
    setLoading(true)
    try {
      const result = await api.searchTags({
        field: query.field, value: query.value, page, pageSize: PAGE_SIZE,
      })
      setRows(result.items)
      setTotal(result.total)
    } catch (caught) {
      setRows([])
      setTotal(0)
      toast.error(caught instanceof Error ? caught.message : 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [query, page, toast])

  useEffect(() => { void load() }, [load])

  const runSearch = () => {
    setSearched(true)
    setPage(1)
    setQuery({ field, value: value.trim() })
  }

  const openTag = async (tagId: number) => {
    setLoadingTag(true)
    try {
      setSelected(await api.getTag(tagId))
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not open that tag.')
    } finally {
      setLoadingTag(false)
    }
  }

  const saveTag = async (tag: AssetTag, payload: ExtractionPayload) => {
    const updated = await api.saveTag(tag.id, payload)
    setSelected(updated)
    toast.success(`Saved ${tag.tag_number}. Both workbooks have been rebuilt.`)
    void load()
  }

  const download = async (tag: AssetTag, kind: 'ai' | 'template') => {
    try {
      const name = await (kind === 'ai' ? api.downloadAi(tag) : api.downloadTemplate(tag))
      toast.success(`Downloaded ${name}`)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Download failed.')
    }
  }

  return (
    <div className="page stack gap-24">
      <header className="page-head">
        <div className="stack gap-4">
          <span className="eyebrow">Find a record</span>
          <h1>Search</h1>
        </div>
      </header>

      <div className="card">
        <div className="search-form">
          <select
            className="select"
            value={field}
            onChange={(event) => setField(event.target.value)}
            aria-label="Search field"
          >
            {SEARCH_FIELDS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <input
            type="text"
            className="input"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') runSearch() }}
            placeholder="Enter a value — use * as a wildcard, e.g. 12* or *12*"
            aria-label="Search value"
          />
          <button type="button" className="btn btn-primary" onClick={runSearch} disabled={loading}>
            {loading ? <Spinner size={14} /> : null}
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </div>

      <div className="stack gap-12">
        <h3 style={{ margin: 0 }}>Search Results</h3>

        {!searched ? (
          <div className="card empty">
            <h3>Nothing searched yet</h3>
            <p>Pick a field, enter a value, and click Search. Use * for a wildcard — 12* matches tag numbers starting with 12, *12* matches anywhere.</p>
          </div>
        ) : loading ? (
          <div className="card"><Spinner size={22} label="Searching…" /></div>
        ) : rows.length === 0 ? (
          <div className="card empty">
            <h3>No matches</h3>
            <p>No records found for {query?.field.toLowerCase()} matching &quot;{query?.value || '*'}&quot;.</p>
          </div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Tag Number</th>
                    <th>Description</th>
                    <th>AI Extraction</th>
                    <th>Manual Review</th>
                    <th>User</th>
                    <th style={{ width: 110 }}>View Details</th>
                    <th style={{ width: 110 }}>View Photo</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td><span className="tag-code">{row.tag_number}</span></td>
                      <td>{row.description}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => setPayloadView({
                            title: `${row.tag_number} — AI Extraction`,
                            payload: row.ai_payload,
                            variant: 'ai',
                          })}
                        >
                          View
                        </button>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => setPayloadView({
                            title: `${row.tag_number} — Manual Review`,
                            payload: row.final_payload,
                            variant: 'final',
                          })}
                        >
                          View
                        </button>
                      </td>
                      <td className="muted">{row.username ?? '—'}</td>
                      <td>
                        <button type="button" className="btn btn-sm btn-primary" onClick={() => openTag(row.id)}>
                          View
                        </button>
                      </td>
                      <td>
                        {row.batch_id ? (
                          <button
                            type="button"
                            className="btn btn-sm btn-accent"
                            onClick={() => { setViewingBatchId(row.batch_id); setViewingItemId(row.batch_item_id) }}
                          >
                            View Photo
                          </button>
                        ) : (
                          <span className="muted">No Photo Available</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </>
        )}
      </div>

      <Modal
        open={selected !== null || loadingTag}
        title={selected ? `${selected.tag_number} — ${selected.description}` : 'Loading…'}
        titleExtra={selected && (
          <span className="modal-user-badge">{selected.username || 'Unknown'}</span>
        )}
        onClose={() => setSelected(null)}
        width={980}
      >
        {loadingTag && !selected ? (
          <Spinner size={22} label="Loading tag…" />
        ) : selected ? (
          <EditableTable
            tag={selected}
            onSave={(payload) => saveTag(selected, payload)}
            onDownloadAi={() => download(selected, 'ai')}
            onDownloadTemplate={() => download(selected, 'template')}
          />
        ) : null}
      </Modal>

      <BatchImagesModal
        batchId={viewingBatchId}
        itemId={viewingItemId}
        onClose={() => { setViewingBatchId(null); setViewingItemId(null) }}
      />

      <Modal
        open={payloadView !== null}
        title={payloadView?.title ?? ''}
        onClose={() => setPayloadView(null)}
        width={640}
      >
        {payloadView && (
          <div className="table-wrap">
            <table className="data result-table">
              <thead>
                <tr>
                  <th style={{ width: '38%' }}>Field</th>
                  <th>Value</th>
                  {payloadView.variant === 'final' && <th style={{ width: 148 }}>Data Quality</th>}
                </tr>
              </thead>
              <tbody>
                {FIELD_ORDER.map(({ key, label }) => {
                  const field = payloadView.payload.fields?.[key]
                  const value = field?.value ?? ''
                  const isMissing = value === NOT_PRESENT
                  return (
                    <tr key={key}>
                      <th scope="row" className="field-label">{label}</th>
                      <td>
                        <span className={`field-value${isMissing ? ' field-missing' : ''}`}>
                          {value || '—'}
                        </span>
                      </td>
                      {payloadView.variant === 'final' && (
                        <td><QualityChip quality={field?.quality ?? 'Verify'} missing={isMissing} /></td>
                      )}
                    </tr>
                  )
                })}

                {payloadView.variant === 'final' && (
                  <>
                    <tr>
                      <th scope="row" className="field-label">Remarks</th>
                      <td colSpan={2}>
                        <span className="field-value">{payloadView.payload.remarks || '—'}</span>
                      </td>
                    </tr>
                    <tr>
                      <th scope="row" className="field-label">Photo Status</th>
                      <td colSpan={2}>
                        <span className="field-value">{payloadView.payload.photo_status || '—'}</span>
                      </td>
                    </tr>
                    <tr>
                      <th scope="row" className="field-label">QC Comment</th>
                      <td colSpan={2}>
                        <span className="field-value">{payloadView.payload.qc_comment || '—'}</span>
                      </td>
                    </tr>
                  </>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Modal>
    </div>
  )
}
