"""Estimated Organization Credits: purchased total minus tracked Anthropic usage.

Anthropic's official API has no endpoint for the account's actual credit
balance on Claude Console/Platform orgs — confirmed against their current
docs, which cover only historical usage and cost, nothing forward-looking
like a balance. So "Estimated Balance" is calculated here, not fetched:

    Estimated Balance = total_purchased_usd - tracked usage

`total_purchased_usd` is a running total an admin adds to via top-ups (see
app/api/v1/admin.py). Tracked usage comes from the same Cost Admin API that
already powers the Claude API Usage card — but that API only ever reports a
trailing ~31-day window, so summing it fresh on every read would silently
lose older days as they roll off. Instead each *closed* day (never today,
which is still accumulating) is folded into OrgCredits.ledger_usage_usd
exactly once, remembered via ledger_through_date, so the running total
survives past the 31-day window. Today's own cost is recomputed fresh on
every call (not persisted) so the estimate keeps moving through the day
without ever double-counting it once it closes.

Known limitation: if the ledger goes unadvanced for longer than the Cost
API's window (nobody loads the Admin page for 31+ days), the unrecorded days
in between age out of Anthropic's report before ever being folded in, and
that usage is permanently missed. This is disclosed rather than worked
around — there is no official way to recover usage older than the window.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import OrgCredits
from app.services.anthropic_usage import ClaudeUsageUnavailable, fetch_claude_usage_report


@dataclass
class LedgerAdvanceResult:
    #: Ledger total (closed days) plus today's still-open, unfolded cost.
    tracked_usage_usd: float
    #: Set when today's Anthropic fetch failed — the ledger itself is
    #: untouched, so tracked_usage_usd is still the last known-good figure.
    usage_error: str | None = None


async def advance_usage_ledger(row: OrgCredits) -> LedgerAdvanceResult:
    """Fold any newly-closed days of Anthropic spend into `row`'s ledger.

    Mutates `row` in place (caller is responsible for committing). Does not
    raise — an Anthropic fetch failure just means the ledger doesn't advance
    this time; the caller still gets the last successfully tracked amount.
    """
    try:
        result = await fetch_claude_usage_report(31)
    except ClaudeUsageUnavailable as exc:
        return LedgerAdvanceResult(tracked_usage_usd=row.ledger_usage_usd, usage_error=str(exc))

    today = datetime.now(timezone.utc).date()
    open_day_cost = 0.0
    for day_usage in sorted(result.daily, key=lambda d: d.day):
        if day_usage.day == today:
            open_day_cost = day_usage.cost_usd
            continue
        if day_usage.day > today:
            continue
        if row.ledger_through_date is not None and day_usage.day <= row.ledger_through_date:
            continue
        row.ledger_usage_usd += day_usage.cost_usd
        row.ledger_through_date = day_usage.day

    return LedgerAdvanceResult(tracked_usage_usd=row.ledger_usage_usd + open_day_cost)
