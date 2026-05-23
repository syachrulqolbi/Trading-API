# Trading API

A production-style **FastAPI backend** that converts a Google Sheets trading watchlist into clean, cache-backed JSON endpoints for trading dashboards and market monitoring tools.

Built with **Python, FastAPI, Docker, Google Cloud Run, Cloud Scheduler, Cloud Storage, Secret Manager, yfinance, yahooquery, and pytest**.

---

## Overview

Trading API reads watchlist data from Google Sheets, normalizes symbols across different asset classes, fetches market data from Yahoo-compatible sources, and serves only the clean fields needed by a trading dashboard.

It supports:

- MT5 stock symbols
- Indonesian stocks
- Forex pairs
- Crypto pairs
- Commodities
- Major indices
- Optional Excel export for local/manual validation

The production API is designed to be **cache-first**, so repeated dashboard requests do not repeatedly call Yahoo Finance.

---

## Trading Data Features

- Converts spreadsheet-based trading watchlists into structured API responses.
- Supports stocks, Indonesian stocks, MT5 symbols, forex, crypto, commodities, and indices.
- Normalizes MT5/global symbols into Yahoo-compatible tickers.
- Normalizes LSE/UK stock prices from pence/GBX into pounds/GBP for cleaner MT5 comparison.
- Normalizes dividend yield into human percent format.
- Keeps only clean public fields in API responses and hides spreadsheet helper rows.
- Uses split refresh routes to avoid one large long-running refresh.
- Stores cache in Cloud Storage so Cloud Run cold starts can reuse the latest trading data.
- Protects refresh routes with `X-Refresh-Token`.
- Keeps Excel export available for manual checking without affecting production deployment.
- Includes Docker, Cloud Run deployment docs, folder-level READMEs, and tests.

---

## Tech Stack

| Area | Technology |
|---|---|
| Backend API | FastAPI, Python |
| Data source | Google Sheets CSV export |
| Market data | yfinance, yahooquery |
| Runtime | Docker |
| Deployment | Google Cloud Run |
| Scheduled refresh | Google Cloud Scheduler |
| Persistent cache | Google Cloud Storage |
| Secret handling | Google Secret Manager |
| Testing | pytest |
| Optional manual output | Excel via openpyxl |

---

## Architecture

```text
Hostinger DNS
├── sqnsportfolio.com       -> Cloud Run website service
├── www.sqnsportfolio.com   -> Cloud Run website service
└── api.sqnsportfolio.com   -> Cloud Run trading API service

Google Cloud
├── Cloud Run               -> FastAPI container
├── Cloud Scheduler         -> Split refresh jobs
├── Cloud Storage           -> Persistent JSON cache
└── Secret Manager          -> Refresh token
```

---

## Cache Strategy

Production cache behavior is controlled by:

```text
CACHE_TTL_SECONDS=3600
AUTO_REFRESH_WHEN_EMPTY=true
AUTO_REFRESH_WHEN_STALE=false
GCS_CACHE_BUCKET=<your-cache-bucket>
```

Expected behavior:

```text
Public GET request          -> reads cache quickly
Split scheduler refresh     -> refreshes one asset group at a time
updated_at_by_asset         -> stores separate refresh time per asset group
Cloud Run cold start        -> loads existing cache from Cloud Storage
Manual refresh endpoint     -> protected by X-Refresh-Token
```

This keeps the API responsive and reduces unnecessary calls to Yahoo Finance.

---

## Public Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API metadata and quick links |
| `GET` | `/health` | Health check |
| `GET` | `/cache/status` | Cache age, freshness, and source status |
| `GET` | `/markets` | Full combined market payload |
| `GET` | `/markets/stocks` | All stock data |
| `GET` | `/markets/stocks/id` | Indonesian stock data |
| `GET` | `/markets/stocks/mt5` | MT5/global stock data |
| `GET` | `/markets/forex` | Forex data |
| `GET` | `/markets/crypto` | Crypto data |
| `POST` | `/refresh` | Protected full refresh endpoint |
| `POST` | `/refresh/forex` | Protected forex refresh endpoint |
| `POST` | `/refresh/crypto` | Protected crypto refresh endpoint |
| `POST` | `/refresh/stocks/id` | Protected Indonesian stock refresh endpoint |
| `POST` | `/refresh/stocks/mt5` | Protected MT5/global stock refresh endpoint |

