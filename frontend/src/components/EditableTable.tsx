import { useEffect, useMemo, useState } from 'react'
import QualityChip from './QualityChip'
import Spinner from './Spinner'
import { FIELD_ORDER, NOT_PRESENT } from '@/api/types'
import type { AssetTag, ExtractionPayload, FieldValue, Quality } from '@/api/types'

interface Props {
  tag: AssetTag
  onSave: (payload: ExtractionPayload) => Promise<void>
  onDownloadAi: () => Promise<void>
  onDownloadTemplate: () => Promise<void>
  onViewPhoto?: () => void
  readOnly?: boolean
}

/** Deep clone so editing never mutates the payload React is rendering from. */
function clonePayload(payload: ExtractionPayload): ExtractionPayload {
  return {
    fields: Object.fromEntries(
      Object.entries(payload.fields ?? {}).map(([key, value]) => [key, { ...value }]),
    ),
    remarks: payload.remarks ?? '',
    photo_status: payload.photo_status ?? '',
    qc_comment: payload.qc_comment ?? '',
  }
}

function emptyField(): FieldValue {
  return { value: '', quality: 'Verify' }
}

export default function EditableTable({
  tag, onSave, onDownloadAi, onDownloadTemplate, onViewPhoto, readOnly = false,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [downloading, setDownloading] = useState<'ai' | 'template' | null>(null)
  const [draft, setDraft] = useState<ExtractionPayload>(() => clonePayload(tag.final_payload))

  // A save returns a new revision; re-seed the draft unless the user is mid-edit.
  useEffect(() => {
    if (!editing) setDraft(clonePayload(tag.final_payload))
  }, [tag.final_payload, tag.revision, editing])

  const source = editing ? draft : tag.final_payload

  /** Fields the reviewer has already changed away from the AI's answer. */
  const corrected = useMemo(() => {
    const set = new Set<string>()
    for (const { key } of FIELD_ORDER) {
      const ai = tag.ai_payload?.fields?.[key]?.value ?? ''
      const final = tag.final_payload?.fields?.[key]?.value ?? ''
      if (ai.trim() !== final.trim()) set.add(key)
    }
    return set
  }, [tag.ai_payload, tag.final_payload])

  const setField = (key: string, patch: Partial<FieldValue>) =>
    setDraft((current) => ({
      ...current,
      fields: {
        ...current.fields,
        [key]: { ...(current.fields[key] ?? emptyField()), ...patch },
      },
    }))

  const startEdit = () => {
    setDraft(clonePayload(tag.final_payload))
    setEditing(true)
  }

  const cancel = () => {
    setDraft(clonePayload(tag.final_payload))
    setEditing(false)
  }

  const save = async () => {
    setSaving(true)
    try {
      await onSave(draft)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const runDownload = async (kind: 'ai' | 'template') => {
    setDownloading(kind)
    try {
      await (kind === 'ai' ? onDownloadAi() : onDownloadTemplate())
    } finally {
      setDownloading(null)
    }
  }

  return (
    <section className="card result-card">
      <div className="card-head">
        <div className="stack gap-4">
          <span className="tag-code result-tag">{tag.tag_number}</span>
          <span className="muted">{tag.description}</span>
        </div>
        <div className="row gap-8 wrap">
          {tag.revision > 1 && (
            <span className="chip chip-neutral">Revision {tag.revision}</span>
          )}
          {editing ? (
            <>
              <button type="button" className="btn" onClick={cancel} disabled={saving}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={save} disabled={saving}>
                {saving ? <Spinner size={14} /> : null}
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <>
              {onViewPhoto && (
                <button type="button" className="btn btn-accent" onClick={onViewPhoto}>
                  View Photo
                </button>
              )}
              {!readOnly && (
                <button type="button" className="btn" onClick={startEdit}>
                  Edit
                </button>
              )}
              <button
                type="button"
                className="btn"
                onClick={() => runDownload('ai')}
                disabled={downloading !== null || !tag.has_ai_excel}
              >
                {downloading === 'ai' ? <Spinner size={14} /> : null}
                Download AI Output
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => runDownload('template')}
                disabled={downloading !== null || !tag.has_template_excel}
              >
                {downloading === 'template' ? <Spinner size={14} /> : null}
                Download Template
              </button>
            </>
          )}
        </div>
      </div>

      {editing && (
        <div className="alert alert-info" style={{ marginBottom: 16 }}>
          <span aria-hidden="true">i</span>
          <span>
            Review and correct the data if needed, then click Save. Changed values are recorded separately from the AI's original answer and appear in blue in the Template workbook.          </span>
        </div>
      )}

      <div className="table-wrap">
        <table className="data result-table">
          <thead>
            <tr>
              <th style={{ width: '22%' }}>Field</th>
              <th>Extracted Value</th>
              <th style={{ width: 148 }}>Data Quality</th>
            </tr>
          </thead>
          <tbody>
            {FIELD_ORDER.map(({ key, label, multiline }) => {
              const field = source.fields?.[key] ?? emptyField()
              const isMissing = field.value === NOT_PRESENT
              const wasCorrected = corrected.has(key)
              // Tag number and description come from the filename and are the
              // record's identity — editing them here would orphan the files.
              const locked = key === 'tag_number' || key === 'description'

              return (
                <tr key={key}>
                  <th scope="row" className="field-label">
                    {label}
                    {wasCorrected && !editing && (
                      <span className="corrected-dot" title="Corrected by a reviewer" />
                    )}
                  </th>
                  <td>
                    {editing && !locked ? (
                      multiline ? (
                        <textarea
                          className="textarea"
                          value={field.value}
                          onChange={(event) => setField(key, { value: event.target.value })}
                          aria-label={label}
                        />
                      ) : (
                        <input
                          className="input"
                          value={field.value}
                          onChange={(event) => setField(key, { value: event.target.value })}
                          aria-label={label}
                        />
                      )
                    ) : (
                      <span
                        className={`field-value${isMissing ? ' field-missing' : ''}${
                          wasCorrected ? ' field-corrected' : ''
                        }`}
                      >
                        {field.value || '—'}
                      </span>
                    )}
                  </td>
                  <td>
                    {editing && !locked ? (
                      <select
                        className="select"
                        value={field.quality}
                        onChange={(event) =>
                          setField(key, { quality: event.target.value as Quality })
                        }
                        aria-label={`${label} data quality`}
                      >
                        <option value="Confirmed">Confirmed</option>
                        <option value="Verify">Verify</option>
                      </select>
                    ) : (
                      <QualityChip quality={field.quality} missing={isMissing} />
                    )}
                  </td>
                </tr>
              )
            })}

            <tr>
              <th scope="row" className="field-label">Remarks</th>
              <td colSpan={2}>
                {editing ? (
                  <textarea
                    className="textarea"
                    value={draft.remarks}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, remarks: event.target.value }))
                    }
                    aria-label="Remarks"
                  />
                ) : (
                  <span className="field-value">{source.remarks || '—'}</span>
                )}
              </td>
            </tr>
            <tr>
              <th scope="row" className="field-label">Photo Status</th>
              <td colSpan={2}>
                {editing ? (
                  <select
                    className="select"
                    style={{ maxWidth: 200 }}
                    value={draft.photo_status}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, photo_status: event.target.value }))
                    }
                    aria-label="Photo status"
                  >
                    <option value="">Not set</option>
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                ) : (
                  <span className="field-value">{source.photo_status || '—'}</span>
                )}
              </td>
            </tr>
            <tr>
              <th scope="row" className="field-label">QC Comment</th>
              <td colSpan={2}>
                {editing ? (
                  <textarea
                    className="textarea"
                    value={draft.qc_comment}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, qc_comment: event.target.value }))
                    }
                    aria-label="QC comment"
                  />
                ) : (
                  <span className="field-value">{source.qc_comment || '—'}</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}
