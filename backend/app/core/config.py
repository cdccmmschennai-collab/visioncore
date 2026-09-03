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
    claude_max_tokens: int = Field(4096, alias="CLAUDE_MAX_TOKENS")
    claude_input_price_per_mtok: float = Field(3.00, alias="CLAUDE_INPUT_PRICE_PER_MTOK")
    claude_output_price_per_mtok: float = Field(15.00, alias="CLAUDE_OUTPUT_PRICE_PER_MTOK")
    # An Admin API key (`sk-ant-admin01-...`), distinct from the regular API
    # key above and only available to organization admins. Required for the
    # Admin page's Claude usage dashboard, which reads exclusively from
    # Anthropic's official Usage & Cost Admin API. Never sent to the
    # frontend. Leave blank and the dashboard reports itself unavailable
    # rather than showing any locally estimated figures.
    anthropic_admin_api_key: str = Field("", alias="ANTHROPIC_ADMIN_API_KEY")
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

    # ── Batch Process (browser-driven folder scan) ──────────────────────────
    # The "Batch Process" button on the New Batch page reads/writes a local
    # folder directly from the browser (File System Access API) rather than
    # from a server-local path, so it works the same whether the backend is
    # local or a remote deployment. It covers far more tags per run than a
    # normal drag-drop upload, hence the separate, higher ceiling.
    max_tags_per_batch_process: int = Field(50, alias="MAX_TAGS_PER_BATCH_PROCESS")

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
