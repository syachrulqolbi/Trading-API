from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StockRecord(BaseModel):
    """Public stock record used by the trading dashboard."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    current_price: float | int | None = Field(default=None, alias="Current Price")
    annual_return_5y: float | int | None = Field(default=None, alias="Annual Return % (5Y)")
    yield_percent: float | int | None = Field(default=None, alias="Yield %")
    market_cap: float | int | None = Field(default=None, alias="Market Cap")
    low_52w: float | int | None = Field(default=None, alias="Low 52W")
    high_52w: float | int | None = Field(default=None, alias="High 52W")
    pe_ratio: float | int | None = Field(default=None, alias="P/E Ratio")
    eps: float | int | None = Field(default=None, alias="EPS")
    one_year_target: float | int | None = Field(default=None, alias="1Y Target")


class BasicMarketRecord(BaseModel):
    """Public forex/crypto record used by the trading dashboard."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    current_price: float | int | None = Field(default=None, alias="Current Price")
    low_52w: float | int | None = Field(default=None, alias="Low 52W")
    high_52w: float | int | None = Field(default=None, alias="High 52W")


class Counts(BaseModel):
    stocks: int = 0
    mt5_stock: int = 0
    id_stock: int = 0
    forex: int = 0
    crypto: int = 0


class ErrorItem(BaseModel):
    job: str
    error: str


class MarketData(BaseModel):
    stocks: list[dict[str, Any]] = Field(default_factory=list)
    mt5_stock: list[dict[str, Any]] = Field(default_factory=list)
    id_stock: list[dict[str, Any]] = Field(default_factory=list)
    forex: list[dict[str, Any]] = Field(default_factory=list)
    crypto: list[dict[str, Any]] = Field(default_factory=list)


class MarketPayload(BaseModel):
    status: str
    updated_at: str | None = None
    updated_at_by_asset: dict[str, str | None] = Field(default_factory=dict)
    api_version: str
    source: str | None = None
    cache_source: str | None = None
    counts: Counts
    data: MarketData
    errors: list[ErrorItem] = Field(default_factory=list)


class AssetPayload(BaseModel):
    updated_at: str | None = None
    type: str
    count: int
    data: list[dict[str, Any]] = Field(default_factory=list)


class RefreshPayload(MarketPayload):
    excel_files: list[str] | None = None


class RefreshSummaryPayload(BaseModel):
    status: str
    updated_at: str | None = None
    updated_at_by_asset: dict[str, str | None] = Field(default_factory=dict)
    api_version: str
    source: str | None = None
    cache_source: str | None = None
    counts: Counts
    errors: list[ErrorItem] = Field(default_factory=list)
    refreshed_jobs: list[str] | None = None
    excel_files: list[str] | None = None


class CacheStatus(BaseModel):
    cache_loaded: bool
    cache_source: str
    gcs_cache_bucket: str | None = None
    gcs_cache_blob: str | None = None
    updated_at: str | None = None
    updated_at_by_asset: dict[str, str | None] = Field(default_factory=dict)
    age_seconds: float | None = None
    ttl_seconds: int
    cache_stale: bool
    auto_refresh_when_empty: bool
    auto_refresh_when_stale: bool


class HealthPayload(BaseModel):
    status: str
    api_version: str
    cache_loaded: bool
    cache_source: str
    gcs_cache_bucket: str | None = None
    gcs_cache_blob: str | None = None
    updated_at: str | None = None
    updated_at_by_asset: dict[str, str | None] = Field(default_factory=dict)
    age_seconds: float | None = None
    ttl_seconds: int
    cache_stale: bool
    auto_refresh_when_empty: bool
    auto_refresh_when_stale: bool


class RootPayload(BaseModel):
    name: str
    version: str
    status: str
    docs: str
    endpoints: dict[str, str]
