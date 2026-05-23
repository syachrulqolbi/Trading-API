# `scripts/` folder

This folder is for helper commands and operational notes.

The main application does not depend on files in this folder. Keep production logic inside `src/trading_api/` so Cloud Run, CLI exports, and tests use the same source code.

## Most common commands

Run local API:

```bash
export PYTHONPATH=src
uvicorn trading_api.main:app --reload --host 0.0.0.0 --port 8080
```

Refresh all jobs without Excel:

```bash
python -m trading_api.cli --job all
```

Refresh all jobs and export Excel files:

```bash
python -m trading_api.cli --job all --excel
```

Refresh one job:

```bash
python -m trading_api.cli --job forex --excel
```

## Why old `run_*.py` scripts were replaced

The original version used separate entry files like `run_forex.py`, `run_crypto.py`, and `run_all.py`. This template replaces them with one command:

```bash
python -m trading_api.cli --job <job-name>
```

This is easier to deploy and maintain because all jobs share the same CLI.
