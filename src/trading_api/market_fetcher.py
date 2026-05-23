from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import yfinance as yf

try:
    from yahooquery import Ticker as YahooQueryTicker
except Exception:  # yahooquery is optional fallback only
    YahooQueryTicker = None

logger = logging.getLogger(__name__)

FUNDAMENTAL_COLUMNS = {"Yield %", "Market Cap", "P/E Ratio", "EPS", "1Y Target"}

LSE_PRICE_COLUMNS = {"Current Price", "Low 52W", "High 52W", "1Y Target"}


def is_lse_yahoo_symbol(symbol: str) -> bool:
    """Return True for London Stock Exchange Yahoo symbols.

    Yahoo Finance commonly returns LSE ordinary share prices in pence/GBX.
    The API normalizes these price-like fields to pounds/GBP so they match
    typical MT5 position prices and are easier to compare in trading reports.
    """
    cleaned = str(symbol).strip().upper()
    return cleaned.endswith(".L") and not cleaned.startswith("^")


def normalize_market_units(symbol: str, data: dict[str, Any]) -> dict[str, Any]:
    """Normalize exchange-specific units after all data sources are merged."""
    normalized = dict(data)

    if is_lse_yahoo_symbol(symbol):
        for column in LSE_PRICE_COLUMNS:
            value = safe_float(normalized.get(column))
            if value is not None:
                normalized[column] = value / 100

        # Some LSE dividend yields are returned as ratios, for example
        # 0.0407 for 4.07%. Keep already-normalized values unchanged.
        yield_value = safe_float(normalized.get("Yield %"))
        if yield_value is not None and 0 < yield_value <= 0.20:
            normalized["Yield %"] = yield_value * 100

    return normalized



def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            value = (
                value.replace(",", "")
                .replace("$", "")
                .replace("%", "")
                .replace("Rp", "")
                .strip()
            )
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def first_non_null(*values: Any) -> Any | None:
    for value in values:
        if value is not None and value != "":
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            return value
    return None


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalize_percent(value: Any) -> float | None:
    """Normalize ordinary ratio-style percentage fields.

    This is still useful for fields that are consistently returned as ratios,
    for example 0.0443 -> 4.43. Dividend yield is handled separately below
    because Yahoo/yfinance can return it inconsistently across tickers.
    """
    value = safe_float(value)
    if value is None:
        return None
    return value * 100 if abs(value) <= 1 else value


def normalize_dividend_yield_percent(value: Any) -> float | None:
    """Normalize dividend yield into human percent units.

    Yahoo/yfinance can return dividend yield inconsistently:
    - AAPL-like case: 0.35 means 0.35%, not 35%.
    - ALV-like case: 0.0443 means 4.43%.

    Because the same field can be either a percent value or a ratio, this
    function only treats very small values as ratios. For a stronger answer,
    use dividend_rate / current_price first via dividend_yield_from_rate().
    """
    value = safe_float(value)
    if value is None or value < 0:
        return None
    if value <= 0.10:
        return value * 100
    return value


def dividend_yield_from_rate(dividend_rate: Any, current_price: Any) -> float | None:
    rate = safe_float(dividend_rate)
    price = safe_float(current_price)
    if rate is None or price is None or price <= 0 or rate < 0:
        return None
    yield_percent = (rate / price) * 100
    if yield_percent < 0 or yield_percent > 100:
        return None
    return yield_percent


def dividend_yield_from_yfinance_info(info: dict[str, Any], fast: dict[str, Any]) -> float | None:
    current_price = first_non_null(
        info.get("currentPrice"),
        info.get("regularMarketPrice"),
        fast.get("lastPrice"),
        fast.get("regularMarketPrice"),
    )

    # Prefer annual dividend amount divided by current price. This avoids the
    # AAPL 0.35 -> 35 bug when dividendYield is already returned as percent.
    annual_dividend_rate = first_non_null(
        info.get("dividendRate"),
        info.get("trailingAnnualDividendRate"),
    )
    computed = dividend_yield_from_rate(annual_dividend_rate, current_price)
    if computed is not None:
        return computed

    # Fallback fields. trailingAnnualDividendYield is usually ratio-style;
    # dividendYield/yield can be either ratio-style or percent-style.
    trailing_yield = safe_float(info.get("trailingAnnualDividendYield"))
    if trailing_yield is not None and trailing_yield >= 0:
        return trailing_yield * 100 if trailing_yield <= 1 else trailing_yield

    return normalize_dividend_yield_percent(first_non_null(info.get("dividendYield"), info.get("yield")))


def dividend_yield_from_yahooquery_data(
    price: dict[str, Any],
    detail: dict[str, Any],
    financial: dict[str, Any],
) -> float | None:
    current_price = first_non_null(price.get("regularMarketPrice"), financial.get("currentPrice"))
    annual_dividend_rate = first_non_null(detail.get("dividendRate"), financial.get("dividendRate"))
    computed = dividend_yield_from_rate(annual_dividend_rate, current_price)
    if computed is not None:
        return computed
    return normalize_dividend_yield_percent(detail.get("dividendYield"))


def history_safe(ticker: yf.Ticker, periods: tuple[str, ...] = ("5y", "2y", "1y", "1mo", "5d")) -> pd.DataFrame:
    for period in periods:
        try:
            hist = ticker.history(period=period, auto_adjust=False)
            if hist is not None and not hist.empty:
                return hist
        except Exception as exc:
            logger.debug("History fetch failed for period=%s: %s", period, exc)
    return pd.DataFrame()


