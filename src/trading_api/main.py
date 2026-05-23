from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from trading_api.schemas import AssetPayload, CacheStatus, HealthPayload, MarketPayload, RefreshSummaryPayload, RootPayload
from trading_api.service import MarketService
from trading_api.settings import AppSettings, JOBS

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

settings = AppSettings()
service = MarketService(settings)

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description=(
        "Trading API that refreshes Google Sheet market data, caches it, "
        "and serves clean stock, forex, and crypto endpoints."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def verify_refresh_token(
    token: Annotated[str | None, Query(alias="token", include_in_schema=False)] = None,
    x_refresh_token: Annotated[str | None, Header(alias="X-Refresh-Token")] = None,
) -> None:
    """Protect POST /refresh.

    The header form is preferred because query tokens can appear in logs. The
    query parameter remains accepted but hidden from OpenAPI for local fallback.
    """
    expected = settings.refresh_token
    if not expected:
        return
    provided = x_refresh_token or token
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.get("/", tags=["system"], response_model=RootPayload)
def root() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "status": "ok",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "cache_status": "/cache/status",
            "all_markets": "/markets",
            "stocks": "/markets/stocks",
            "id_stocks": "/markets/stocks/id",
            "mt5_stocks": "/markets/stocks/mt5",
            "forex": "/markets/forex",
            "crypto": "/markets/crypto",
            "refresh": "POST /refresh with X-Refresh-Token header",
            "refresh_forex": "POST /refresh/forex with X-Refresh-Token header",
            "refresh_crypto": "POST /refresh/crypto with X-Refresh-Token header",
            "refresh_id_stocks": "POST /refresh/stocks/id with X-Refresh-Token header",
            "refresh_mt5_stocks": "POST /refresh/stocks/mt5 with X-Refresh-Token header",
        },
    }


@app.get("/health", tags=["system"], response_model=HealthPayload)
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "api_version": settings.api_version,
        **service.cache_status(),
    }


@app.get("/cache/status", tags=["system"], response_model=CacheStatus)
def cache_status() -> dict[str, object]:
    return service.cache_status()


@app.post("/refresh", tags=["admin"], response_model=RefreshSummaryPayload)
def refresh(_: None = Depends(verify_refresh_token)) -> dict[str, object]:
    payload = service.refresh(export_excel=False)
    return service.refresh_summary(payload, refreshed_jobs=list(JOBS.keys()))


@app.post("/refresh/forex", tags=["admin"], response_model=RefreshSummaryPayload)
def refresh_forex(_: None = Depends(verify_refresh_token)) -> dict[str, object]:
    jobs = ["forex"]
    payload = service.refresh(export_excel=False, job_names=jobs, merge_existing=True)
    return service.refresh_summary(payload, refreshed_jobs=jobs)


@app.post("/refresh/crypto", tags=["admin"], response_model=RefreshSummaryPayload)
def refresh_crypto(_: None = Depends(verify_refresh_token)) -> dict[str, object]:
    jobs = ["crypto"]
    payload = service.refresh(export_excel=False, job_names=jobs, merge_existing=True)
    return service.refresh_summary(payload, refreshed_jobs=jobs)


@app.post("/refresh/stocks/id", tags=["admin"], response_model=RefreshSummaryPayload)
def refresh_id_stocks(_: None = Depends(verify_refresh_token)) -> dict[str, object]:
    jobs = ["id_stock"]
    payload = service.refresh(export_excel=False, job_names=jobs, merge_existing=True)
    return service.refresh_summary(payload, refreshed_jobs=jobs)


@app.post("/refresh/stocks/mt5", tags=["admin"], response_model=RefreshSummaryPayload)
def refresh_mt5_stocks(_: None = Depends(verify_refresh_token)) -> dict[str, object]:
    jobs = ["mt5_stock"]
    payload = service.refresh(export_excel=False, job_names=jobs, merge_existing=True)
    return service.refresh_summary(payload, refreshed_jobs=jobs)


@app.get("/markets", tags=["markets"], response_model=MarketPayload)
def markets(auto_refresh: bool = True) -> dict[str, object]:
    return service.get_payload(allow_auto_refresh=auto_refresh)


@app.get("/markets/stocks", tags=["markets"], response_model=AssetPayload)
def stocks(auto_refresh: bool = True) -> dict[str, object]:
    return service.get_asset("stocks", allow_auto_refresh=auto_refresh)


@app.get("/markets/stocks/mt5", tags=["markets"], response_model=AssetPayload)
def mt5_stocks(auto_refresh: bool = True) -> dict[str, object]:
    return service.get_asset("mt5_stock", allow_auto_refresh=auto_refresh)


@app.get("/markets/stocks/id", tags=["markets"], response_model=AssetPayload)
def id_stocks(auto_refresh: bool = True) -> dict[str, object]:
    return service.get_asset("id_stock", allow_auto_refresh=auto_refresh)


@app.get("/markets/forex", tags=["markets"], response_model=AssetPayload)
def forex(auto_refresh: bool = True) -> dict[str, object]:
    return service.get_asset("forex", allow_auto_refresh=auto_refresh)


@app.get("/markets/crypto", tags=["markets"], response_model=AssetPayload)
def crypto(auto_refresh: bool = True) -> dict[str, object]:
    return service.get_asset("crypto", allow_auto_refresh=auto_refresh)