Manual refresh requires this header:

```text
X-Refresh-Token: <secret-token>
```

---

## Public API Output Columns

### Stocks

`/markets/stocks`, `/markets/stocks/id`, and `/markets/stocks/mt5` return:

```text
symbol
Current Price
Annual Return % (5Y)
Yield %
Market Cap
Low 52W
High 52W
P/E Ratio
EPS
1Y Target
```

### Forex and Crypto

`/markets/forex` and `/markets/crypto` return:

```text
symbol
Current Price
Low 52W
High 52W
```

---

## Example Response

```json
{
  "status": "ok",
  "updated_at": "2026-05-17T11:00:00Z",
  "updated_at_by_asset": {
    "stocks": "2026-05-17T11:00:00Z",
    "mt5_stock": "2026-05-17T10:40:00Z",
    "id_stock": "2026-05-17T10:20:00Z",
    "forex": "2026-05-17T10:00:00Z",
    "crypto": "2026-05-17T10:10:00Z"
  },
  "api_version": "1.0.0",
  "source": "google_sheet",
  "counts": {
    "stocks": 42,
    "mt5_stock": 20,
    "id_stock": 22,
    "forex": 40,
    "crypto": 30
  },
  "data": {
    "mt5_stock": [
      {
        "symbol": "AZN.LSE",
        "Current Price": 139.16,
        "Yield %": 1.6959,
        "Low 52W": 118.0,
        "High 52W": 150.0
      }
    ],
    "forex": [
      {
        "symbol": "EURUSD",
        "Current Price": 1.1631,
        "Low 52W": 1.1227,
        "High 52W": 1.2024
      }
    ],
    "crypto": [
      {
        "symbol": "BTCUSD",
        "Current Price": 78431.35,
        "Low 52W": 60074.2,
        "High 52W": 126198.07
      }
    ]
  }
}
```

---

## Repository Structure

```text
Trading/
├── src/
│   └── trading_api/
│       ├── main.py              # FastAPI routes and CORS
│       ├── schemas.py           # Pydantic response models for OpenAPI docs
│       ├── service.py           # Refresh and cache orchestration
│       ├── cache.py             # Local + Cloud Storage JSON cache
│       ├── sheets.py            # Google Sheet / Excel loading and public row shaping
│       ├── market_fetcher.py    # Yahoo Finance / yahooquery fetch logic
│       ├── symbols.py           # Symbol normalization
│       ├── settings.py          # Environment config, jobs, sheet IDs, symbol maps
│       └── cli.py               # Manual refresh / Excel export CLI
├── docs/                        # Deployment and operations notes
├── scripts/                     # Helper scripts and command examples
├── data/                        # Optional local Excel input; not committed
├── outputs/                     # Optional Excel/JSON output; not committed
├── tests/                       # Unit tests
├── Dockerfile                   # Cloud Run container
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development and test dependencies
├── .env.example                 # Environment template
├── .gcloudignore                # Files excluded from gcloud source deploy
├── .dockerignore                # Files excluded from Docker build context
└── README.md
```

---

## Local Docker Usage

### Build the image

```powershell
docker rm -f trading-api
docker build --no-cache -t trading-api .
```

### Run the API locally

```powershell
docker run --rm --name trading-api -p 8080:8080 `
  -e REFRESH_TOKEN="test-token" `
  -e API_VERSION="1.0.0" `
  -e AUTO_REFRESH_WHEN_EMPTY="true" `
  -e AUTO_REFRESH_WHEN_STALE="false" `
  -e CACHE_TTL_SECONDS="3600" `
  -e REQUEST_SLEEP_SECONDS="0.15" `
  trading-api
```

Open the interactive API docs:

```text
http://localhost:8080/docs
```

### Refresh local data with curl

```powershell
curl.exe -X POST "http://localhost:8080/refresh/crypto" `
  -H "X-Refresh-Token: test-token" `
  -H "Content-Type: application/json" `
  -d "{}" `
  -o outputs/refresh_crypto_local.json
