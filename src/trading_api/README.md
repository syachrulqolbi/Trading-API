# `trading_api` package

Core Python package for the Trading API.

## Modules

| File | Purpose |
|---|---|
| `main.py` | FastAPI application, routes, CORS, refresh-token validation. |
| `schemas.py` | Pydantic response models for cleaner OpenAPI documentation. |
| `service.py` | Orchestrates refresh jobs, cache loading/saving, and asset-specific responses. |
| `cache.py` | JSON cache helpers for local `/tmp` and Google Cloud Storage. |
| `sheets.py` | Loads Google Sheet/Excel data, fills market columns, and shapes public records. |
| `market_fetcher.py` | Fetches market data from Yahoo Finance through `yfinance` and `yahooquery`. |
| `symbols.py` | Converts raw sheet symbols into Yahoo-compatible symbols. |
| `settings.py` | Application settings, environment variables, sheet jobs, and symbol maps. |
| `cli.py` | Local/manual refresh tool and optional Excel exporter. |

## Design notes

The deployment path does not need Excel output. Excel export is preserved only for manual checking:

```powershell
python -m trading_api.cli --job all --excel
```

Public API endpoints use cached JSON and only expose selected fields required by the trading dashboard.
