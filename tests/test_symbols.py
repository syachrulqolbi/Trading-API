from trading_api.symbols import normalize_crypto_base, normalize_forex, normalize_id_stock, normalize_mt5_stock, to_yahoo_symbols


def test_id_stock_adds_jk_suffix():
    assert normalize_id_stock("BBCA") == "BBCA.JK"
    assert normalize_id_stock("BBCA.JK") == "BBCA.JK"


def test_forex_adds_yahoo_suffix():
    assert normalize_forex("EURUSD") == "EURUSD=X"
    assert normalize_forex("XAUUSD") == "GC=F"


def test_crypto_candidates():
    assert normalize_crypto_base("BTC/USDT") == "BTC"
    assert "BTC-USD" in to_yahoo_symbols("BTC/USDT", "crypto")


def test_mt5_exact_map():
    assert normalize_mt5_stock("AUS200 (AXJO)") == "^AXJO"
    assert normalize_mt5_stock("ASML.EAS") == "ASML.AS"
