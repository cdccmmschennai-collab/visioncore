"""Public configuration the frontend needs before a user signs in."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/config", tags=["config"])


class PublicConfig(BaseModel):
    company_name: str
    app_name: str
    max_images_per_batch: int
    max_tags_per_batch: int
    max_images_per_tag: int
    max_image_size_mb: int


@router.get("", response_model=PublicConfig)
async def public_config() -> PublicConfig:
    return PublicConfig(
        company_name=settings.company_name,
        app_name=settings.app_name,
        max_images_per_batch=settings.max_images_per_batch,
        max_tags_per_batch=settings.max_tags_per_batch,
        max_images_per_tag=settings.max_images_per_tag,
        max_image_size_mb=settings.max_image_size_mb,
    )
