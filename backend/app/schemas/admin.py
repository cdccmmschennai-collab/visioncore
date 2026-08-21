from datetime import datetime

from pydantic import BaseModel, Field


class ClaudeModelUsage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ClaudeUsageDaily(BaseModel):
    day: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class ClaudeUsageSummary(BaseModel):
    """Claude usage/cost, sourced entirely from Anthropic's official Usage &
    Cost Admin API. When `available` is False, every numeric/list field is
    empty — the frontend must show `error` rather than treat zeros as data.
    """
    available: bool
    error: str | None = None
    generated_at: datetime
    window_days: int
    configured_model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost_usd: float
    #: Pure USD -> INR display conversion of total_cost_usd. Not data
    #: Anthropic returns — always render it labeled as a conversion.
    total_cost_inr: float
    usd_to_inr_rate: float
    by_model: list[ClaudeModelUsage]
    daily: list[ClaudeUsageDaily]
    #: Console metrics Anthropic's official API does not expose, so the
    #: frontend can label them "unavailable" instead of ever inventing them.
    unavailable_metrics: list[str]
    #: Configured spend-warning threshold and whether official USD spend has
    #: reached it. Both derived only from total_cost_usd above.
    spend_warning_threshold_usd: float
    spend_warning_triggered: bool


class OrgCreditsOut(BaseModel):
    """Estimated Organization Credits: total purchased minus Anthropic's own
    reported usage, tracked in a ledger (see services/org_credits.py) so the
    estimate survives Anthropic's Cost API's ~31-day reporting window. This
    is a calculated estimate, never Anthropic's own account balance — no
    such balance endpoint exists. `estimated_balance_*` are `None` only when
    no credits have ever been recorded.
    """
    total_purchased_usd: float
    tracked_usage_usd: float
    estimated_balance_usd: float | None
    estimated_balance_inr: float | None
    usd_to_inr_rate: float
    updated_at: datetime | None
    #: Set when today's latest Anthropic usage couldn't be fetched — the
    #: estimate shown is still the last successfully tracked one, not fake
    #: or zeroed data.
    usage_error: str | None = None


class OrgCreditsTopUp(BaseModel):
    """A credit purchase/top-up — added to the running total, never overwrites it."""
    top_up_usd: float = Field(gt=0)


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_tags: int
    total_batches: int
    total_uploads: int
    total_downloads: int
