import { forwardRef, useCallback, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { ACCEPTED_EXTENSIONS, LIMITS } from '@/config'
import { stagedFromDataTransfer, stagedFromDirectoryInput, stagedFromFiles, stagedGroup, stagedKey, type StagedFile } from '@/utils/upload'

interface Props {
  files: StagedFile[]
  onChange: (files: StagedFile[]) => void
  disabled?: boolean
}

export interface DropzoneHandle {
  /** Opens the OS folder-selection dialog, used by the page-level Add Folder button. */
  openFolderPicker: () => void
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot).toLowerCase()
}

const Dropzone = forwardRef<DropzoneHandle, Props>(function Dropzone(
  { files, onChange, disabled = false },
  ref,
) {
  const [dragging, setDragging] = useState(false)
  const [dropIssue, setDropIssue] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement | null>(null)

  /**
   * `webkitdirectory`/`directory`/`mozdirectory` are non-standard boolean
   * attributes with inconsistent JSX/TypeScript attribute support across
   * React versions — setting them as plain JSX props isn't reliable everywhere.
   * Setting them directly on the DOM node via a ref callback is the
   * well-documented, cross-browser-reliable way to force this input into
   * folder-selection mode instead of the ordinary multi-file picker.
   */
  const attachFolderInput = useCallback((node: HTMLInputElement | null) => {
    folderInputRef.current = node
    if (node) {
      node.setAttribute('webkitdirectory', '')
      node.setAttribute('directory', '')
      node.setAttribute('mozdirectory', '')
    }
  }, [])

  useImperativeHandle(ref, () => ({
    openFolderPicker: () => folderInputRef.current?.click(),
  }), [])

  /** Group the selection by tag so the user sees what will be processed. */
  const groups = useMemo(() => {
    const map = new Map<string, { description: string; files: StagedFile[]; valid: boolean; reason?: string; folder: string | null }>()
    for (const staged of files) {
      const { key, parsed } = stagedGroup(staged)
      const group = map.get(key) ?? {
        description: parsed.description,
        files: [],
        valid: parsed.ok,
        reason: parsed.reason,
        folder: staged.folder,
      }
      group.files.push(staged)
      map.set(key, group)
    }
    return [...map.entries()]
  }, [files])

  const tagCount = groups.filter(([, g]) => g.valid).length
  const overImageLimit = files.length > LIMITS.maxImagesPerBatch
  const overTagLimit = tagCount > LIMITS.maxTagsPerBatch

  const addFiles = useCallback(
    (incoming: StagedFile[]) => {
      const existing = new Set(files.map(stagedKey))
      // De-duplicate so dropping the same folder twice doesn't double the batch.
      const merged = [...files]
      for (const staged of incoming) {
        const key = stagedKey(staged)
        if (!existing.has(key)) {
          existing.add(key)
          merged.push(staged)
        }
      }
      onChange(merged)
    },
    [files, onChange],
  )

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      setDragging(false)
      setDropIssue(null)
      if (disabled) return
      const itemCount = event.dataTransfer.items?.length ?? 0
      if (!itemCount && !event.dataTransfer.files?.length) return

      stagedFromDataTransfer(event.dataTransfer).then(({ staged, unreadableCount }) => {
        if (staged.length === 0 && itemCount > 0) {
          // Most often a dropped folder whose files are cloud-placeholders
          // (OneDrive/network-drive "Files On-Demand") that this browser
          // can't read via drag-and-drop — the file dialog handles that
          // fine, so point the user at "browse a folder" instead of
          // leaving the drop looking like it silently did nothing.
          setDropIssue(
            "That drop couldn't be read — this can happen with folders on OneDrive or a network " +
              'drive that aren’t fully downloaded locally. Use "browse a folder" instead.',
          )
          return
        }
        if (unreadableCount > 0) {
          setDropIssue(
            `${unreadableCount} item${unreadableCount === 1 ? '' : 's'} in that drop couldn't be read ` +
              'and were skipped — try "browse a folder" instead if photos are missing below.',
          )
        }
        addFiles(staged)
      })
    },
    [addFiles, disabled],
  )

  const removeFile = (target: StagedFile) =>
    onChange(files.filter((staged) => staged !== target))

  return (
    <div className="stack gap-16">
      <div
        className={`dropzone${dragging ? ' dropzone-active' : ''}${disabled ? ' dropzone-disabled' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        onKeyDown={(event) => {
          if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
            event.preventDefault()
            fileInputRef.current?.click()
          }
        }}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Add nameplate images"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(',')}
          hidden
          disabled={disabled}
          onChange={(event) => {
            if (event.target.files?.length) addFiles(stagedFromFiles(event.target.files))
            event.target.value = ''   // allow re-picking the same file
          }}
        />
        <input
          ref={attachFolderInput}
          type="file"
          hidden
          disabled={disabled}
          onChange={(event) => {
            if (event.target.files?.length) addFiles(stagedFromDirectoryInput(event.target.files))
            event.target.value = ''
          }}
        />
        <span className="dropzone-glyph" aria-hidden="true">⬆</span>
        <p className="dropzone-lead">
          Drop nameplate photos here, or{' '}
          <span
            className="link-like"
            onClick={(event) => {
              event.stopPropagation()
              if (!disabled) fileInputRef.current?.click()
            }}
          >
            browse your files
          </span>
        </p>
        <p className="dropzone-hint">
          Up to {LIMITS.maxImagesPerBatch} images across {LIMITS.maxTagsPerBatch} tags,
          {' '}{LIMITS.maxImagesPerTag} photos per tag, {LIMITS.maxImageSizeMb} MB each
        </p>
        <p className="dropzone-format">
          Name files like <code>12-4020-BV-0074-BALL VALVE.jpg</code>, or name each subfolder
          that way and add the parent folder — every subfolder's photos become one tag.
        </p>
      </div>

      {dropIssue && (
        <div className="alert alert-warn">
          <span aria-hidden="true">▲</span>
          <span>{dropIssue}</span>
        </div>
      )}

      {(overImageLimit || overTagLimit) && (
        <div className="alert alert-error">
          <span aria-hidden="true">!</span>
          <span>
            {overImageLimit
              ? `That's ${files.length} images — remove ${files.length - LIMITS.maxImagesPerBatch} to get under the limit of ${LIMITS.maxImagesPerBatch}.`
              : `That's ${tagCount} tags — a batch covers up to ${LIMITS.maxTagsPerBatch}.`}
          </span>
        </div>
      )}

      {groups.length > 0 && (
        <div className="stack gap-8">
          <div className="row gap-12 wrap">
            <span className="eyebrow">
              {tagCount} tag{tagCount === 1 ? '' : 's'} · {files.length} image
              {files.length === 1 ? '' : 's'}
            </span>
            <span className="spacer" />
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => onChange([])}>
              Clear all
            </button>
          </div>

          <div className="stage-list">
            {groups.map(([key, group]) => (
              <div key={key} className={`stage-group${group.valid ? '' : ' stage-invalid'}`}>
                <div className="stage-group-head">
                  {group.valid ? (
                    <>
                      <span className="tag-code">{key}</span>
                      <span className="muted">{group.description}</span>
                      {group.folder !== null && (
                        <span className="chip chip-neutral" title="Grouped from a subfolder">
                          📁 {group.folder}
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="chip chip-danger">{group.reason ?? 'Unreadable name'}</span>
                  )}
                  <span className="spacer" />
                  {group.valid && group.files.length > LIMITS.maxImagesPerTag && (
                    <span className="chip chip-verify">
                      {group.files.length} photos — max {LIMITS.maxImagesPerTag}
                    </span>
                  )}
                </div>
                <ul className="stage-files">
                  {group.files.map((staged) => (
                    <li key={stagedKey(staged)}>
                      <span className="stage-ext">{extensionOf(staged.file.name).replace('.', '')}</span>
                      <span className="stage-name" title={staged.file.name}>{staged.file.name}</span>
                      <span className="muted nowrap">{(staged.file.size / 1024 / 1024).toFixed(1)} MB</span>
                      <button
                        type="button"
                        className="icon-btn icon-btn-sm"
                        onClick={() => removeFile(staged)}
                        aria-label={`Remove ${staged.file.name}`}
                        disabled={disabled}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
})

export default Dropzone
