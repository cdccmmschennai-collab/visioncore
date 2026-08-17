"""Gemini vision extraction provider for temporary/sample testing.

Uses Google's current `google-genai` SDK. The provider returns the same
ExtractionResult shape as ClaudeExtractor so the rest of VisionCore
(FastAPI/Celery/PostgreSQL/Excel/UI) does not need to change.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.config import settings
from app.services.claude_extractor import (
    ALLOWED_MEDIA_TYPES,
    SYSTEM_PROMPT,
    ExtractionError,
    _parse_json,
)
from app.services.fields import FIELDS, VALID_QUALITY, normalise_payload

logger = logging.getLogger(__name__)

#: Mirrors the schema described in SYSTEM_PROMPT. Passing this as
#: response_json_schema (rather than relying on response_mime_type alone)
#: makes Gemini use grammar-constrained decoding, so values containing raw
#: quote characters (e.g. a nameplate's 4" size mark) come back correctly
#: escaped instead of breaking the JSON.
_FIELD_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": "string"},
        "quality": {"type": "string", "enum": list(VALID_QUALITY)},
    },
    "required": ["value", "quality"],
}

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "object",
            "properties": {f.key: _FIELD_ENTRY_SCHEMA for f in FIELDS},
            "required": [f.key for f in FIELDS],
        },
        "remarks": {"type": "string"},
        "photo_status": {"type": "string", "enum": ["EASY", "MEDIUM", "HARD"]},
        "qc_comment": {"type": "string"},
    },
    "required": ["fields", "remarks", "photo_status", "qc_comment"],
}


@dataclass
class ExtractionResult:
    payload: dict
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * settings.gemini_input_price_per_mtok
            + self.output_tokens / 1_000_000 * settings.gemini_output_price_per_mtok
        )


def _encode_image_part(path: str | Path) -> types.Part:
    p = Path(path)
    media_type, _ = mimetypes.guess_type(p.name)
    if media_type not in ALLOWED_MEDIA_TYPES:
        media_type = "image/jpeg"
    return types.Part.from_bytes(
        data=p.read_bytes(),
        mime_type=media_type,
    )


class GeminiExtractor:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or settings.gemini_api_key
        if not key:
            raise ExtractionError(
                "GEMINI_API_KEY is not set. Add it to .env and restart the API."
            )
        self._client = genai.Client(api_key=key)
        self._model = model or settings.gemini_model

    async def extract(
        self, image_paths: list[str], tag_number: str, description: str
    ) -> ExtractionResult:
        if not image_paths:
            raise ExtractionError("No images supplied for extraction")

        contents: list[object] = []
        for index, path in enumerate(image_paths, start=1):
            contents.append(
                f"Photo {index} of {len(image_paths)}:"
            )
            contents.append(_encode_image_part(path))

        contents.append(
            f"""These photographs show the nameplate for asset tag
{tag_number} ({description}).

The tag number and equipment description are already known from the asset
register — copy them into the response unchanged and mark both Confirmed.
If a different tag number is printed on the plate, keep the register value
and flag the mismatch in remarks.

Return the JSON object now."""
        )

        started = time.perf_counter()
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_json_schema=_RESPONSE_SCHEMA,
                    max_output_tokens=settings.gemini_max_tokens,
                ),
            )
        except genai_errors.APIError as exc:
            logger.exception("Gemini API request failed")
            if exc.code == 429 or exc.status == "RESOURCE_EXHAUSTED":
                raise ExtractionError(
                    "Gemini's free-tier daily quota is exhausted for this API key. "
                    "It resets roughly every 24 hours. To keep working now, either "
                    "enable billing on the Google AI Studio project or set "
                    "AI_PROVIDER=claude in .env and restart the API."
                ) from exc
            raise ExtractionError(f"Gemini API error: {exc.status}. {exc.message}") from exc
        except Exception as exc:  # Google SDK has several provider-specific exception types.
            logger.exception("Gemini API request failed")
            raise ExtractionError(f"Gemini API error: {exc}") from exc
        finally:
            # The SDK client is lightweight and can be reused by the worker.
            pass

        latency_ms = int((time.perf_counter() - started) * 1000)
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise ExtractionError("Gemini returned an empty response")

        try:
            payload = normalise_payload(
                _parse_json(text), tag_number, description
            )
        except Exception as exc:
            raise ExtractionError(f"Could not parse Gemini JSON: {exc}") from exc

        usage = getattr(response, "usage_metadata", None)
        input_tokens = int(
            getattr(usage, "prompt_token_count", 0) or 0
        )
        output_tokens = int(
            getattr(usage, "candidates_token_count", 0) or 0
        )

        return ExtractionResult(
            payload=payload,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=self._model,
        )
