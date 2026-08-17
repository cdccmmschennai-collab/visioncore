from datetime import datetime

from pydantic import BaseModel


class UsageDaily(BaseModel):
    day: datetime
    input_tokens: int
    output_tokens: int
    cost_usd: float
    calls: int


class UsageSummary(BaseModel):
    model: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost_usd: float
    credit_budget_usd: float
    remaining_usd: float
    percent_used: float
    avg_latency_ms: int
    input_price_per_mtok: float
    output_price_per_mtok: float
    daily: list[UsageDaily]


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_tags: int
    total_batches: int
    total_uploads: int
    total_downloads: int
