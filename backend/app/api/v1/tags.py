"""Read, edit and download a saved asset tag."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased, selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import Activity, ActivityAction, AssetTag, BatchItem, ItemStatus, TagImage, User, UserRole
from app.schemas.common import Page
from app.schemas.tag import AssetTagOut, SaveTagRequest, SearchResultOut
from app.services.excel_template import build_template_workbook
from app.services.fields import normalise_payload
from app.services.filename_parser import excel_basename, safe_filename
from app.services.pipeline import generate_workbooks, template_path_columns
from app.services.storage import resolve_stored

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

    Scoped the same way as `list_tags`: non-admins only ever see tags they
    personally extracted; admins get the org-wide view. Only the field chosen
    in the dropdown is searched — never every field at once.
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

    if user.role != UserRole.ADMIN:
        query = query.where(AssetTag.created_by_id == user.id)
        count_query = count_query.where(AssetTag.created_by_id == user.id)

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
async def download_all_templates(user: CurrentUser, db: DbSession) -> Response:
    """One consolidated Template workbook, one row per unique asset tag.

    Reads from AssetTag (unique on tag_number) rather than the Activity log,
    so the export can't contain duplicate rows for a tag that was uploaded,
    edited or downloaded more than once.

    Scoped the same way as `list_tags` above: non-admins only ever get tags
    they personally extracted (`created_by_id`); admins get every tag.
    """
    query = select(AssetTag).order_by(AssetTag.tag_number)
    if user.role != UserRole.ADMIN:
        query = query.where(AssetTag.created_by_id == user.id)
    tags = (await db.scalars(query)).all()
    if not tags:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No extracted tags to export yet.")

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
        })

    content = build_template_workbook(records)

    db.add(Activity(
        user_id=user.id, action=ActivityAction.DOWNLOAD,
        detail=f"Downloaded consolidated Template workbook ({len(tags)} tag(s))",
    ))
    await db.commit()

    return Response(
        content=content,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": 'attachment; filename="All-Tags-Template.xlsx"'},
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
    """
    tag = await _get_tag(db, tag_id)

    tag.final_payload = normalise_payload(
        body.payload.model_dump(), tag.tag_number, tag.description
    )
    tag.edited_by_id = user.id
    tag.revision += 1

    photo_names = list(
        (await db.scalars(
            select(TagImage.original_filename)
            .join(BatchItem, BatchItem.id == TagImage.item_id)
            .where(BatchItem.tag_number == tag.tag_number)
            .order_by(TagImage.id)
        )).all()
    )
    await generate_workbooks(db, tag, photo_names or [f"{tag.tag_number}.jpg"])

    db.add(Activity(
        user_id=user.id, action=ActivityAction.EDIT,
        tag_number=tag.tag_number, description=tag.description,
        detail=f"Saved revision {tag.revision}",
    ))
    await db.commit()
    await db.refresh(tag)
    return _out(tag, await _username_of(db, tag))


async def _download(db, tag: AssetTag, kind: str, user) -> FileResponse:
    path_str = tag.ai_excel_path if kind == "ai" else tag.template_excel_path
    if not path_str:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "That workbook hasn't been generated yet. Save the tag to build it.",
        )
    try:
        path = resolve_stored(path_str)
    except (FileNotFoundError, ValueError):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "The workbook file is missing from storage. Save the tag to rebuild it.",
        ) from None

    db.add(Activity(
        user_id=user.id, action=ActivityAction.DOWNLOAD,
        tag_number=tag.tag_number, description=tag.description,
        detail=f"Downloaded {'AI Output' if kind == 'ai' else 'Template'} workbook",
    ))
    await db.commit()

    return FileResponse(path=path, filename=path.name, media_type=XLSX_MEDIA)


@router.get("/{tag_id}/download/ai")
async def download_ai(tag_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    return await _download(db, await _get_tag(db, tag_id), "ai", user)


@router.get("/{tag_id}/download/template")
async def download_template(tag_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    return await _download(db, await _get_tag(db, tag_id), "template", user)
