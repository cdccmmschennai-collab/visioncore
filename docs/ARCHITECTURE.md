# Architecture

## Request lifecycle: upload to workbook

```
Browser                    FastAPI                   Background task        Claude
   │                          │                            │                  │
   ├─ POST /batches/upload ──►│                            │                  │
   │  (multipart, ≤20 files)  ├─ parse each filename       │                  │
   │                          ├─ group by tag number       │                  │
   │                          ├─ SELECT asset_tags ────────┼─ duplicate?      │
   │                          ├─ write files to storage    │                  │
   │                          ├─ INSERT batch + items      │                  │
   │◄─ 201 batch (uploaded) ──┤                            │                  │
   │                          └─ schedule process_batch ──►│                  │
   │                                                       ├─ status=extracting
   │─ GET /batches/{id} ──────► (poll every 2.5s)          ├─ encode images ─►│
   │◄─ items with status ─────┤                            │◄─ JSON payload ──┤
   │                                                       ├─ record ApiUsage │
   │                                                       ├─ status=processing
   │                                                       ├─ INSERT asset_tag
   │                                                       ├─ write both .xlsx
   │◄─ items completed ───────┤                            ├─ status=completed
   │                                                       │
   ├─ PUT /tags/{id} (edits) ►│─ normalise, bump revision  │                  │
   │                          ├─ regenerate both workbooks │                  │
   │◄─ 200 asset_tag ─────────┤                            │                  │
   │                                                       │
   ├─ GET /tags/{id}/download/template ──► FileResponse    │                  │
```

## Why background tasks, not Celery

At the stated scale — ten tags per batch, one vision call each, a handful of
concurrent users — FastAPI background tasks are the right tool. They add no
broker, no worker image, and no deployment surface.

Move to Celery or ARQ when you need any of: retries that survive an API restart,
a worker pool sized independently of the web process, scheduled re-processing,
or visibility into a queue depth. The pipeline is already written as
`process_item(item_id, user_id)` taking only primitives, so the move is a
decorator and a broker URL rather than a rewrite.

## Duplicate protection

Two layers, and the order matters:

1. **`SELECT` at upload time** — fast, and drives the "Tag already extracted"
   message with the existing record attached.
2. **`UNIQUE` constraint on `asset_tags.tag_number`** — the actual guarantee.

The `SELECT` is an optimisation for the common case; it cannot be relied on
alone, because two batches containing the same tag can pass it concurrently.
`process_item` catches the resulting `IntegrityError`, rolls back, re-reads the
winning row and marks its own item `duplicate` rather than `failed`. A race
produces a correct outcome, not an error.

## The two payloads

`asset_tags` stores `ai_payload` and `final_payload` as separate JSONB columns.

- `ai_payload` is written once and never modified. It is the audit record of
  what the model actually said.
- `final_payload` starts as a copy and diverges as reviewers correct fields.

This is what lets the Template writer colour a reviewer-supplied value blue, and
what lets the UI mark corrected rows. Collapsing them into one column would save
a little space and destroy the audit trail.

## Trusting model output

`normalise_payload` in `services/fields.py` treats every response as untrusted
input: missing keys are filled, unknown keys dropped, quality marks constrained
to the two legal values, and the tag number and description forced back to the
values parsed from the filename. A model that returns a different tag number
gets overruled and the mismatch noted in remarks — the filename comes from the
asset register and is ground truth.

## Auth

JWT access tokens (60 min default) plus refresh tokens (7 days). The client
refreshes on a 401 and retries once; a shared in-flight promise means several
concurrent 401s trigger exactly one refresh. A failed refresh clears storage and
dispatches `visioncore:auth-expired`, which `AuthProvider` listens for.

"Remember me" persists the **username only**. Passwords are never stored client
side.

Login returns the same message for an unknown username and a wrong password, so
the endpoint cannot be used to enumerate valid usernames.

## Storage layout

```
<STORAGE_DIR>/uploads/<batch_ref>/<tag_number>/<uuid>.<ext>
<STORAGE_DIR>/exports/<tag_number>/AI Output-<stem>.xlsx
<STORAGE_DIR>/exports/<tag_number>/<stem>-Template.xlsx
```

Uploads are stored under a UUID so two photos with the same original name cannot
collide; the original name is kept in `tag_images.original_filename` for the
Source line and the INPUT PHOTOS column.

Every path is resolved and checked against the storage root before use, so a
crafted tag number cannot escape via `../`.

## Scaling notes

| Concern | Now | Next step |
|---|---|---|
| Extraction | Background tasks | Celery/ARQ with retry + DLQ |
| File storage | Docker volume | S3/Azure Blob behind a storage interface |
| Status updates | 2.5s polling | Server-Sent Events or WebSocket |
| Sessions | Stateless JWT | Add a revocation list if you need forced logout |
| Postgres | Single instance | Read replica for History; `activities` is append-only and partitions cleanly by month |

## Where to change what

| Task | File |
|---|---|
| Add or reorder an extracted field | `backend/app/services/fields.py` |
| Change the extraction prompt | `backend/app/services/claude_extractor.py` |
| Change workbook layout | `backend/app/services/excel_ai.py`, `excel_template.py` |
| Change filename parsing | `backend/app/services/filename_parser.py` (mirror in `frontend/src/utils/filename.ts`) |
| Rebrand | `frontend/src/config.ts`, `frontend/src/assets/logo.svg` |
| Restyle | `frontend/src/styles/theme.css` |
