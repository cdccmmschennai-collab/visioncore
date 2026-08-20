"""Claude usage/cost data for the Admin dashboard, sourced *entirely* from
Anthropic's official Usage & Cost Admin API
(https://api.anthropic.com/v1/organizations/usage_report/messages and
/cost_report) — no local PostgreSQL usage records are read here.

This requires an Admin API key (`sk-ant-admin01-...`), a different credential
from ANTHROPIC_API_KEY, only available to organization admins. It stays on
the backend and is never sent to the frontend.

Anthropic's official API does not expose everything the Console UI shows —
notably no account credit balance and no derivable "usage percentage" (the
Spend Limits API that would supply that is Claude Enterprise-only, not
available to Claude Console/Platform organizations). Those are reported as
unavailable rather than approximated from anything else. Per-request latency
and call success/failure counts also aren't in this API, but VisionCore can
still show them from its own request logs — see VisionCoreApiUsage instead.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_ADMIN_API_BASE = "https://api.anthropic.com/v1/organizations"
_ANTHROPIC_VERSION = "2023-06-01"
_MAX_DAYS = 31  # Usage/Cost API's max window at 1-day bucket granularity

#: Metrics with no official grounding at all — no Anthropic endpoint exposes
#: them for a Claude Console/Platform organization (confirmed: the Spend
#: Limits API that covers credits/budget is Claude Enterprise-only). Kept as
#: a list (rather than deleted) so a future genuinely-unavailable metric has
#: a place to go; currently empty because "Usage percentage" and "Remaining
#: credits / budget" were replaced by the admin-entered Organization Credits
#: card (see OrgCredits) instead of being shown as bare "unavailable" cards.
UNAVAILABLE_METRICS: list[str] = []


class ClaudeUsageUnavailable(Exception):
    """Raised with a safe, user-facing reason the report could not be fetched."""


@dataclass
class ClaudeModelTotal:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ClaudeDayUsage:
    day: date
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class ClaudeUsageResult:
    daily: list[ClaudeDayUsage]
    by_model: list[ClaudeModelTotal]
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float


async def fetch_claude_usage_report(days: int) -> ClaudeUsageResult:
    """Fetch and aggregate the usage + cost reports for the last `days` days.

    Raises ClaudeUsageUnavailable (never a raw exception) when the report
    can't be produced — no admin key configured, network failure, or a
    non-2xx response from Anthropic.
    """
    if not settings.anthropic_admin_api_key:
        raise ClaudeUsageUnavailable(
            "ANTHROPIC_ADMIN_API_KEY is not configured on the backend."
        )

    window = min(max(days, 1), _MAX_DAYS)
    ending_at = datetime.now(timezone.utc).replace(microsecond=0)
    starting_at = ending_at - timedelta(days=window)
    starting_str = starting_at.isoformat().replace("+00:00", "Z")
    ending_str = ending_at.isoformat().replace("+00:00", "Z")

    headers = {
        "x-api-key": settings.anthropic_admin_api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
    }
    usage_params = [
        ("starting_at", starting_str), ("ending_at", ending_str),
        ("bucket_width", "1d"), ("limit", str(window)),
        ("group_by[]", "model"),
    ]
    cost_params = [
        ("starting_at", starting_str), ("ending_at", ending_str),
        ("bucket_width", "1d"), ("limit", str(window)),
    ]

    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            usage_resp, cost_resp = await asyncio.gather(
                client.get(f"{_ADMIN_API_BASE}/usage_report/messages", params=usage_params),
                client.get(f"{_ADMIN_API_BASE}/cost_report", params=cost_params),
            )
            usage_resp.raise_for_status()
            cost_resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Anthropic Usage & Cost API returned an error: %s", exc)
        raise ClaudeUsageUnavailable(
            f"Anthropic's API returned HTTP {exc.response.status_code}. "
            "Check that ANTHROPIC_ADMIN_API_KEY is valid and has usage/cost read access."
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("Anthropic Usage & Cost API request failed: %s", exc)
        raise ClaudeUsageUnavailable(
            f"Could not reach Anthropic's API ({exc.__class__.__name__})."
        ) from exc

    days_map: dict[date, ClaudeDayUsage] = {}
    model_totals: dict[str, ClaudeModelTotal] = {}

    for bucket in usage_resp.json().get("data", []):
        day = _bucket_date(bucket["starting_at"])
        day_entry = days_map.setdefault(day, ClaudeDayUsage(day=day))
        for row in bucket.get("results", []):
            cache_creation = row.get("cache_creation") or {}
            row_input = (
                row.get("uncached_input_tokens", 0)
                + row.get("cache_read_input_tokens", 0)
                + cache_creation.get("ephemeral_1h_input_tokens", 0)
                + cache_creation.get("ephemeral_5m_input_tokens", 0)
            )
            row_output = row.get("output_tokens", 0)
            day_entry.input_tokens += row_input
            day_entry.output_tokens += row_output

            model_name = row.get("model") or "unknown"
            model_entry = model_totals.setdefault(model_name, ClaudeModelTotal(model=model_name))
            model_entry.input_tokens += row_input
            model_entry.output_tokens += row_output

    for bucket in cost_resp.json().get("data", []):
        day = _bucket_date(bucket["starting_at"])
        day_entry = days_map.setdefault(day, ClaudeDayUsage(day=day))
        for row in bucket.get("results", []):
            # `amount` is a decimal string in the currency's lowest unit
            # (cents for USD), e.g. "123.45" == $1.2345.
            day_entry.cost_usd += float(row.get("amount") or 0) / 100

    daily = sorted(days_map.values(), key=lambda d: d.day)
    by_model = sorted(model_totals.values(), key=lambda m: -(m.input_tokens + m.output_tokens))

    return ClaudeUsageResult(
        daily=daily,
        by_model=by_model,
        total_input_tokens=sum(d.input_tokens for d in daily),
        total_output_tokens=sum(d.output_tokens for d in daily),
        total_cost_usd=sum(d.cost_usd for d in daily),
    )


def _bucket_date(starting_at: str) -> date:
    return datetime.fromisoformat(starting_at.replace("Z", "+00:00")).date()
