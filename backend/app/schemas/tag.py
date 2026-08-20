from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.batch import BatchStatus
from app.models.tag import ItemStatus
from app.schemas.common import ORMModel


class FieldValue(BaseModel):
    value: str = ""
    quality: Literal["Confirmed", "Verify"] = "Verify"


class ExtractionPayload(BaseModel):
    """The editable record shown in the results table."""
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    remarks: str = ""
    photo_status: str = ""
    qc_comment: str = ""


class ImageOut(ORMModel):
    id: int
    original_filename: str
    media_type: str
    size_bytes: int


class ExtractedImageOut(BaseModel):
    """One row in the Home page's Total Images Extracted drill-down."""
    id: int
    original_filename: str
    tag_number: str
    batch_reference: str
    status: ItemStatus
    created_at: datetime


class AssetTagOut(ORMModel):
    id: int
    tag_number: str
    description: str
    ai_payload: dict
    final_payload: dict
    revision: int
    has_ai_excel: bool = False
    has_template_excel: bool = False
    created_at: datetime
    updated_at: datetime


class BatchItemOut(ORMModel):
    id: int
    tag_number: str
    description: str
    status: ItemStatus
    error_message: str | None = None
    images: list[ImageOut] = Field(default_factory=list)
    asset_tag: AssetTagOut | None = None
    is_duplicate: bool = False


class BatchOut(ORMModel):
    id: int
    reference: str
    status: BatchStatus
    total_images: int
    total_tags: int
    created_at: datetime
    items: list[BatchItemOut] = Field(default_factory=list)


class RejectedFile(BaseModel):
    filename: str
    reason: str


class UploadResponse(BaseModel):
    batch: BatchOut
    rejected: list[RejectedFile] = Field(default_factory=list)
    duplicates: list[AssetTagOut] = Field(default_factory=list)


class SaveTagRequest(BaseModel):
    payload: ExtractionPayload


class HistoryRow(BaseModel):
    id: int
    date: datetime
    tag_number: str | None = None
    description: str | None = None
    action: str
    status: str
    username: str | None = None
    detail: str | None = None
    asset_tag_id: int | None = None
    can_download: bool = False
    batch_id: int | None = None
    batch_item_id: int | None = None
