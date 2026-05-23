from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from trading_api.settings import (
    EXACT_YAHOO_SYMBOL_MAP,
    EXCHANGE_SUFFIX_MAP,
    SPECIAL_CRYPTO_CANDIDATES,
    SPECIAL_FOREX_SYMBOLS,
)


def code_in_parentheses(raw: str) -> str | None:
    match = re.search(r"\(([\dA-Z]+)\)", str(raw).upper())
    return match.group(1) if match else None


def base_exchange(raw: str) -> tuple[str, str | None]:
    cleaned = str(raw).strip().upper()
    match = re.match(r"^([A-Z0-9]+)\.([A-Z0-9]+)", cleaned)
    return (match.group(1), match.group(2)) if match else (cleaned, None)


def normalize_mt5_stock(symbol: str) -> str | None:
    if not symbol or pd.isna(symbol):
        return None

    raw = str(symbol).strip().upper()
    if raw in EXACT_YAHOO_SYMBOL_MAP:
        return EXACT_YAHOO_SYMBOL_MAP[raw]

    yahoo_suffixes = (
        ".AX", ".L", ".MC", ".MI", ".AS", ".HE", ".PA", ".DE", ".SI", ".T", ".TO", ".V", ".SW", ".HK"
    )
    if raw.startswith("^") or raw.endswith(yahoo_suffixes):
        return raw

    base, exchange = base_exchange(raw)
    code = code_in_parentheses(raw)
    if exchange == "TSE" and code:
        return f"{code}.T"
    if exchange == "SGX" and code:
        return f"{code}.SI"
    if exchange in EXCHANGE_SUFFIX_MAP:
        return f"{base}{EXCHANGE_SUFFIX_MAP[exchange]}"
    return base


def normalize_forex(symbol: str) -> str | None:
    if not symbol or pd.isna(symbol):
        return None

    raw = str(symbol).upper().strip()
    cleaned = re.sub(r"[^A-Z]", "", raw)
    if not cleaned:
        return None
    if cleaned in SPECIAL_FOREX_SYMBOLS:
        return SPECIAL_FOREX_SYMBOLS[cleaned]
    if raw.endswith(("=X", "=F")):
        return raw
    if re.fullmatch(r"[A-Z]{6}", cleaned):
        return f"{cleaned}=X"
    return cleaned


def normalize_id_stock(symbol: str) -> str | None:
    if not symbol or pd.isna(symbol):
        return None
    cleaned = str(symbol).strip().upper().replace(" ", "")
    return cleaned if cleaned.endswith(".JK") else f"{cleaned}.JK"


def normalize_crypto_base(symbol: str) -> str | None:
    if not symbol or pd.isna(symbol):
        return None

    raw = str(symbol).upper().strip()
    raw = raw.replace("/", "").replace("-", "").replace("_", "").replace(" ", "")
    for suffix in ("USDT", "USD"):
        if raw.endswith(suffix) and len(raw) > len(suffix):
            raw = raw[: -len(suffix)]
            break
    return raw


def crypto_candidates(symbol: str) -> list[str]:
    base = normalize_crypto_base(symbol)
    if not base:
        return []
    special = SPECIAL_CRYPTO_CANDIDATES.get(base, [])
    common = [f"{base}-USD", f"{base}USD=X"]
    return list(dict.fromkeys(special + common))


def to_yahoo_symbols(raw_symbol: str, source_kind: str) -> list[str]:
    candidates: Iterable[str | None]
    if source_kind == "crypto":
        candidates = crypto_candidates(raw_symbol)
    elif source_kind == "forex":
        candidates = [normalize_forex(raw_symbol)]
    elif source_kind == "id_stock":
        candidates = [normalize_id_stock(raw_symbol)]
    else:
        candidates = [normalize_mt5_stock(raw_symbol)]
    return [candidate for candidate in candidates if candidate]
