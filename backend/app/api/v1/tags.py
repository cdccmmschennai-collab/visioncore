"""Read, edit and download a saved asset tag."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.orm import aliased, selectinload

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models import Activity, ActivityAction, AssetTag, BatchItem, ItemStatus, TagImage, User, UserRole
from app.schemas.common import Message, Page
from app.schemas.tag import AssetTagOut, SaveTagRequest, SearchResultOut
from app.services.download_links import ai_excel_download_url, photo_view_url, verify_ai_excel_token
from app.services.excel_template import build_template_workbook
from app.services.fields import normalise_payload, quality_of, value_of
from app.services.filename_parser import excel_basename, safe_filename
from app.services.pipeline import generate_workbooks, template_path_columns
from app.services.storage import remove_files, resolve_stored

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tags", tags=["tags"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _out(tag: AssetTag, username: str | None = None) -> AssetTagOut:
    out = AssetTagOut.model_validate(tag)
    out.has_ai_excel = bool(tag.ai_excel_path)
    out.has_template_excel = bool(tag.template_excel_path)
    out.username = username
    return out


async def _get_tag(db, tag_id: int) -> AssetTag:
    tag = await db.get(AssetTag, tag_id)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That tag no longer exists.")
    return tag


async def _username_of(db, tag: AssetTag) -> str | None:
    """The username of whoever extracted this specific tag (created_by_id)."""
    if tag.created_by_id is None:
        return None
    return await db.scalar(select(User.username).where(User.id == tag.created_by_id))


async def _photo_names_and_paths(db, tag_number: str) -> tuple[list[str], list[str]]:
    rows = (
        await db.execute(
            select(TagImage.original_filename, TagImage.stored_path)
            .join(BatchItem, BatchItem.id == TagImage.item_id)
            .where(BatchItem.tag_number == tag_number)
            .order_by(TagImage.id)
        )
    ).all()
    names = [r[0] for r in rows] or [f"{tag_number}.jpg"]
    paths = [r[1] for r in rows]
    return names, paths


@router.get("", response_model=Page[AssetTagOut])
async def list_tags(
    user: CurrentUser,
    db: DbSession,
    search: str = Query("", max_length=128),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[AssetTagOut]:
    """Backs the Home dashboard's totals/recent list and the tag search box.

    Non-admins see only tags they personally extracted (`created_by_id`) —
    this is what keeps a new user's dashboard at zero and stops one user's
    totals from including work another user did on a shared tag. Admins get
    the unscoped, org-wide view.
    """
    query = select(AssetTag)
    count_query = select(func.count()).select_from(AssetTag)

    if user.role != UserRole.ADMIN:
        query = query.where(AssetTag.created_by_id == user.id)
        count_query = count_query.where(AssetTag.created_by_id == user.id)

    if search.strip():
        pattern = f"%{search.strip()}%"
        condition = or_(
            AssetTag.tag_number.ilike(pattern),
            AssetTag.description.ilike(pattern),
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = await db.scalar(count_query) or 0
    rows = (
        await db.scalars(
            query.order_by(AssetTag.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return Page[AssetTagOut](
        items=[_out(t) for t in rows], total=total, page=page, page_size=page_size
    )


#: Dropdown key -> AssetTag column (plain) or ExtractionPayload field key (JSONB),
#: in the exact order the Search page's dropdown lists them.
SEARCH_FIELDS: dict[str, str] = {
    "TAG NUMBER": "tag_number",
    "EQUIPMENT DESCRIPTION": "description",
    "SIZE/DIMENSION": "size_dimension",
    "MAKE (ASSET)": "make",
    "MODEL": "model",
    "SERIAL NO": "serial_no",
    "PART NO": "part_no",
    "COUNTRY": "country",
}
#: These two live as real columns on AssetTag; everything else is a key inside
#: final_payload["fields"][key]["value"] (JSONB).
PLAIN_COLUMNS = {"tag_number", "description"}


def _wildcard_pattern(value: str) -> str:
    """Turn a user-typed `*` search into an ILIKE pattern.

    `%` and `_` in the user's text are escaped first so they stay literal, then
    `*` becomes the SQL wildcard `%`. A value with no `*` therefore has no
    unescaped `%` left, so ILIKE degrades to an exact (case-insensitive) match
    — one code path covers both "=" and wildcard search.
    """
    escaped = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped.replace("*", "%")


def _search_condition(field_key: str, value: str):
    pattern = _wildcard_pattern(value)
    if field_key in PLAIN_COLUMNS:
        return getattr(AssetTag, field_key).ilike(pattern, escape="\\")
    return AssetTag.final_payload["fields"][field_key]["value"].astext.ilike(pattern, escape="\\")


@router.get("/search", response_model=Page[SearchResultOut])
async def search_tags(
    user: CurrentUser,
    db: DbSession,
    field: str = Query(..., max_length=64),
    value: str = Query("", max_length=256),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[SearchResultOut]:
    """Multi-field tag search backing the Search page.

    Org-wide for every user, admin or not — unlike `list_tags`, search isn't
    scoped to tags the caller personally extracted. The results table's
    "User" column already shows who extracted each match. Only the field
    chosen in the dropdown is searched — never every field at once.
    """
    field_key = SEARCH_FIELDS.get(field.strip().upper())
    if field_key is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown search field.")

    # The batch item whose extraction produced this tag — a duplicate re-upload
    # of the same tag_number is marked DUPLICATE, never COMPLETED, so at most
    # one row here is ever COMPLETED for a given asset_tag_id.
    completed_item = aliased(BatchItem)
    query = (
        select(AssetTag, User.username, completed_item.batch_id, completed_item.id)
        .join(User, User.id == AssetTag.created_by_id, isouter=True)
        .join(
            completed_item,
            and_(completed_item.asset_tag_id == AssetTag.id,
                 completed_item.status == ItemStatus.COMPLETED),
            isouter=True,
        )
    )
    count_query = select(func.count()).select_from(AssetTag)

    if value.strip():
        condition = _search_condition(field_key, value)
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = await db.scalar(count_query) or 0
    rows = (
        await db.execute(
            query.order_by(AssetTag.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = []
    for tag, username, batch_id, batch_item_id in rows:
        out = SearchResultOut.model_validate(tag)
        out.has_ai_excel = bool(tag.ai_excel_path)
        out.has_template_excel = bool(tag.template_excel_path)
        out.username = username
        out.batch_id = batch_id
        out.batch_item_id = batch_item_id
        items.append(out)

    return Page[SearchResultOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/download-all/template")
async def download_all_templates(
    user: CurrentUser,
    db: DbSession,
    tag_numbers: list[str] | None = Query(
        None, description="Restrict the export to just these tag numbers; omit for every tag."
    ),
    from_date: date | None = Query(
        None, description="Only tags extracted on/after this date (History's date-range download)."
    ),
    to_date: date | None = Query(
        None, description="Only tags extracted on/before this date (History's date-range download)."
    ),
) -> Response:
    """One consolidated Template workbook, one row per unique asset tag.

    Reads from AssetTag (unique on tag_number) rather than the Activity log,
    so the export can't contain duplicate rows for a tag that was uploaded,
    edited or downloaded more than once.

    Scoped the same way as `list_tags` above: non-admins only ever get tags
    they personally extracted (`created_by_id`); admins get every tag. Passing
    `tag_numbers` (History's per-tag checkboxes) narrows the same query rather
    than changing it, so the "download everything" call every existing caller
    already makes — no `tag_numbers` at all — is untouched.

    `from_date`/`to_date` (History's date-wise download) filter by the tag's
    own `created_at` — when it was extracted, since that's the moment an
    AssetTag row (and so an exportable Template row) starts existing at all.
    A single-day download is just `from_date == to_date`; both are inclusive
    of the whole day.
    """
    query = select(AssetTag).order_by(AssetTag.tag_number)
    if user.role != UserRole.ADMIN:
        query = query.where(AssetTag.created_by_id == user.id)
    if tag_numbers:
        query = query.where(AssetTag.tag_number.in_(tag_numbers))
    if from_date is not None:
        query = query.where(
            AssetTag.created_at >= datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        )
    if to_date is not None:
        query = query.where(
            AssetTag.created_at
            < datetime.combine(to_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        )
    tags = (await db.scalars(query)).all()
    if not tags:
        if from_date or to_date:
            detail = (
                f"No tags were extracted on {from_date}." if from_date == to_date
                else f"No tags were extracted between {from_date or 'the beginning'} "
                     f"and {to_date or 'now'}."
            )
        elif tag_numbers:
            detail = "None of the selected tags could be found."
        else:
            detail = "No extracted tags to export yet."
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)

    photo_rows = (
        await db.execute(
            select(BatchItem.tag_number, TagImage.original_filename)
            .join(TagImage, TagImage.item_id == BatchItem.id)
            .where(BatchItem.tag_number.in_([t.tag_number for t in tags]))
            .order_by(TagImage.id)
        )
    ).all()
    photos_by_tag: dict[str, list[str]] = {}
    for tag_number, filename in photo_rows:
        photos_by_tag.setdefault(tag_number, []).append(filename)

    records = []
    for tag in tags:
        input_cell, output_cell = template_path_columns(
            tag.tag_number, tag.description, photos_by_tag.get(tag.tag_number, [])
        )
        records.append({
            "payload": tag.final_payload,
            "ai_payload": tag.ai_payload,
            "input_photos": input_cell,
            "output_file": output_cell,
            "ai_excel_url": ai_excel_download_url(tag.tag_number),
            "input_photo_url": (
                photo_view_url(tag.tag_number) if tag.tag_number in photos_by_tag else None
            ),
        })

    content = build_template_workbook(records)

    date_range = f"{from_date} to {to_date}" if (from_date or to_date) else ""
    db.add(Activity(
        user_id=user.id, action=ActivityAction.DOWNLOAD,
        detail=f"Downloaded consolidated Template workbook "
               f"({len(tags)} {'selected ' if tag_numbers else ''}tag(s)"
               f"{f', {date_range}' if date_range else ''})",
    ))
    await db.commit()

    if from_date or to_date:
        filename = (
            f"Tags-{from_date}-Template.xlsx" if from_date == to_date
            else f"Tags-{from_date or 'start'}_to_{to_date or 'now'}-Template.xlsx"
        )
    elif tag_numbers:
        filename = "Selected-Tags-Template.xlsx"
    else:
        filename = "All-Tags-Template.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/by-number/{tag_number}", response_model=AssetTagOut)
async def get_by_number(tag_number: str, user: CurrentUser, db: DbSession) -> AssetTagOut:
    """Used by the duplicate notice to show what was extracted the first time."""
    tag = await db.scalar(select(AssetTag).where(AssetTag.tag_number == tag_number.upper()))
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No record for that tag number.")
    return _out(tag, await _username_of(db, tag))


@router.get("/{tag_id}", response_model=AssetTagOut)
async def get_tag(tag_id: int, user: CurrentUser, db: DbSession) -> AssetTagOut:
    tag = await _get_tag(db, tag_id)
    return _out(tag, await _username_of(db, tag))


@router.put("/{tag_id}", response_model=AssetTagOut)
async def save_tag(
    tag_id: int, body: SaveTagRequest, user: CurrentUser, db: DbSession
) -> AssetTagOut:
    """Persist reviewer corrections and rebuild both workbooks.

    `ai_payload` is deliberately left untouched — the whole point of keeping it
    is that the Template sheet can colour a reviewer-supplied value blue by
    comparing the two.

    Tag Number and Description are editable like any other field. Description
    is just text — it flows straight into final_payload and the regenerated
    workbook names below. Tag Number is this record's identity everywhere
    else in the schema (BatchItem, Activity, photo links, duplicate check all
    key off the string, not asset_tag_id), so a change here is a rename:
    checked for a collision with another tag, then carried onto every
    BatchItem and Activity row that pointed at the old number, so nothing
    that already existed for this tag becomes unreachable under the new one.
    """
    tag = await _get_tag(db, tag_id)

    raw_payload = body.payload.model_dump()
    old_tag_number = tag.tag_number
    new_tag_number = value_of(raw_payload, "tag_number").strip().upper() or old_tag_number
    new_description = value_of(raw_payload, "description").strip() or tag.description

    if new_tag_number != old_tag_number:
        collision = await db.scalar(
            select(AssetTag.id).where(AssetTag.tag_number == new_tag_number, AssetTag.id != tag.id)
        )
        if collision is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Tag number {new_tag_number} is already used by another record.",
            )
        await db.execute(
            update(BatchItem)
            .where(BatchItem.asset_tag_id == tag.id)
            .values(tag_number=new_tag_number)
        )
        await db.execute(
            update(Activity)
            .where(Activity.tag_number == old_tag_number)
            .values(tag_number=new_tag_number)
        )
        tag.tag_number = new_tag_number

    tag.description = new_description
    tag.final_payload = normalise_payload(
        raw_payload, new_tag_number, new_description,
        tag_number_quality=quality_of(raw_payload, "tag_number"),
        description_quality=quality_of(raw_payload, "description"),
    )
    tag.edited_by_id = user.id
    tag.revision += 1

    photo_rows = (
        await db.execute(
            select(TagImage.original_filename, TagImage.stored_path)
            .join(BatchItem, BatchItem.id == TagImage.item_id)
            .where(BatchItem.tag_number == tag.tag_number)
            .order_by(TagImage.id)
        )
    ).all()
    photo_names = [r[0] for r in photo_rows]
    photo_paths = [r[1] for r in photo_rows]
    # Workbook filenames are built from tag_number + description (see
    # excel_basename) — renaming either leaves the old-named files behind
    # under the previous path unless they're cleaned up once the new ones
    # are safely written.
    stale_exports = [p for p in (tag.ai_excel_path, tag.template_excel_path) if p]
    await generate_workbooks(db, tag, photo_names or [f"{tag.tag_number}.jpg"], photo_paths)
    stale_exports = [p for p in stale_exports if p not in (tag.ai_excel_path, tag.template_excel_path)]
    if stale_exports:
        remove_files(stale_exports)

    db.add(Activity(
        user_id=user.id, action=ActivityAction.EDIT,
        tag_number=tag.tag_number, description=tag.description,
        detail=f"Saved revision {tag.revision}",
    ))
    await db.commit()
    await db.refresh(tag)
    return _out(tag, await _username_of(db, tag))


async def _download(db, tag: AssetTag, kind: str, user: User | None) -> FileResponse:
    """`user` is None for a signed-link download (see the /download/ai-link
    route below) — Excel's hyperlink click carries no bearer token, so there's
    no logged-in user to attribute the download to.
    """
    path_str = tag.ai_excel_path if kind == "ai" else tag.template_excel_path
    if not path_str:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "That workbook hasn't been generated yet. Save the tag to build it.",
        )
    try:
        path = resolve_stored(path_str)
    except (FileNotFoundError, ValueError):
        # Common for a tag synced in from production (app/services/sync_client.py):
        # the row, including both payloads, replicates — the generated file on disk
        # never does. Rebuild it here from the payload data, which did sync.
        try:
            photo_names, photo_paths = await _photo_names_and_paths(db, tag.tag_number)
            await generate_workbooks(db, tag, photo_names, photo_paths)
            await db.commit()
            path = resolve_stored(
                tag.ai_excel_path if kind == "ai" else tag.template_excel_path
            )
        except Exception:
            logger.exception("Could not rebuild missing workbook for %s", tag.tag_number)
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "The workbook file is missing from storage and could not be rebuilt.",
            ) from None

    workbook_kind = "AI Output" if kind == "ai" else "Template"
    db.add(Activity(
        user_id=user.id if user else None, action=ActivityAction.DOWNLOAD,
        tag_number=tag.tag_number, description=tag.description,
        detail=f"Downloaded {workbook_kind} workbook"
               + ("" if user else " (via AI OUTPUT EXCEL link)"),
    ))
    await db.commit()

    return FileResponse(path=path, filename=path.name, media_type=XLSX_MEDIA)


@router.get("/{tag_id}/download/ai")
async def download_ai(tag_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    return await _download(db, await _get_tag(db, tag_id), "ai", user)


@router.get("/download/ai-link")
async def download_ai_by_link(token: str, db: DbSession) -> FileResponse:
    """Unauthenticated counterpart to `download_ai`, for the AI OUTPUT EXCEL
    hyperlink embedded in an exported Template workbook — see
    app.services.download_links. Guarded by a signed, expiring, tag-scoped
    token instead of CurrentUser, since a hyperlink click carries no bearer
    token for the SPA's normal auth to check.
    """
    tag_number = verify_ai_excel_token(token)
    if tag_number is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "This download link is invalid or has expired."
        )
    tag = await db.scalar(select(AssetTag).where(AssetTag.tag_number == tag_number))
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That tag no longer exists.")
    return await _download(db, tag, "ai", None)


@router.get("/{tag_id}/download/template")
async def download_template(tag_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    return await _download(db, await _get_tag(db, tag_id), "template", user)


@router.delete("/{tag_id}", response_model=Message)
async def delete_tag(tag_id: int, admin: AdminUser, db: DbSession) -> Message:
    """Permanently remove a completed tag and everything tied to it.

    Admin-only (enforced by `AdminUser`, independent of whatever the frontend
    shows) and only for a tag that has actually completed extraction — the
    same condition `search_tags`/`list_history` use to decide whether a tag
    can be viewed at all. Deleting `BatchItem` rows here lets the existing
    `tag_images.item_id` ON DELETE CASCADE remove their `TagImage` rows in
    the database; the `AssetTag` row is removed last so callers never see a
    tag with no batch items.
    """
    tag = await _get_tag(db, tag_id)

    has_completed = await db.scalar(
        select(func.count()).select_from(BatchItem)
        .where(BatchItem.asset_tag_id == tag.id, BatchItem.status == ItemStatus.COMPLETED)
    )
    if not has_completed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a completed tag can be deleted.")

    image_paths = (
        await db.scalars(
            select(TagImage.stored_path)
            .join(BatchItem, BatchItem.id == TagImage.item_id)
            .where(BatchItem.asset_tag_id == tag.id)
        )
    ).all()
    excel_paths = [p for p in (tag.ai_excel_path, tag.template_excel_path) if p]

    await db.execute(delete(BatchItem).where(BatchItem.asset_tag_id == tag.id))
    tag_number = tag.tag_number
    await db.delete(tag)
    await db.commit()

    remove_files([*image_paths, *excel_paths])

    return Message(message=f"Tag {tag_number} has been deleted.")
