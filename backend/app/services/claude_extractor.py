"""Claude vision extraction for nameplate images.

All images belonging to one tag go into a *single* request. That matters: a
nameplate is often photographed two or three times because no single angle is
legible, and the model can only reconcile a glare-obscured serial in shot 1
against a clean read in shot 3 if it sees both at once.

The prompt asks for JSON only. Model output is still treated as untrusted —
`normalise_payload` in `fields.py` is what actually guarantees the shape.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
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
from app.services.fields import (
    FIELDS,
    NOT_PRESENT,
    normalise_payload,
    reconcile_description,
    reconcile_tag_number,
)
from app.services.image_optimizer import ALLOWED_MEDIA_TYPES, prepare_images_for_claude

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class ExtractionError(RuntimeError):
    """Raised when extraction could not produce a usable payload.

    `retryable` distinguishes a transient failure (rate limit, timeout,
    connection drop, 5xx) worth an automatic retry from a permanent one (bad
    request, corrupt image, unparseable response) that never will succeed no
    matter how many times it's retried. Defaults to False so every existing
    raise site (bad JSON, no images supplied) stays non-retryable unless
    explicitly marked otherwise.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


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
voltages. Before adding any entry, check it against every dedicated field's \
captured value (size_dimension, hazardous_classification, year/month of \
manufacture, and all others) and omit it if it already appears there in any \
form — do not restate a value already recorded in a dedicated field (e.g. no \
plain "MONTH: 02" or "YEAR: 2024" line, since those live in \
month_of_manufacture / year_of_manufacture; no "CLASS: 150RF" line if that \
class was already folded into size_dimension per rule 12). A composite code \
printed on the plate in its own right — such as a date code like "02/24" — \
is still transcribed once as printed, since it documents the plate's own \
notation, not a restatement.
7. "hazardous_classification": capture the complete classification exactly as \
printed, in full — the ATEX/IECEx marking including certificate numbers, \
ingress rating, temperature class, and group/category markings, if present. \
Pay particular attention to markings starting "EX" (e.g. "EX II 2GD C \
LCIE"): transcribe the entire string verbatim. Never shorten, split, or move \
any part of it to additional_information.
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
12. "size_dimension": capture the size together with any class, pressure \
rating, or schedule printed immediately alongside it, as one value — e.g. a \
plate reading 3/4" 150RF becomes size_dimension = "3/4\" 150RF". Never split \
them, and never move the class/rating half into additional_information.
13. "description": the plain equipment/item name — e.g. "BALL VALVE", "GATE \
VALVE", "GLOBE VALVE", "BUTTERFLY VALVE", "PUMP", "MOTOR", "COMPRESSOR", \
"PRESSURE GAUGE" — never a full nameplate transcription. Identify it from \
what type of item is visibly photographed, using any type name printed on \
the plate as confirmation. quality = "Confirmed" only when the equipment \
type is unambiguous from the photo or a printed label; "Verify" if you are \
inferring it from limited visual cues.

