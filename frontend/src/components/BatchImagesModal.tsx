import { useEffect, useState } from 'react'
import Modal from './Modal'
import Spinner from './Spinner'
import { api } from '@/api/client'
import { useToast } from '@/store/ToastContext'

interface Photo {
  id: number
  original_filename: string
  url: string
}

interface TagGroup {
  tagNumber: string
  description: string
  photos: Photo[]
}

interface Props {
  batchId: number | null
  /** When set, show only this tag's photos instead of the whole batch. */
  itemId?: number | null
  onClose: () => void
}

/** The raw input photos a batch was uploaded with — opened from its History row. */
export default function BatchImagesModal({ batchId, itemId = null, onClose }: Props) {
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [groups, setGroups] = useState<TagGroup[]>([])

  useEffect(() => {
    if (batchId === null) return
    let cancelled = false
    setLoading(true)
    setGroups([])

    api.getBatch(batchId)
      .then(async (batch) => {
        // Tag Number / Description were already parsed from the filename (or
        // folder name) at upload time — reuse that instead of re-parsing here.
        const items = itemId === null ? batch.items : batch.items.filter((item) => item.id === itemId)
        const withUrls = await Promise.all(
          items.map(async (item) => ({
            tagNumber: item.tag_number,
            description: item.description,
            photos: await Promise.all(
              item.images.map(async (image) => ({
                id: image.id,
                original_filename: image.original_filename,
                url: await api.batchImageUrl(batchId, image.id),
              })),
            ),
          })),
        )
        if (!cancelled) setGroups(withUrls.filter((group) => group.photos.length > 0))
      })
      .catch((caught) => {
        toast.error(caught instanceof Error ? caught.message : 'Could not load the uploaded photos.')
      })
      .finally(() => !cancelled && setLoading(false))

    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId, itemId])

  // Object URLs are only good for this component's lifetime — release them.
  useEffect(() => () => {
    groups.forEach((group) => group.photos.forEach((photo) => URL.revokeObjectURL(photo.url)))
  }, [groups])

  const title = itemId !== null && groups.length === 1
    ? `${groups[0].tagNumber} — ${groups[0].description}`
    : 'Uploaded photos'

  return (
    <Modal open={batchId !== null} title={title} onClose={onClose} width={720}>
      {loading ? (
        <Spinner size={22} label="Loading photos…" />
      ) : groups.length === 0 ? (
        <p className="muted">No photos found for this upload.</p>
      ) : (
        <div className="stack gap-20">
          {groups.map((group) => (
            <div key={group.tagNumber} className="stack gap-8">
              <div className="row gap-8" style={{ alignItems: 'center' }}>
                <span className="tag-code">{group.tagNumber}</span>
                <span className="muted">{group.description}</span>
              </div>
              <div className="photo-grid">
                {group.photos.map((photo) => (
                  <a
                    key={photo.id}
                    href={photo.url}
                    target="_blank"
                    rel="noreferrer"
                    className="photo-thumb"
                    title={photo.original_filename}
                  >
                    <img src={photo.url} alt={photo.original_filename} />
                    <span className="photo-thumb-name">{photo.original_filename}</span>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}
