# Docs

This folder contains operational notes for the Trading API.

## Files

- `cloud-run-deployment.md` — Cloud Run deployment, Secret Manager, Cloud Storage cache, Cloud Scheduler, and custom domain planning.

## Recommended Deployment

```text
frontend service -> sqnsportfolio.com
trading-api      -> api.sqnsportfolio.com
```


## Asset refresh timestamps

The API stores separate `updated_at_by_asset` values for `mt5_stock`, `id_stock`, `forex`, and `crypto`. Split Cloud Scheduler jobs update only the asset group they refresh, while `/markets` keeps a combined cache payload.
