from datetime import datetime

from pydantic import BaseModel, Field

from app.models.claude_config import Team


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


class ClaudeConfigOut(BaseModel):
    """Never carries the real key — only a masked preview, or null when the
    team has no configuration at all yet. See app/services/claude_config.py."""
    team: Team
    masked_key: str | None
    status: str  # "Configured" | "Not Configured"
    updated_at: datetime | None


class ClaudeConfigUpdate(BaseModel):
    api_key: str = Field(min_length=16, max_length=200)


class ClaudeConfigTestResult(BaseModel):
    success: bool
    message: str


class TeamUsageRow(BaseModel):
    team: Team
    extractions: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class TeamUsageSummary(BaseModel):
    """Team-level usage from VisionCore's own api_usage table — distinct
    from ClaudeUsageSummary above, which is Anthropic's org-wide official
    report and has no concept of team."""
    teams: list[TeamUsageRow]
