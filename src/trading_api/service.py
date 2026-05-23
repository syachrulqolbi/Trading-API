from __future__ import annotations

import logging
import threading
from typing import Any

from trading_api.cache import cache_age_seconds, load_cache, save_cache, utc_now_iso
from trading_api.settings import AppSettings, JOBS
from trading_api.sheets import process_job, save_excel

logger = logging.getLogger(__name__)

ASSET_KEYS = ["stocks", "mt5_stock", "id_stock", "forex", "crypto"]


def _max_timestamp(*values: str | None) -> str | None:
    cleaned = [value for value in values if value]
    return max(cleaned) if cleaned else None


def _updated_at_by_asset_from_payload(payload: dict[str, Any] | None) -> dict[str, str | None]:
    if not payload:
        return {key: None for key in ASSET_KEYS}

    existing = payload.get("updated_at_by_asset")
    fallback = payload.get("updated_at")
    if not isinstance(existing, dict):
        existing = {}

    result = {key: existing.get(key) for key in ASSET_KEYS}

    # Backward compatibility for older cache payloads that only had one
    # global updated_at value. If the old cache already has data, use the
    # global timestamp as a reasonable fallback until each split refresh runs.
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    for key in ["mt5_stock", "id_stock", "forex", "crypto"]:
        if result.get(key) is None and data.get(key):
            result[key] = fallback

    result["stocks"] = existing.get("stocks") or _max_timestamp(result.get("mt5_stock"), result.get("id_stock"))
    return result


