"""AI extraction provider selector.

`AI_PROVIDER=gemini` is intended for temporary/sample testing.
`AI_PROVIDER=claude` is the production/default provider.
"""
from app.core.config import settings
from app.services.claude_extractor import ClaudeExtractor, ExtractionError
from app.services.gemini_extractor import GeminiExtractor


def get_extractor():
    provider = settings.ai_provider.strip().lower()
    if provider == "gemini":
        return GeminiExtractor()
    if provider == "claude":
        return ClaudeExtractor()
    raise ExtractionError(
        f"Unsupported AI_PROVIDER={settings.ai_provider!r}. "
        "Use 'gemini' or 'claude'."
    )