```

### Check cached output

```powershell
curl.exe "http://localhost:8080/markets" -o outputs/markets_local.json
curl.exe "http://localhost:8080/markets/stocks/mt5" -o outputs/mt5_stock_local.json
curl.exe "http://localhost:8080/markets/stocks/id" -o outputs/id_stock_local.json
curl.exe "http://localhost:8080/markets/forex" -o outputs/forex_local.json
curl.exe "http://localhost:8080/markets/crypto" -o outputs/crypto_local.json
```

---

## Manual Excel Export

Deployment does not generate Excel files. Excel output is only for local/manual validation.

```powershell
docker run --rm `
  -e EXPORT_OUTPUT_DIR="/app/outputs" `
  -v "${PWD}/outputs:/app/outputs" `
  trading-api `
  python -m trading_api.cli --job all --excel
```

Generated files are saved in:

```text
outputs/
```

---

## Deployment

Full Cloud Run deployment instructions are available in:

```text
docs/cloud-run-deployment.md
```

Production services:

```text
Cloud Run service: trading-api
Cloud Scheduler: split hourly refresh jobs
Cloud Storage: persistent JSON cache
Secret Manager: refresh token
Hostinger DNS: api.sqnsportfolio.com -> Cloud Run trading API service
```

Recommended deployment settings:

```text
region=asia-southeast1
min-instances=0
max-instances=1
memory=2Gi
cpu=2
concurrency=5
timeout=3600
CACHE_TTL_SECONDS=3600
AUTO_REFRESH_WHEN_EMPTY=true
AUTO_REFRESH_WHEN_STALE=false
```

---

## Environment Variables

| Variable | Default | Purpose |
|---|---:|---|
| `APP_NAME` | `Trading API` | Swagger/OpenAPI title. |
| `API_VERSION` | `1.0.0` | API version string. |
| `ENVIRONMENT` | `local` | Runtime label. |
| `GOOGLE_SHEET_ID` | empty/example | Source Google Sheet ID. |
| `USE_PUBLIC_GOOGLE_SHEET` | `true` | Reads Google Sheet CSV export when enabled. |
| `LOCAL_INPUT_XLSX` | `data/trading.xlsx` | Optional local Excel input. |
| `REFRESH_TOKEN` | empty | Protects refresh endpoints. Use Secret Manager in production. |
| `CACHE_FILE` | `/tmp/trading_api_cache.json` | Local same-instance cache path. |
| `CACHE_TTL_SECONDS` | `3600` | One-hour cache window. |
| `AUTO_REFRESH_WHEN_EMPTY` | `true` | Refresh if cache is empty. |
| `AUTO_REFRESH_WHEN_STALE` | `false` | Keep public GET routes cache-first. |
| `GCS_CACHE_BUCKET` | empty | Cloud Storage cache bucket for Cloud Run. |
| `GCS_CACHE_BLOB` | `cache/trading_api_cache.json` | Cache object path in Cloud Storage. |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins. Use your website domains in production. |
| `REQUEST_SLEEP_SECONDS` | `0.25` | Delay between Yahoo requests to reduce rate-limit pressure. |
| `EXPORT_OUTPUT_DIR` | `outputs` | Manual Excel output folder. |

---

## Testing

```powershell
pip install -r requirements-dev.txt
pytest -q
```

---

## Production Notes

1. Keep `REFRESH_TOKEN` in Secret Manager, not in GitHub.
2. Keep `max-instances=1` at first to avoid duplicate refresh jobs and keep Yahoo Finance usage predictable.
3. Use Cloud Storage cache for Cloud Run because local `/tmp` can disappear after cold starts.
4. Use split refresh routes instead of one large full refresh.
5. Use curl for long-running manual refresh calls.
6. If Yahoo Finance temporarily fails, the API should return `partial_error` instead of crashing the service.
7. Treat market data as delayed/best-effort data, not guaranteed real-time pricing.

---

## Disclaimer

Market data is fetched from Yahoo-compatible public sources and may be delayed, incomplete, or temporarily unavailable.

This API does not provide financial advice, trading advice, or investment recommendations.
