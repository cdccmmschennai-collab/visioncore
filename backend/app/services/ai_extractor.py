"""AI extraction provider selector.

Claude is the sole extraction provider. The API key is resolved per-team, at
call time, from the encrypted configuration in claude_api_configs (see
app/services/claude_config.py) — never cached process-wide, so a key an
Admin just rotated takes effect on the very next extraction, correctly, even
if that extraction runs in a separate Celery worker process. Building an
AsyncAnthropic client is cheap (no eager connection), so this costs nothing
worth caching for.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Team
from app.services.claude_config import ClaudeConfigError, get_decrypted_key
from app.services.claude_extractor import ClaudeExtractor, ExtractionError


async def get_extractor(db: AsyncSession, team: Team) -> tuple[ClaudeExtractor, int]:
    """Returns (extractor, claude_config_id) for `team`.

    Raises ExtractionError (non-retryable) if the team has no active Claude
    API configuration — callers must let this fail the item rather than
    falling back to another team's key. Reuses the exact same exception
    type/handling every other extraction failure already goes through (see
    app/services/pipeline.py's process_item).
    """
    try:
        api_key, config_id = await get_decrypted_key(db, team)
    except ClaudeConfigError as exc:
        raise ExtractionError(
            f"{exc} Extraction cannot start. Please contact an administrator."
        ) from exc
    return ClaudeExtractor(api_key=api_key), config_id
