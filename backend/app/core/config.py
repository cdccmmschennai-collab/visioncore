"""Application settings, loaded once from the environment.

pydantic-settings validates and coerces at import time, so a typo'd env var
fails at startup with a clear message instead of surfacing as a mystery None
deep inside a request handler.
"""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Visioncore"
    company_name: str = Field("Visioncore", alias="COMPANY_NAME")
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = Field("http://localhost:5173", alias="CORS_ORIGINS")

    # ── Database ─────────────────────────────────────────────────────────────
    postgres_user: str = Field("visioncore", alias="POSTGRES_USER")
    postgres_password: str = Field("visioncore", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("visioncore", alias="POSTGRES_DB")
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")

     # ── Background jobs ───────────────────────────────────────────────────────
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_result_backend: str = Field("redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")

    # ── Security ─────────────────────────────────────────────────────────────
    jwt_secret: str = Field("dev-only-secret-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # ── Claude ───────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-sonnet-5", alias="CLAUDE_MODEL")
    # Raised from 4096: a too-tight ceiling risks the model being cut off
    # before it finishes the JSON payload on a dense multi-photo nameplate
    # tag, which can surface as an empty/truncated response rather than a
    # clean answer. The API only bills for tokens actually generated, so a
    # higher ceiling costs nothing when the model finishes well under it.
    claude_max_tokens: int = Field(8192, alias="CLAUDE_MAX_TOKENS")
    claude_input_price_per_mtok: float = Field(3.00, alias="CLAUDE_INPUT_PRICE_PER_MTOK")
    claude_output_price_per_mtok: float = Field(15.00, alias="CLAUDE_OUTPUT_PRICE_PER_MTOK")
    # An Admin API key (`sk-ant-admin01-...`), distinct from the regular API
    # key above and only available to organization admins. Required for the
    # Admin page's Claude usage dashboard, which reads exclusively from
    # Anthropic's official Usage & Cost Admin API. Never sent to the
    # frontend. Leave blank and the dashboard reports itself unavailable
    # rather than showing any locally estimated figures.
    anthropic_admin_api_key: str = Field("", alias="ANTHROPIC_ADMIN_API_KEY")
    # ── Claude image optimization (temporary, in-memory copies only — see
    # app/services/image_optimizer.py) ─────────────────────────────────────
    # A photo at or under BOTH thresholds is sent to Claude completely
    # unmodified — no re-encode, no quality loss, the file on disk is never
    # touched either way. Only a photo that exceeds one of these gets a
    # resized/recompressed copy built in memory for that one Claude request.
    # 1600px: Anthropic's vision pipeline itself resizes the long edge down
    # to ~1568px before reading an image, so sending noticeably more than
    # that spends extra payload bytes and tokens without any OCR benefit —
    # 1600 keeps a small margin above that internal cap rather than cutting
    # it exactly at it.
    claude_image_max_dimension_px: int = Field(1600, alias="CLAUDE_IMAGE_MAX_DIMENSION_PX")
    claude_image_max_bytes: int = Field(4 * 1024 * 1024, alias="CLAUDE_IMAGE_MAX_BYTES")
    # Moderate compression only — see docstring above; OCR accuracy on small
    # stamped/etched nameplate text matters far more than a smaller payload,
    # so this defaults high rather than chasing maximum size reduction.
    claude_image_jpeg_quality: int = Field(88, alias="CLAUDE_IMAGE_JPEG_QUALITY")
    # Hard ceiling on ONE photo's optimized output. If the standard pass
    # above is still over this (an unusually detailed/noisy photo), a
    # second, more conservative pass (smaller dimension, lower quality) is
    # tried before accepting whatever came out smallest — see
    # image_optimizer.optimize_for_claude. Comfortably under Anthropic's
    # documented ~5 MB per-image limit even after base64's ~33% inflation.
    claude_image_hard_max_bytes: int = Field(3 * 1024 * 1024, alias="CLAUDE_IMAGE_HARD_MAX_BYTES")
    # Combined budget across ALL of one tag's optimized photos (raw bytes,
    # before base64) — a multi-photo tag (e.g. 4 photos) can still add up to
    # an oversized request even when each photo individually cleared the cap
    # above. If the total exceeds this, the largest photo(s) get one more,
    # more aggressive pass rather than the request going out oversized — see
    # image_optimizer.prepare_images_for_claude. Sized to comfortably clear
    # Anthropic's overall request-size limits for a typical 3-5 photo tag.
    claude_request_max_bytes: int = Field(12 * 1024 * 1024, alias="CLAUDE_REQUEST_MAX_BYTES")
    # Pure display conversion of Anthropic's official USD spend — never sent
    # to Anthropic, never treated as data Anthropic returned.
    usd_to_inr_rate: float = Field(83.00, alias="USD_TO_INR_RATE")
    # Spend warning shown on the Admin page once official USD spend reaches
    # this threshold. Based only on Anthropic's official cost report.
    claude_spend_warning_usd: float = Field(5.00, alias="CLAUDE_SPEND_WARNING_USD")

    # ── Uploads ──────────────────────────────────────────────────────────────
    storage_dir: str = Field("./storage", alias="STORAGE_DIR")
    max_images_per_batch: int = Field(20, alias="MAX_IMAGES_PER_BATCH")
    max_tags_per_batch: int = Field(10, alias="MAX_TAGS_PER_BATCH")
    max_images_per_tag: int = Field(5, alias="MAX_IMAGES_PER_TAG")
    max_image_size_mb: int = Field(15, alias="MAX_IMAGE_SIZE_MB")

    # ── Concurrent batch processing ─────────────────────────────────────────
    # How many tags can be mid-extraction (a live Claude call) at once, across
    # the WHOLE process — not per batch. A single module-level semaphore in
    # app/services/pipeline.py enforces this, so two users' batches running at
    # the same time still share this one ceiling. Keep this comfortably below
    # db/session.py's pool_size + max_overflow (30): each in-flight extraction
    # holds one pooled connection for the whole call, plus the app still
    # needs headroom for ordinary request traffic (auth, polling).
    extraction_max_concurrency: int = Field(4, alias="EXTRACTION_MAX_CONCURRENCY")

    # Transient-failure retry (rate limit / timeout / connection / 5xx only —
    # see ExtractionError.retryable in claude_extractor.py). A 4xx or
    # malformed-response failure is never retried, regardless of this setting.
    extraction_max_retries: int = Field(3, alias="EXTRACTION_MAX_RETRIES")
    extraction_retry_base_delay_seconds: float = Field(2.0, alias="EXTRACTION_RETRY_BASE_DELAY_SECONDS")

    # The Anthropic SDK has its own internal retry-with-backoff for the same
    # class of transient errors. Our outer retry loop above now owns retry
    # policy (and writes ItemStatus.RETRYING so it's visible), so this is left
    # at 0 by default — otherwise a single outer attempt could silently retry
    # again inside the SDK, multiplying total attempts and worst-case delay.
    claude_sdk_max_retries: int = Field(0, alias="CLAUDE_SDK_MAX_RETRIES")

    # Purely presentational grouping for the progress display ("Batch 2 of
    # 4") — items are never queued or throttled in chunks; concurrency is
    # governed solely by extraction_max_concurrency above.
    batch_progress_chunk_size: int = Field(25, alias="BATCH_PROGRESS_CHUNK_SIZE")

    # ── Batch Process (browser-driven folder scan) ──────────────────────────
    # The "Batch Process" button on the New Batch page reads/writes a local
    # folder directly from the browser (File System Access API) rather than
    # from a server-local path, so it works the same whether the backend is
    # local or a remote deployment. It covers far more tags per run than a
    # normal drag-drop upload, hence the separate, higher ceiling.
    # Raised from 100: a run of 300-500 photos at ~4 photos/tag is 125-150+
    # tags, and the frontend now uploads a Batch Process run in sequential
    # chunks anyway (see frontend/src/utils/upload.ts chunkStagedFiles), so a
    # higher tag ceiling here no longer means a single giant request.
    max_tags_per_batch_process: int = Field(200, alias="MAX_TAGS_PER_BATCH_PROCESS")

    # ── Template path columns ────────────────────────────────────────────────
    # The reference workbook records the network location of each photo and
    # workbook in INPUT PHOTOS / OUTPUT WITH IMAGES. Point these at your share
    # to reproduce that exactly; leave blank to write bare filenames instead.
    template_input_path_prefix: str = Field(
        r"Z:\CMMS-CMN\DISCN\SOFTWARE TOOL TEAM\4-8-26(FINAL OUTPUT)\INPUT",
        alias="TEMPLATE_INPUT_PATH_PREFIX",
    )
    template_output_path_prefix: str = Field(
        r"Z:\CMMS-CMN\DISCN\SOFTWARE TOOL TEAM\4-8-26(FINAL OUTPUT)\OUTPUT",
        alias="TEMPLATE_OUTPUT_PATH_PREFIX",
    )

    # ── Signed download links (see app.services.download_links) ────────────────
    # The AI OUTPUT EXCEL / INPUT PHOTO hyperlinks embedded in an exported
    # workbook must resolve on whatever machine later opens that file, not just
    # this server — so they point at this public URL rather than a local path.
    public_base_url: str = Field("http://localhost:8000", alias="PUBLIC_BASE_URL")
    # These workbooks are long-lived reference documents, not one-time shares,
    # so the signed link is deliberately long-lived rather than short-expiry.
    download_link_expire_days: int = Field(365, alias="DOWNLOAD_LINK_EXPIRE_DAYS")

    # ── Production -> local sync ─────────────────────────────────────────────
    # Shared secret, set identically in both environments' .env files.
    # Production uses it to authenticate incoming pulls (app/api/v1/sync.py);
    # local uses it to authenticate outgoing ones (app/services/sync_client.py).
    sync_api_token: str = Field("", alias="SYNC_API_TOKEN")
    # Base URL of the production API. Leave blank on production itself — that
    # is what keeps the pull loop from ever starting there.
    sync_source_url: str = Field("", alias="SYNC_SOURCE_URL")
    sync_poll_interval_seconds: int = Field(30, alias="SYNC_POLL_INTERVAL_SECONDS")

    # ── Seed accounts ────────────────────────────────────────────────────────
    seed_admin_username: str = Field("admin", alias="SEED_ADMIN_USERNAME")
    seed_admin_password: str = Field("Admin@123", alias="SEED_ADMIN_PASSWORD")
    seed_user_username: str = Field("user", alias="SEED_USER_USERNAME")
    seed_user_password: str = Field("User@123", alias="SEED_USER_PASSWORD")

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        """Async driver URL used by the app at runtime."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync driver URL — Alembic runs migrations synchronously."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
