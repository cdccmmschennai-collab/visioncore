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
    """The organization's available Claude API credit balance — a value an
    admin manually entered from the Claude Console, not fetched or
    calculated. `None` fields mean it has never been set.
    """
    amount_usd: float | None
    amount_inr: float | None
    usd_to_inr_rate: float
    updated_at: datetime | None


class OrgCreditsUpdate(BaseModel):
    amount_usd: float = Field(ge=0)


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_tags: int
    total_batches: int
    total_uploads: int
    total_downloads: int
