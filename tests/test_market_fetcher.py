from trading_api.market_fetcher import (
    dividend_yield_from_rate,
    dividend_yield_from_yfinance_info,
    normalize_dividend_yield_percent,
)


def test_dividend_yield_from_rate_uses_annual_dividend_over_price():
    assert round(dividend_yield_from_rate(1.05, 300), 2) == 0.35


def test_aapl_style_percent_under_one_stays_percent():
    assert normalize_dividend_yield_percent(0.35) == 0.35


def test_alv_style_ratio_under_point_one_becomes_percent():
    assert round(normalize_dividend_yield_percent(0.0443), 2) == 4.43


def test_yfinance_prefers_computed_dividend_yield_over_ambiguous_raw_field():
    info = {
        "currentPrice": 300,
        "dividendRate": 1.05,
        "dividendYield": 0.35,
    }
    assert round(dividend_yield_from_yfinance_info(info, {}), 2) == 0.35


from trading_api.market_fetcher import normalize_market_units


def test_lse_gbx_prices_are_normalized_to_gbp():
    data = {
        "Current Price": 13916,
        "Low 52W": 11800,
        "High 52W": 15000,
        "1Y Target": 14500,
        "Yield %": 1.69,
        "Market Cap": 123456789,
    }
    normalized = normalize_market_units("AZN.L", data)
    assert normalized["Current Price"] == 139.16
    assert normalized["Low 52W"] == 118.0
    assert normalized["High 52W"] == 150.0
    assert normalized["1Y Target"] == 145.0
    assert normalized["Yield %"] == 1.69
    assert normalized["Market Cap"] == 123456789


def test_lse_ratio_yield_is_normalized_to_percent():
    normalized = normalize_market_units("BATS.L", {"Yield %": 0.05025641})
    assert round(normalized["Yield %"], 6) == 5.025641


def test_non_lse_prices_are_not_scaled():
    normalized = normalize_market_units("AAPL", {"Current Price": 212.29, "Yield %": 0.35})
    assert normalized["Current Price"] == 212.29
    assert normalized["Yield %"] == 0.35
