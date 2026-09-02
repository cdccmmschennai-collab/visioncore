import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import EditableTable from '@/components/EditableTable'
import Spinner from '@/components/Spinner'
import { ApiError, api } from '@/api/client'
import type { AssetTag, ExtractionPayload } from '@/api/types'
import { pushTemplateRevision } from '@/services/localHelper'
import { useToast } from '@/store/ToastContext'

/** Opening a single saved tag from Home or History. */
export default function TagDetail() {
  const { tagId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [tag, setTag] = useState<AssetTag | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .getTag(Number(tagId))
      .then((result) => !cancelled && setTag(result))
      .catch((caught) =>
        !cancelled &&
        setError(caught instanceof ApiError ? caught.message : 'Could not load that tag.'))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [tagId])

  const save = useCallback(
    async (payload: ExtractionPayload) => {
      if (!tag) return
      try {
        const updated = await api.saveTag(tag.id, payload)
        setTag(updated)
        toast.success(`Saved ${updated.tag_number}. Both workbooks were rebuilt.`)
        void pushTemplateRevision(updated)
      } catch (caught) {
        toast.error(caught instanceof ApiError ? caught.message : 'Could not save those changes.')
        throw caught
      }
    },
    [tag, toast],
  )

  const download = useCallback(
    async (kind: 'ai' | 'template') => {
      if (!tag) return
      try {
        const name = kind === 'ai' ? await api.downloadAi(tag) : await api.downloadTemplate(tag)
        toast.success(`Downloaded ${name}`)
      } catch (caught) {
        toast.error(
          caught instanceof ApiError ? caught.message : 'Could not download that workbook.')
      }
    },
    [tag, toast],
  )

  return (
    <div className="page">
      <div className="page-head">
        <div className="stack gap-4">
          <button type="button" className="btn btn-ghost btn-sm back-link" onClick={() => navigate(-1)}>
            ← Back
          </button>
          <h1>Tag Detail</h1>
        </div>
      </div>

      {loading && <div className="card"><Spinner size={22} label="Loading tag…" /></div>}
      {error && <div className="alert alert-error">{error}</div>}

      {tag && (
        <EditableTable
          tag={tag}
          onSave={save}
          onDownloadAi={() => download('ai')}
          onDownloadTemplate={() => download('template')}
        />
      )}
    </div>
  )
}
