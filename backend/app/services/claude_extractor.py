"""Claude vision extraction for nameplate images.

All images belonging to one tag go into a *single* request. That matters: a
nameplate is often photographed two or three times because no single angle is
legible, and the model can only reconcile a glare-obscured serial in shot 1
against a clean read in shot 3 if it sees both at once.

The prompt asks for JSON only. Model output is still treated as untrusted —
`normalise_payload` in `fields.py` is what actually guarantees the shape.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    RateLimitError,
)

from app.core.config import settings
from app.services.fields import FIELDS, NOT_PRESENT, normalise_payload

logger = logging.getLogger(__name__)

#: Anthropic's vision endpoint accepts these media types only.
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class ExtractionError(RuntimeError):
    """Raised when extraction could not produce a usable payload."""


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
            self.input_tokens / 1_000_000 * settings.claude_input_price_per_mtok
            + self.output_tokens / 1_000_000 * settings.claude_output_price_per_mtok
        )


def _field_spec() -> str:
    return "\n".join(f'  - "{f.key}"  \u2014 {f.ai_label}' for f in FIELDS)


SYSTEM_PROMPT = f"""You are a data-capture specialist reading industrial equipment \
nameplates for an asset-register migration. Accuracy and honesty about legibility \
matter far more than completeness — a wrong value is worse than an admitted gap, \
because a wrong value gets trusted.

Return ONE JSON object and nothing else. No prose, no markdown fence.

Schema:
{{
  "fields": {{
    "<key>": {{ "value": "<string>", "quality": "Confirmed" | "Verify" }},
    ...
  }},
  "remarks": "<string>",
  "photo_status": "EASY" | "MEDIUM" | "HARD",
  "qc_comment": "<string>"
}}

Required keys under "fields":
{_field_spec()}

Rules:
1. Transcribe exactly what is printed. Do not correct, expand, or tidy \
manufacturer spellings, model codes, or serial numbers.
2. quality = "Confirmed" only when the characters are clearly legible and read \
directly off the plate. Use "Verify" for anything inferred, referenced from a \
logo or model code, worn, glared, partially obscured, or absent.
3. When a field is genuinely not printed on the nameplate, set value to exactly \
"{NOT_PRESENT}" and quality to "Verify".
4. Use UPPERCASE for short coded values (sizes, materials, classifications).
5. "year_of_manufacture" is YYYY, "month_of_manufacture" is MM. A date code such \
as "10/24" means month 10, year 2024 — record both and say so in remarks.
6. "additional_information": every remaining nameplate detail not already \
captured by one of the dedicated fields above, as "LABEL: value" pairs \
separated by ", " — body/trim materials, standards, pressure and temperature \
ratings, certificate numbers, calibration data, drawing numbers, supply \
voltages. Do not add an entry that merely restates a value already recorded \
in a dedicated field (e.g. no plain "MONTH: 02" or "YEAR: 2024" line, since \
those live in month_of_manufacture / year_of_manufacture). A composite code \
printed on the plate in its own right — such as a date code like "02/24" — \
is still transcribed once as printed, since it documents the plate's own \
notation, not a restatement.
7. "hazardous_classification": the full ATEX/IECEx marking including certificate \
numbers, ingress rating and temperature class, if present.
8. "remarks": a short note naming anything a human should check — what was \
illegible, what was inferred and from where, and any mismatch between the tag \
number in the filename and one printed on the plate. Empty string if nothing.
9. "photo_status": how hard the plate was to read — EASY, MEDIUM or HARD.
10. When several photos show the same plate, reconcile them and prefer the \
clearest reading of each field.
11. For "part_no", "serial_no", and "model": strip only the field's own \
printed label/abbreviation — "P/N:", "P/N.", "P/N-", "S/No.", "S.No:", "M/N", \
"Model:", "Ser. No", and similar — and record just the identifier that \
follows. Do not alter the identifier itself: keep every letter, digit, \
hyphen and slash that is part of the value, in the order printed. These \
identifiers are not necessarily numeric — "P/N: AB-123-CD" is "AB-123-CD", \
not a digits-only reading of it.
"""


def _encode_image(path: str | Path) -> dict:
    p = Path(path)
    media_type, _ = mimetypes.guess_type(p.name)
    # .jfif and friends resolve oddly across platforms; JPEG is the safe default.
    if media_type not in ALLOWED_MEDIA_TYPES:
        media_type = "image/jpeg"
    data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _parse_json(text: str) -> dict:
    """Recover the JSON object from the response, fence or no fence."""
    candidate = text.strip()
    fenced = _JSON_FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise ExtractionError("Claude did not return a JSON object")
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Could not parse Claude's JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ExtractionError("Claude returned JSON that was not an object")
    return parsed


class ClaudeExtractor:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ExtractionError(
                "ANTHROPIC_API_KEY is not set. Add it to .env and restart the API."
            )
        self._client = AsyncAnthropic(api_key=key, max_retries=2, timeout=120.0)
        self._model = model or settings.claude_model

    async def extract(
        self, image_paths: list[str], tag_number: str, description: str
    ) -> ExtractionResult:
        if not image_paths:
            raise ExtractionError("No images supplied for extraction")

        content: list[dict] = []
        for index, path in enumerate(image_paths, start=1):
            content.append({"type": "text", "text": f"Photo {index} of {len(image_paths)}:"})
            content.append(_encode_image(path))

        content.append({
            "type": "text",
            "text": (
                f"These photographs show the nameplate for asset tag "
                f"{tag_number} ({description}).\n"
                f"The tag number and equipment description are already known from "
                f"the asset register — copy them into the response unchanged and "
                f"mark both Confirmed. If a *different* tag number is printed on "
                f"the plate, keep the register value and flag the mismatch in "
                f"remarks.\n\nReturn the JSON object now."
            ),
        })

        started = time.perf_counter()
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=settings.claude_max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
        except RateLimitError as exc:
            raise ExtractionError(
                "Claude API rate limit reached. Wait a moment and retry this tag."
            ) from exc
        except APIConnectionError as exc:
            raise ExtractionError(f"Could not reach the Claude API: {exc}") from exc
        except APIStatusError as exc:
            detail = getattr(exc, "message", str(exc))
            raise ExtractionError(f"Claude API error ({exc.status_code}): {detail}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        if not text.strip():
            raise ExtractionError("Claude returned an empty response")

        payload = normalise_payload(_parse_json(text), tag_number, description)

        return ExtractionResult(
            payload=payload,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
            model=self._model,
        )
