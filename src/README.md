# `src/` folder

This folder contains the application source code.

The package uses the `src` layout, which is a professional Python project structure that keeps application code separate from project files such as `README.md`, `Dockerfile`, `docs/`, and tests.

## Main package

```text
src/trading_api/
```

This is the importable Python package used by both the FastAPI server and the command-line tools.

## Local import setup

When running commands locally from the repo root, set:

```bash
export PYTHONPATH=src
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
```

Cloud Run already sets this in the `Dockerfile`:

```dockerfile
ENV PYTHONPATH=/app/src
```

## Why this structure is useful

- Keeps deployment code clean.
- Makes imports predictable.
- Makes testing easier.
- Avoids mixing generated Excel files with source code.
- Makes the repo easier to reuse as a GitHub template.
