"""AI extraction provider selector.

Claude is the sole extraction provider.
"""
from app.services.claude_extractor import ClaudeExtractor


def get_extractor():
    return ClaudeExtractor()
