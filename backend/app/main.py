"""Visioncore API entrypoint."""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.seed import seed_users
from app.db.session import AsyncSessionLocal, engine
from app.services.storage import storage_root
from app.services.sync_client import run_sync_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger("visioncore")


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage_root()
    async with AsyncSessionLocal() as session:
        try:
            await seed_users(session)
        except Exception:                       # noqa: BLE001
            # A seed failure must not stop the API from serving; migrations may
            # simply not have run yet on a very fresh volume.
            logger.exception("Could not seed accounts")
    if not settings.anthropic_api_key:
        logger.warning(
            "ANTHROPIC_API_KEY is not set \u2014 uploads will fail at the extraction step."
        )

    # Only the local/mirror side sets SYNC_SOURCE_URL \u2014 production leaves it
    # blank and never starts this task.
    sync_task = asyncio.create_task(run_sync_loop()) if settings.sync_source_url else None

    logger.info("Visioncore API ready")
    yield
    if sync_task is not None:
        sync_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sync_task
    await engine.dispose()


app = FastAPI(
    title="Visioncore API",
    description="Nameplate data migration \u2014 turn nameplate photos into structured asset data.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/docs", include_in_schema=False)
async def swagger_docs():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} \u2014 Docs",
        swagger_favicon_url="/static/cdc-logo.jpg",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_docs():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} \u2014 ReDoc",
        redoc_favicon_url="/static/cdc-logo.jpg",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],   # the browser needs this to name downloads
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn Pydantic's nested error list into one readable sentence."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query"))
    message = first.get("msg", "Invalid request")
    detail = f"{field}: {message}" if field else message
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail}
    )


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


app.include_router(api_router, prefix=settings.api_v1_prefix)