def annual_return_from_history(hist: pd.DataFrame) -> float | None:
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None
    close = hist["Close"].dropna()
    if len(close) < 2:
        return None

    start = safe_float(close.iloc[0])
    end = safe_float(close.iloc[-1])
    if start is None or end is None or start <= 0:
        return None

    days = (close.index[-1] - close.index[0]).days
    years = days / 365.25 if days > 0 else None
    if not years:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


def _price_data_from_history(hist: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if hist is None or hist.empty:
        return result

    if "Current Price" in columns and "Close" in hist.columns:
        close = hist["Close"].dropna()
        if not close.empty:
            result["Current Price"] = safe_float(close.iloc[-1])

    hist_52w = hist.tail(252) if len(hist) >= 252 else hist
    if "Low 52W" in columns and "Low" in hist_52w.columns:
        result["Low 52W"] = safe_float(hist_52w["Low"].min())
    if "High 52W" in columns and "High" in hist_52w.columns:
        result["High 52W"] = safe_float(hist_52w["High"].max())
    if "Annual Return % (5Y)" in columns:
        result["Annual Return % (5Y)"] = annual_return_from_history(hist)

    return result


def _info_data_from_yfinance(ticker: yf.Ticker, columns: list[str]) -> dict[str, Any]:
    needs_fundamentals = bool(FUNDAMENTAL_COLUMNS.intersection(columns))
    if not needs_fundamentals and "Current Price" not in columns and "Low 52W" not in columns and "High 52W" not in columns:
        return {}

    try:
        info = ticker.get_info()
    except Exception:
        try:
            info = ticker.info
        except Exception:
            info = {}
    info = as_dict(info)

    try:
        fast = as_dict(dict(ticker.fast_info))
    except Exception:
        fast = {}

    return {
        "Current Price": first_non_null(info.get("currentPrice"), info.get("regularMarketPrice"), fast.get("lastPrice"), fast.get("regularMarketPrice")),
        "Yield %": dividend_yield_from_yfinance_info(info, fast) if "Yield %" in columns else None,
        "Market Cap": first_non_null(info.get("marketCap"), fast.get("marketCap")) if "Market Cap" in columns else None,
        "Low 52W": first_non_null(info.get("fiftyTwoWeekLow"), fast.get("yearLow")) if "Low 52W" in columns else None,
        "High 52W": first_non_null(info.get("fiftyTwoWeekHigh"), fast.get("yearHigh")) if "High 52W" in columns else None,
        "P/E Ratio": first_non_null(info.get("trailingPE"), info.get("forwardPE")) if "P/E Ratio" in columns else None,
        "EPS": first_non_null(info.get("trailingEps"), info.get("forwardEps")) if "EPS" in columns else None,
        "1Y Target": first_non_null(info.get("targetMeanPrice"), info.get("oneYearTargetPrice")) if "1Y Target" in columns else None,
    }


def fetch_yfinance(symbol: str, columns: list[str]) -> dict[str, Any]:
    result = {column: None for column in columns}
    try:
        ticker = yf.Ticker(symbol)
        history_data = _price_data_from_history(history_safe(ticker), columns)
        info_data = _info_data_from_yfinance(ticker, columns)
        result.update({key: first_non_null(history_data.get(key), info_data.get(key)) for key in columns})
    except Exception as exc:
        logger.warning("yfinance failed for %s: %s", symbol, exc)
    return result


def fetch_yahooquery(symbol: str, columns: list[str]) -> dict[str, Any]:
    result = {column: None for column in columns}
    if YahooQueryTicker is None:
        return result

    try:
        ticker = YahooQueryTicker(symbol)
        price = as_dict(getattr(ticker, "price", {}).get(symbol, {}))
        detail = as_dict(getattr(ticker, "summary_detail", {}).get(symbol, {}))
        financial = as_dict(getattr(ticker, "financial_data", {}).get(symbol, {}))
        stats = as_dict(getattr(ticker, "key_stats", {}).get(symbol, {}))

        result.update(
            {
                "Current Price": first_non_null(price.get("regularMarketPrice"), financial.get("currentPrice")),
                "Yield %": dividend_yield_from_yahooquery_data(price, detail, financial) if "Yield %" in columns else None,
                "Market Cap": price.get("marketCap") if "Market Cap" in columns else None,
                "Low 52W": detail.get("fiftyTwoWeekLow") if "Low 52W" in columns else None,
                "High 52W": detail.get("fiftyTwoWeekHigh") if "High 52W" in columns else None,
                "P/E Ratio": first_non_null(detail.get("trailingPE"), detail.get("forwardPE")) if "P/E Ratio" in columns else None,
                "EPS": first_non_null(stats.get("trailingEps"), financial.get("currentEps")) if "EPS" in columns else None,
                "1Y Target": financial.get("targetMeanPrice") if "1Y Target" in columns else None,
            }
        )
    except Exception as exc:
        logger.warning("yahooquery failed for %s: %s", symbol, exc)

    return {column: result.get(column) for column in columns}


def merge_data(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    keys = set(primary) | set(fallback)
    return {key: first_non_null(primary.get(key), fallback.get(key)) for key in keys}
