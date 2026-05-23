from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from google.cloud import storage
except Exception:  # Optional. Only needed when GCS_CACHE_BUCKET is configured.
    storage = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_utc_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def cache_age_seconds(payload: dict[str, Any]) -> float | None:
    updated_at = parse_utc_iso(payload.get("updated_at"))
    if updated_at is None:
        return None
    return (datetime.now(timezone.utc) - updated_at).total_seconds()


def load_local_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read local cache %s: %s", path, exc)
        return None


def save_local_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_gcs_cache(bucket_name: str, blob_name: str) -> dict[str, Any] | None:
    if storage is None:
        logger.warning("google-cloud-storage is not installed; falling back to local cache only")
        return None
    try:
        blob = storage.Client().bucket(bucket_name).blob(blob_name)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read GCS cache gs://%s/%s: %s", bucket_name, blob_name, exc)
        return None


def save_gcs_cache(bucket_name: str, blob_name: str, payload: dict[str, Any]) -> None:
    if storage is None:
        raise RuntimeError("google-cloud-storage is not installed")
    blob = storage.Client().bucket(bucket_name).blob(blob_name)
    blob.upload_from_string(
        json.dumps(payload, indent=2, ensure_ascii=False),
        content_type="application/json",
    )


def load_cache(path: Path, gcs_bucket: str | None = None, gcs_blob: str | None = None) -> dict[str, Any] | None:
    """Load cache from GCS when configured, otherwise from local disk.

    GCS is recommended on Cloud Run because local /tmp is instance-local and
    can disappear after a cold start. Local cache remains useful for Docker and
    manual local testing.
    """
    if gcs_bucket and gcs_blob:
        payload = load_gcs_cache(gcs_bucket, gcs_blob)
        if payload is not None:
            return payload
    return load_local_cache(path)


def save_cache(path: Path, payload: dict[str, Any], gcs_bucket: str | None = None, gcs_blob: str | None = None) -> None:
    # Always save local cache as a fast same-instance fallback.
    save_local_cache(path, payload)
    if gcs_bucket and gcs_blob:
        save_gcs_cache(gcs_bucket, gcs_blob, payload)