Before returning the JSON, validate: size_dimension includes its class/rating; \
no dedicated field's value is repeated in additional_information; and \
hazardous_classification holds the complete "EX..." string unmodified.
"""


def _image_block(optimized) -> dict:
    data = base64.standard_b64encode(optimized.data).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": optimized.media_type, "data": data},
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
        self._client = AsyncAnthropic(
            api_key=key, max_retries=settings.claude_sdk_max_retries, timeout=120.0
        )
        self._model = model or settings.claude_model

    async def extract(
        self, image_paths: list[str], tag_number: str, description: str
    ) -> ExtractionResult:
        if not image_paths:
            raise ExtractionError("No images supplied for extraction")

        # Compression/optimization happens fully here, BEFORE anything is
        # base64-encoded or handed to the Anthropic client — never send the
        # originals first and shrink them after the fact. Each photo is
        # optimized (and validated) individually; only if the tag's combined
        # payload would still be oversized does this tighten the largest
        # photo(s) further — see image_optimizer.prepare_images_for_claude.
        # Off the event loop: reading multi-MB files and, for large photos,
        # resizing/re-encoding them in Pillow are blocking calls that would
        # otherwise stall every other coroutine (DB queries, other tags'
        # progress polling) for their duration. One call for the whole tag,
        # not one per photo, so the combined-payload check sees every photo
        # in the tag at once rather than one at a time.
        optimized_images = await asyncio.to_thread(
            prepare_images_for_claude, [Path(p) for p in image_paths]
        )

        content: list[dict] = []
        payload_bytes = 0
        for index, optimized in enumerate(optimized_images, start=1):
            content.append({"type": "text", "text": f"Photo {index} of {len(optimized_images)}:"})
            content.append(_image_block(optimized))
            payload_bytes += optimized.final_bytes

        registered_as = f"tag number {tag_number} ({description})" if description else f"tag number {tag_number}"
        description_instruction = (
            "" if description else (
                " The register has no equipment description for this tag yet — "
                "determine \"description\" yourself from the photo(s), per rule 13.\n"
            )
        )
        content.append({
            "type": "text",
            "text": (
                f"These photographs show a nameplate. For reference only, the "
                f"batch register currently files these photos under {registered_as} "
                f"— you do not need to match it.\n"
                f"Read \"tag_number\" independently, straight off the physical "
                f"plate in the photo(s), the same way you read every other "
                f"field. Quality \"Confirmed\" only if it's clearly legible; "
                f"\"Verify\" if uncertain or damaged. If no tag number is "
                f"printed on the plate at all, set value to exactly "
                f"\"{NOT_PRESENT}\" and quality \"Verify\".\n"
                f"{description_instruction}\n"
                f"Return the JSON object now."
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
                "Claude API rate limit reached. Wait a moment and retry this tag.",
                retryable=True,
            ) from exc
        except APIConnectionError as exc:      # includes APITimeoutError
            raise ExtractionError(
                f"Could not reach the Claude API: {exc}", retryable=True
            ) from exc
        except APIStatusError as exc:
            detail = getattr(exc, "message", str(exc))
            # A 4xx is a bad request (malformed image, bad params) that will
            # never succeed on retry; a 5xx/overload is the API's own
            # transient trouble, worth retrying.
            raise ExtractionError(
                f"Claude API error ({exc.status_code}): {detail}",
                retryable=exc.status_code >= 500,
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        if not text.strip():
            # Never seen bare "the model said nothing" without a reason —
            # log enough to actually diagnose it next time (stop_reason,
            # token usage, what kind of content blocks came back, and this
            # request's photo count/payload size) without logging the image
            # bytes themselves or any secret. stop_reason == "max_tokens"
            # with no visible text usually means the response was cut off
            # before any JSON was emitted; other stop reasons point at a
            # genuinely empty/filtered generation instead.
            block_types = [getattr(block, "type", "?") for block in response.content]
            logger.warning(
                "Claude returned no text for tag %s: stop_reason=%s, "
                "output_tokens=%s, input_tokens=%s, content_block_types=%s, "
                "photos=%d, optimized_payload_bytes=%d, model=%s",
                tag_number, response.stop_reason, response.usage.output_tokens,
                response.usage.input_tokens, block_types, len(optimized_images),
                payload_bytes, self._model,
            )
            # Treat as retryable (bounded by the caller's existing
            # extraction_max_retries) rather than failing the tag outright —
            # an empty generation is far more often a one-off API hiccup
            # than a deterministic "this request can never succeed" case,
            # especially now that the request itself is pre-validated and
            # size-budgeted above. It is NOT retried without limit: the
            # outer loop in pipeline.py.process_item still gives up after
            # extraction_max_retries attempts.
            raise ExtractionError("Claude returned an empty response", retryable=True)

        raw = _parse_json(text)
        final_tag_number, tag_number_quality = reconcile_tag_number(raw, tag_number)
        final_description, description_quality = reconcile_description(raw, description)
        payload = normalise_payload(
            raw, final_tag_number, final_description,
            tag_number_quality=tag_number_quality, description_quality=description_quality,
        )

        return ExtractionResult(
            payload=payload,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
            model=self._model,
        )
