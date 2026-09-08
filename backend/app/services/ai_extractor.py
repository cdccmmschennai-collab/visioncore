"""AI extraction provider selector.

Claude is the sole extraction provider. One shared AsyncAnthropic client (and
its underlying HTTP connection pool) is reused across every concurrent
extraction — see app/services/pipeline.py's semaphore-bounded worker pool —
instead of opening a new client per tag.
"""
from app.services.claude_extractor import ClaudeExtractor

_extractor: ClaudeExtractor | None = None


def get_extractor() -> ClaudeExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ClaudeExtractor()
    return _extractor
