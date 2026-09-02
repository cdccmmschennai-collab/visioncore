import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import BatchImagesModal from '@/components/BatchImagesModal'
import EditableTable from '@/components/EditableTable'
import Modal from '@/components/Modal'
import Pagination from '@/components/Pagination'
import SearchInput from '@/components/SearchInput'
import Spinner from '@/components/Spinner'
import { api } from '@/api/client'
import type { AssetTag, ExtractionPayload, HistoryRow } from '@/api/types'
import { formatDateTime } from '@/utils/filename'
import { useAuth } from '@/store/AuthContext'
import { useToast } from '@/store/ToastContext'

const PAGE_SIZE = 12

const STATUS_CLASS: Record<string, string> = {
  Completed: 'chip-confirmed',
  Saved: 'chip-info',
  Downloaded: 'chip-neutral',
  Uploaded: 'chip-orange',
  Duplicate: 'chip-verify',
}

const STATUS_FILTERS: { label: string; action: string }[] = [
  { label: 'Downloaded', action: 'download' },
  { label: 'Completed', action: 'extract' },
  { label: 'Duplicate', action: 'duplicate_blocked' },
  { label: 'Uploaded', action: 'upload' },
]

export default function History() {
  const { isAdmin } = useAuth()
  const toast = useToast()
  const [params, setParams] = useSearchParams()

  const [search, setSearch] = useState(params.get('tag') ?? '')
  const [debounced, setDebounced] = useState(search)
  const [mineOnly, setMineOnly] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [rows, setRows] = useState<HistoryRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const [selected, setSelected] = useState<AssetTag | null>(null)
  const [loadingTag, setLoadingTag] = useState(false)
  const [viewingBatchId, setViewingBatchId] = useState<number | null>(null)
  const [viewingItemId, setViewingItemId] = useState<number | null>(null)

  // Checkbox-driven download selection. `allSelected` and individual tags are
  // mutually exclusive — checking All clears individual picks (and disables
  // their checkboxes, since "all" spans every completed tag, not just what's
  // on this page); picking a tag only ever applies while All is unchecked.
  const [allSelected, setAllSelected] = useState(false)
  const [selectedTagNumbers, setSelectedTagNumbers] = useState<Set<string>>(new Set())

  // Debounce so a fast typist doesn't fire a request per keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebounced(search)
      setPage(1)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api.history({
        search: debounced, action: statusFilter, mineOnly, page, pageSize: PAGE_SIZE,
      })
      setRows(result.items)
      setTotal(result.total)
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Could not load history.')
    } finally {
      setLoading(false)
    }
  }, [debounced, statusFilter, mineOnly, page, toast])

  useEffect(() => { void load() }, [load])

  // Deep link from Home: /history?tag=12-4020-BV-0074 opens that record.
  useEffect(() => {
    const tagParam = params.get('tag')
    if (!tagParam) return
    setLoadingTag(true)
    api
      .getTagByNumber(tagParam)
      .then(setSelected)
      .catch(() => toast.error(`No saved record for ${tagParam}.`))
      .finally(() => {
        setLoadingTag(false)
        params.delete('tag')
        setParams(params, { replace: true })
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
      void load()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Download failed.')
    }
  }

  const [downloadingAll, setDownloadingAll] = useState(false)
  const downloadAll = async () => {
    setDownloadingAll(true)
    try {
      const name = await api.downloadAllTemplates()
      toast.success(`Downloaded ${name}`)
      void load()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Download failed.')
    } finally {
      setDownloadingAll(false)
    }
  }

  const toggleTag = (tagNumber: string) => {
    setSelectedTagNumbers((prev) => {
      const next = new Set(prev)
      if (next.has(tagNumber)) next.delete(tagNumber)
      else next.add(tagNumber)
      return next
    })
  }

  const toggleAll = (checked: boolean) => {
    setAllSelected(checked)
    if (checked) setSelectedTagNumbers(new Set())
  }

  const [downloadingSelected, setDownloadingSelected] = useState(false)
  const downloadSelected = async () => {
    if (!allSelected && selectedTagNumbers.size === 0) {
      toast.warn('Select at least one completed tag, or check All, before downloading.')
      return
    }
    setDownloadingSelected(true)
    try {
      const name = allSelected
        ? await api.downloadAllTemplates()
        : await api.downloadSelectedTemplates([...selectedTagNumbers])
      toast.success(`Downloaded ${name}`)
      void load()
    } catch (caught) {
      toast.error(caught instanceof Error ? caught.message : 'Download failed.')
    } finally {
      setDownloadingSelected(false)
    }
  }

  return (
    <div className="page stack gap-24">
      <header className="page-head">
        <div className="stack gap-4">
          <span className="eyebrow">Audit trail</span>
          <h1>History</h1>
        </div>
        <div className="row gap-12 wrap">
          {isAdmin && (
            <label className="checkbox">
              <input
                type="checkbox"
                checked={mineOnly}
                onChange={(event) => { setMineOnly(event.target.checked); setPage(1) }}
              />
              Only my activity
            </label>
          )}
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search tag number or description"
          />
          <button
            type="button"
            className="btn btn-sm"
            disabled={downloadingSelected}
            onClick={() => void downloadSelected()}
          >
            {downloadingSelected ? 'Downloading…' : 'Download Selected (Template)'}
          </button>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={downloadingAll}
            onClick={() => void downloadAll()}
          >
            {downloadingAll ? 'Downloading…' : 'Download All (Template)'}
          </button>
        </div>
      </header>

      {loading ? (
        <div className="card"><Spinner size={22} label="Loading history…" /></div>
      ) : rows.length === 0 ? (
        <div className="card empty">
          <h3>Nothing here yet</h3>
          <p>
            {debounced
              ? `No activity matches "${debounced}".`
              : 'Upload a batch and its activity will appear here.'}
          </p>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th style={{ width: 32 }}>
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={(event) => toggleAll(event.target.checked)}
                      aria-label="Select all completed tags"
                      title="Select all completed tags"
                    />
                  </th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Tag Number</th>
                  <th>Description</th>
                  <th>
                    <div className="row gap-8" style={{ alignItems: 'center' }}>
                      Status
                      <select
                        className="select"
                        style={{ padding: '2px 6px', fontSize: 12 }}
                        value={statusFilter}
                        onChange={(event) => { setStatusFilter(event.target.value); setPage(1) }}
                      >
                        <option value="">All</option>
                        {STATUS_FILTERS.map((filter) => (
                          <option key={filter.action} value={filter.action}>{filter.label}</option>
                        ))}
                      </select>
                    </div>
                  </th>
                  <th>User</th>
                  <th style={{ width: 120 }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const { date, time } = formatDateTime(row.date)
                  const openable = Boolean(row.can_download && row.asset_tag_id)
                  return (
                    <tr
                      key={row.id}
                      className={openable ? 'row-clickable' : undefined}
                      onClick={openable ? () => openTag(row.asset_tag_id!) : undefined}
                    >
                      <td onClick={(event) => event.stopPropagation()}>
                        {row.action === 'extract' && row.tag_number && (
                          <input
                            type="checkbox"
                            checked={allSelected || selectedTagNumbers.has(row.tag_number)}
                            disabled={allSelected}
                            onChange={() => toggleTag(row.tag_number!)}
                            aria-label={`Select ${row.tag_number}`}
                          />
                        )}
                      </td>
                      <td className="nowrap">{date}</td>
                      <td className="nowrap muted">{time}</td>
                      <td>
                        {row.tag_number
                          ? <span className="tag-code">{row.tag_number}</span>
                          : <span className="muted">—</span>}
                      </td>
                      <td>{row.description ?? <span className="muted">{row.detail ?? '—'}</span>}</td>
                      <td>
                        <span className={`chip ${STATUS_CLASS[row.status] ?? 'chip-neutral'}`}>
                          {row.status}
                        </span>
                      </td>
                      <td className="muted">{row.username ?? '—'}</td>
                      <td>
                        {row.batch_id ? (
                          <button
                            type="button"
                            className="btn btn-sm btn-accent"
                            onClick={(event) => {
                              event.stopPropagation()
                              setViewingBatchId(row.batch_id)
                              setViewingItemId(row.batch_item_id)
                            }}
                          >
                            View photos
                          </button>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </>
      )}

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
    </div>
  )
}
