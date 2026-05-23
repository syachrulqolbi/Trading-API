# Cloud Run Deployment Guide

This guide deploys the Trading API to Google Cloud Run with Cloud Storage cache, Secret Manager, and Cloud Scheduler.

## Target Architecture

```text
Google Sheets watchlist
        ↓
Cloud Scheduler refresh jobs
        ↓
Cloud Run trading-api service
        ↓
Cloud Storage JSON cache
        ↓
Trading dashboard / API consumers
```

## Recommended Refresh Strategy

Use split refresh jobs instead of one large refresh.

```text
00 min -> /refresh/forex
10 min -> /refresh/crypto
20 min -> /refresh/stocks/id
40 min -> /refresh/stocks/mt5
```

Public GET endpoints stay fast because they read from cache.

## PowerShell Variables

```powershell
$PROJECT_ID="personal-project-414620"
$REGION="asia-southeast1"
$SERVICE_NAME="trading-api"
$CACHE_BUCKET="$PROJECT_ID-trading-api-cache"
$SECRET_NAME="trading-api-refresh-token"
$REFRESH_TOKEN = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
$RUN_SA_NAME="trading-api-sa"
$RUN_SA="$RUN_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
$SECRET_ARG = "REFRESH_TOKEN=$($SECRET_NAME):latest"
```

## Enable Services

```powershell
gcloud.cmd config set project $PROJECT_ID

gcloud.cmd services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  cloudscheduler.googleapis.com `
  secretmanager.googleapis.com `
  storage.googleapis.com `
  iam.googleapis.com
```

## Service Account

```powershell
gcloud.cmd iam service-accounts describe $RUN_SA
```

If not found:

```powershell
gcloud.cmd iam service-accounts create $RUN_SA_NAME `
  --display-name "Trading API Cloud Run service account"
```

## Cloud Storage Cache

```powershell
gcloud.cmd storage buckets describe "gs://$CACHE_BUCKET"
```

If not found:

```powershell
gcloud.cmd storage buckets create "gs://$CACHE_BUCKET" `
  --location=$REGION `
  --uniform-bucket-level-access
```

Grant cache access:

```powershell
gcloud.cmd storage buckets add-iam-policy-binding "gs://$CACHE_BUCKET" `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/storage.objectAdmin"
```

## Secret Manager

```powershell
Set-Content -Path "refresh_token.txt" -Value $REFRESH_TOKEN -NoNewline
```

If secret does not exist:

```powershell
gcloud.cmd secrets create $SECRET_NAME --data-file="refresh_token.txt"
```

If secret exists:

```powershell
gcloud.cmd secrets versions add $SECRET_NAME --data-file="refresh_token.txt"
```

Clean local token file:

```powershell
Remove-Item "refresh_token.txt"
```

Grant secret access:

```powershell
gcloud.cmd secrets add-iam-policy-binding $SECRET_NAME `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/secretmanager.secretAccessor"
```

## Deploy Cloud Run Service

```powershell
gcloud.cmd run deploy $SERVICE_NAME `
  --source . `
  --region $REGION `
  --service-account $RUN_SA `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --min-instances 0 `
  --max-instances 1 `
  --concurrency 5 `
  --timeout 3600 `
  --set-env-vars "ENVIRONMENT=production,API_VERSION=1.0.0,AUTO_REFRESH_WHEN_EMPTY=true,AUTO_REFRESH_WHEN_STALE=false,CACHE_TTL_SECONDS=3600,GCS_CACHE_BUCKET=$CACHE_BUCKET,GCS_CACHE_BLOB=cache/trading_api_cache.json,REQUEST_SLEEP_SECONDS=0.15,ALLOWED_ORIGINS=*" `
  --set-secrets $SECRET_ARG
```

## Get Service URL

```powershell
$SERVICE_URL = gcloud.cmd run services describe $SERVICE_NAME `
  --region $REGION `
  --format "value(status.url)"

