import time

import pandas as pd

from trading_api.service import MarketService
from trading_api.settings import AppSettings


def test_split_refresh_keeps_separate_asset_timestamps(monkeypatch, tmp_path):
    def fake_process_job(job, settings):
        if job.asset_group == "stock":
            records = [{"symbol": job.name, "Current Price": 1.0}]
        else:
            records = [{"symbol": job.name, "Current Price": 1.0, "Low 52W": 0.5, "High 52W": 2.0}]
        return pd.DataFrame(records), records

    monkeypatch.setattr("trading_api.service.process_job", fake_process_job)

    settings = AppSettings(cache_file=str(tmp_path / "cache.json"), gcs_cache_bucket=None)
    service = MarketService(settings)

    forex_payload = service.refresh(job_names=["forex"], merge_existing=True)
    forex_updated_at = forex_payload["updated_at_by_asset"]["forex"]

    time.sleep(0.01)
    crypto_payload = service.refresh(job_names=["crypto"], merge_existing=True)

    assert crypto_payload["updated_at_by_asset"]["forex"] == forex_updated_at
    assert crypto_payload["updated_at_by_asset"]["crypto"] != forex_updated_at
    assert crypto_payload["updated_at_by_asset"]["mt5_stock"] is None
    assert crypto_payload["updated_at_by_asset"]["id_stock"] is None
