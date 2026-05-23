from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Any

import pandas as pd

from trading_api.market_fetcher import fetch_yahooquery, fetch_yfinance, merge_data, normalize_market_units, safe_float
from trading_api.settings import AppSettings, SheetJob
from trading_api.symbols import to_yahoo_symbols

logger = logging.getLogger(__name__)


def google_sheet_csv_url(sheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized = {str(column).strip().lower(): column for column in df.columns}
    for alias in aliases:
        found = normalized.get(alias.strip().lower())
        if found is not None:
            return str(found)
    return None


def load_sheet(job: SheetJob, settings: AppSettings) -> pd.DataFrame:
    if settings.use_public_google_sheet:
        url = google_sheet_csv_url(settings.google_sheet_id, job.gid)
        logger.info("Loading Google Sheet CSV for %s", job.name)
        df = pd.read_csv(url, header=job.header_row)
    else:
        path = Path(settings.local_input_xlsx)
        logger.info("Loading local Excel for %s from %s", job.name, path)
        df = pd.read_excel(path, sheet_name=job.local_sheet_name, header=job.header_row)

    df.columns = [str(column).strip() for column in df.columns]
    return df


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Ensure output columns exist and can safely receive numeric values.

    Google Sheets often returns empty/placeholder columns as string dtype.
    Pandas can then reject assigning floats into those columns. Casting the
    output columns to object keeps the dataframe flexible for API and Excel use.
    """
    for column in columns:
        if column not in df.columns:
            df[column] = pd.Series([None] * len(df), dtype="object")
        else:
            df[column] = df[column].astype("object")
    return df


INVALID_SYMBOL_LABELS = {"coeff", "coefficient"}


def valid_symbol_mask(df: pd.DataFrame, symbol_col: str) -> pd.Series:
    symbol_values = df[symbol_col].astype("string").str.strip()
    lowered = symbol_values.str.lower()
    mask = df[symbol_col].notna() & symbol_values.ne("")
    return (
        mask
        & ~lowered.str.contains("total", na=False)
        & ~lowered.isin(INVALID_SYMBOL_LABELS)
    )


def fetch_first_valid(raw_symbol: str, job: SheetJob) -> dict[str, Any]:
    for yahoo_symbol in to_yahoo_symbols(raw_symbol, job.source_kind):
        logger.info("Fetching %s as %s", raw_symbol, yahoo_symbol)
        data = fetch_yfinance(yahoo_symbol, job.market_columns)
        if job.use_yahooquery_fallback:
            data = merge_data(data, fetch_yahooquery(yahoo_symbol, job.market_columns))
        data = normalize_market_units(yahoo_symbol, data)
        if any(value is not None for value in data.values()):
            return data
    return {column: None for column in job.market_columns}


def fill_job_dataframe(df: pd.DataFrame, job: SheetJob, settings: AppSettings) -> pd.DataFrame:
    df = df.copy()
    symbol_col = find_column(df, job.symbol_aliases)
    if symbol_col is None:
        raise ValueError(f"Could not find symbol column for job={job.name}. Loaded columns: {list(df.columns)}")

    df = ensure_columns(df, job.all_output_columns)
    allocation_values: list[tuple[int, float]] = []

    for idx in df.index[valid_symbol_mask(df, symbol_col)]:
        raw_symbol = str(df.at[idx, symbol_col]).strip()
        data = fetch_first_valid(raw_symbol, job)
        for column, value in data.items():
            if column in df.columns:
                df.at[idx, column] = value

        if job.source_kind == "id_stock":
            lot = safe_float(df.at[idx, "Lot"]) if "Lot" in df.columns else None
            avg_price = safe_float(df.at[idx, "Avg Price"]) if "Avg Price" in df.columns else None
            if lot is not None and avg_price is not None:
                df.at[idx, "Position Value"] = lot * avg_price
            position_value = safe_float(df.at[idx, "Position Value"]) if "Position Value" in df.columns else None
            if position_value is not None:
                allocation_values.append((idx, position_value))

        if settings.request_sleep_seconds > 0:
            time.sleep(settings.request_sleep_seconds)

    if job.source_kind == "id_stock":
        total = sum(value for _, value in allocation_values)
        if total > 0:
            for idx, value in allocation_values:
                df.at[idx, "Allocation %"] = (value / total) * 100

    return df


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        abs_value = abs(value)
        if abs_value >= 1000:
            return round(value, 2)
        if abs_value >= 1:
            return round(value, 4)
        return round(value, 8)
    return value


def public_records_from_dataframe(df: pd.DataFrame, job: SheetJob) -> list[dict[str, Any]]:
    symbol_col = find_column(df, job.symbol_aliases)
    if symbol_col is None:
        return []

    records: list[dict[str, Any]] = []
    public_columns = [column for column in job.public_columns if column in df.columns]
    for idx in df.index[valid_symbol_mask(df, symbol_col)]:
        row: dict[str, Any] = {"symbol": str(df.at[idx, symbol_col]).strip()}
        for column in public_columns:
            row[column] = clean_value(df.at[idx, column])

        # Hide footer/helper rows from the public API. Example: a "Coeff" row
        # from the sheet should not be returned if no market data was found.
        if any(row.get(column) is not None for column in public_columns):
            records.append(row)
    return records


def process_job(job: SheetJob, settings: AppSettings) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    raw_df = load_sheet(job, settings)
    filled_df = fill_job_dataframe(raw_df, job, settings)
    public_records = public_records_from_dataframe(filled_df, job)
    return filled_df, public_records


def save_excel(df: pd.DataFrame, job: SheetJob, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / job.output_xlsx
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=job.local_sheet_name, index=False)
    return output_path