class MarketService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings()
        self._lock = threading.Lock()
        self._cache: dict[str, Any] | None = load_cache(
            self.settings.cache_path,
            self.settings.gcs_cache_bucket,
            self.settings.gcs_cache_blob,
        )

    def cache_payload(self) -> dict[str, Any] | None:
        if self._cache is not None:
            return self._cache
        self._cache = load_cache(
            self.settings.cache_path,
            self.settings.gcs_cache_bucket,
            self.settings.gcs_cache_blob,
        )
        return self._cache

    def is_stale(self) -> bool:
        payload = self.cache_payload()
        if not payload:
            return True
        age = cache_age_seconds(payload)
        return age is None or age > self.settings.cache_ttl_seconds

    def get_payload(self, allow_auto_refresh: bool = True) -> dict[str, Any]:
        payload = self.cache_payload()
        should_refresh_empty = allow_auto_refresh and self.settings.auto_refresh_when_empty and not payload
        should_refresh_stale = allow_auto_refresh and self.settings.auto_refresh_when_stale and self.is_stale()
        if should_refresh_empty or should_refresh_stale:
            return self.refresh(export_excel=False, force=False)
        return payload or self.empty_payload()

    def cache_source(self) -> str:
        return "gcs" if self.settings.gcs_cache_bucket else "local"

    def cache_status(self) -> dict[str, Any]:
        payload = self.cache_payload()
        age = cache_age_seconds(payload) if payload else None
        return {
            "cache_loaded": payload is not None,
            "cache_source": self.cache_source(),
            "gcs_cache_bucket": self.settings.gcs_cache_bucket,
            "gcs_cache_blob": self.settings.gcs_cache_blob if self.settings.gcs_cache_bucket else None,
            "updated_at": payload.get("updated_at") if payload else None,
            "updated_at_by_asset": _updated_at_by_asset_from_payload(payload),
            "age_seconds": round(age, 2) if age is not None else None,
            "ttl_seconds": self.settings.cache_ttl_seconds,
            "cache_stale": self.is_stale(),
            "auto_refresh_when_empty": self.settings.auto_refresh_when_empty,
            "auto_refresh_when_stale": self.settings.auto_refresh_when_stale,
        }

    def empty_payload(self) -> dict[str, Any]:
        return {
            "status": "empty",
            "updated_at": None,
            "updated_at_by_asset": {key: None for key in ASSET_KEYS},
            "api_version": self.settings.api_version,
            "counts": {"stocks": 0, "mt5_stock": 0, "id_stock": 0, "forex": 0, "crypto": 0},
            "data": {"stocks": [], "mt5_stock": [], "id_stock": [], "forex": [], "crypto": []},
        }

    def refresh(
        self,
        export_excel: bool = False,
        job_names: list[str] | None = None,
        force: bool = True,
        merge_existing: bool = False,
    ) -> dict[str, Any]:
        selected_jobs = job_names or list(JOBS.keys())
        invalid = [name for name in selected_jobs if name not in JOBS]
        if invalid:
            raise ValueError(f"Unknown job(s): {invalid}. Valid jobs: {list(JOBS)}")

        with self._lock:
            # Public GET requests use force=False. Re-check the cache inside the
            # lock so two simultaneous stale requests do not both fetch Yahoo data.
            if not force and job_names is None:
                payload = self.cache_payload()
                if payload and not self.is_stale():
                    return payload

            existing_payload = self.cache_payload() if merge_existing else None
            if existing_payload and isinstance(existing_payload.get("data"), dict):
                existing_data = existing_payload.get("data", {})
                data = {
                    "stocks": list(existing_data.get("stocks", [])),
                    "mt5_stock": list(existing_data.get("mt5_stock", [])),
                    "id_stock": list(existing_data.get("id_stock", [])),
                    "forex": list(existing_data.get("forex", [])),
                    "crypto": list(existing_data.get("crypto", [])),
                }
            else:
                data = {"stocks": [], "mt5_stock": [], "id_stock": [], "forex": [], "crypto": []}

            updated_at_by_asset = _updated_at_by_asset_from_payload(existing_payload) if merge_existing else {key: None for key in ASSET_KEYS}
            excel_files: list[str] = []
            errors: list[dict[str, str]] = []

            for job_name in selected_jobs:
                job = JOBS[job_name]
                try:
                    df, records = process_job(job, self.settings)
                    job_updated_at = utc_now_iso()
                    data[job.name] = records
                    if job.asset_group == "stock":
                        data[job.name] = records
                        updated_at_by_asset[job.name] = job_updated_at
                    else:
                        data[job.asset_group] = records
                        updated_at_by_asset[job.asset_group] = job_updated_at
                    if export_excel:
                        output_path = save_excel(df, job, self.settings.output_dir)
                        excel_files.append(str(output_path))
                except Exception as exc:
                    logger.exception("Job failed: %s", job_name)
                    errors.append({"job": job_name, "error": str(exc)})

            data["stocks"] = list(data.get("mt5_stock", [])) + list(data.get("id_stock", []))
            updated_at_by_asset["stocks"] = _max_timestamp(
                updated_at_by_asset.get("mt5_stock"),
                updated_at_by_asset.get("id_stock"),
            )

            payload = {
                "status": "ok" if not errors else "partial_error",
                "updated_at": utc_now_iso(),
                "updated_at_by_asset": updated_at_by_asset,
                "api_version": self.settings.api_version,
                "source": "google_sheet" if self.settings.use_public_google_sheet else "local_excel",
                "cache_source": self.cache_source(),
                "counts": {
                    "stocks": len(data["stocks"]),
                    "mt5_stock": len(data["mt5_stock"]),
                    "id_stock": len(data["id_stock"]),
                    "forex": len(data["forex"]),
                    "crypto": len(data["crypto"]),
                },
                "data": data,
                "errors": errors,
            }
            if export_excel:
                payload["excel_files"] = excel_files

            self._cache = payload
            save_cache(
                self.settings.cache_path,
                payload,
                self.settings.gcs_cache_bucket,
                self.settings.gcs_cache_blob,
            )
            return payload

    def refresh_summary(self, payload: dict[str, Any], refreshed_jobs: list[str] | None = None) -> dict[str, Any]:
        summary = {
            "status": payload.get("status", "unknown"),
            "updated_at": payload.get("updated_at"),
            "updated_at_by_asset": payload.get("updated_at_by_asset", {}),
            "api_version": payload.get("api_version", self.settings.api_version),
            "source": payload.get("source"),
            "cache_source": payload.get("cache_source", self.cache_source()),
            "counts": payload.get("counts", {}),
            "errors": payload.get("errors", []),
        }
        if refreshed_jobs is not None:
            summary["refreshed_jobs"] = refreshed_jobs
        if "excel_files" in payload:
            summary["excel_files"] = payload.get("excel_files")
        return summary

    def get_asset(self, asset: str, allow_auto_refresh: bool = True) -> dict[str, Any]:
        payload = self.get_payload(allow_auto_refresh=allow_auto_refresh)
        data = payload.get("data", {})
        if asset not in data:
            raise KeyError(asset)
        updated_at_by_asset = _updated_at_by_asset_from_payload(payload)
        return {
            "updated_at": updated_at_by_asset.get(asset) or payload.get("updated_at"),
            "type": asset,
            "count": len(data.get(asset, [])),
            "data": data.get(asset, []),
        }
