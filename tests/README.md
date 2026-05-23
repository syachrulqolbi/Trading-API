# `tests/` folder

This folder contains automated tests.

## Run tests

```bash
pytest -q
```

## Current coverage

The template includes tests for symbol normalization because bad symbol conversion usually causes most fetch failures.

## Suggested future tests

- Mock `yfinance` and test `market_fetcher.py` without internet.
- Test `public_records_from_dataframe()` returns only allowed public columns.
- Test `/refresh` requires token when `REFRESH_TOKEN` is set.
- Test `/markets/stocks` response format.

## Test design rule

Keep tests independent from live Yahoo or Google Sheet data. External network tests can be flaky and slow. Use mocks for reliable CI.