$SERVICE_URL
```

## Test With curl

Health:

```powershell
curl.exe "$SERVICE_URL/health"
```

Cache status:

```powershell
curl.exe "$SERVICE_URL/cache/status"
```

Refresh crypto:

```powershell
curl.exe -X POST "$SERVICE_URL/refresh/crypto" `
  -H "X-Refresh-Token: $REFRESH_TOKEN" `
  -H "Content-Type: application/json" `
  -d "{}" `
  -o refresh_crypto.json
```

Refresh forex:

```powershell
curl.exe -X POST "$SERVICE_URL/refresh/forex" `
  -H "X-Refresh-Token: $REFRESH_TOKEN" `
  -H "Content-Type: application/json" `
  -d "{}" `
  -o refresh_forex.json
```

Read cached markets:

```powershell
curl.exe "$SERVICE_URL/markets" -o markets.json
curl.exe "$SERVICE_URL/markets/crypto" -o crypto.json
curl.exe "$SERVICE_URL/markets/forex" -o forex.json
```

## Cloud Scheduler Jobs

Delete the old single full-refresh job if it exists:

```powershell
gcloud.cmd scheduler jobs delete trading-api-hourly-refresh --location $REGION
```

Create split refresh jobs:

```powershell
gcloud.cmd scheduler jobs create http trading-api-refresh-forex `
  --location $REGION `
  --schedule "0 * * * *" `
  --time-zone "Australia/Sydney" `
  --uri "$SERVICE_URL/refresh/forex" `
  --http-method POST `
  --headers "X-Refresh-Token=$REFRESH_TOKEN,Content-Type=application/json" `
  --message-body "{}" `
  --attempt-deadline 1800s
```

```powershell
gcloud.cmd scheduler jobs create http trading-api-refresh-crypto `
  --location $REGION `
  --schedule "10 * * * *" `
  --time-zone "Australia/Sydney" `
  --uri "$SERVICE_URL/refresh/crypto" `
  --http-method POST `
  --headers "X-Refresh-Token=$REFRESH_TOKEN,Content-Type=application/json" `
  --message-body "{}" `
  --attempt-deadline 1800s
```

```powershell
gcloud.cmd scheduler jobs create http trading-api-refresh-id-stock `
  --location $REGION `
  --schedule "20 * * * *" `
  --time-zone "Australia/Sydney" `
  --uri "$SERVICE_URL/refresh/stocks/id" `
  --http-method POST `
  --headers "X-Refresh-Token=$REFRESH_TOKEN,Content-Type=application/json" `
  --message-body "{}" `
  --attempt-deadline 1800s
```

```powershell
gcloud.cmd scheduler jobs create http trading-api-refresh-mt5-stock `
  --location $REGION `
  --schedule "40 * * * *" `
  --time-zone "Australia/Sydney" `
  --uri "$SERVICE_URL/refresh/stocks/mt5" `
  --http-method POST `
  --headers "X-Refresh-Token=$REFRESH_TOKEN,Content-Type=application/json" `
  --message-body "{}" `
  --attempt-deadline 1800s
```

Run one job manually:

```powershell
gcloud.cmd scheduler jobs run trading-api-refresh-crypto --location $REGION
```

## Custom Domain

Use a domain such as:

```text
api.sqnsportfolio.com
```

Map it to the Cloud Run service using your preferred Google Cloud domain method. After the domain works, restrict CORS:

```powershell
gcloud.cmd run services update $SERVICE_NAME `
  --region $REGION `
  --update-env-vars "ALLOWED_ORIGINS=https://sqnsportfolio.com,https://www.sqnsportfolio.com,https://api.sqnsportfolio.com"
```

## Logs

```powershell
gcloud.cmd run services logs read $SERVICE_NAME `
  --region $REGION `
  --limit 100
```


## Asset refresh timestamps

The API stores separate `updated_at_by_asset` values for `mt5_stock`, `id_stock`, `forex`, and `crypto`. Split Cloud Scheduler jobs update only the asset group they refresh, while `/markets` keeps a combined cache payload.
