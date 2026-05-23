from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class AppSettings:
    app_name: str = os.getenv("APP_NAME", "Trading API")
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    environment: str = os.getenv("ENVIRONMENT", "local")

    google_sheet_id: str = os.getenv(
        "GOOGLE_SHEET_ID",
        "1o1exoHTCrfG45V-mLuaDNPhMt_yWwAuGl06bLZYD_Kk",
    )
    use_public_google_sheet: bool = _env_bool("USE_PUBLIC_GOOGLE_SHEET", True)
    local_input_xlsx: str = os.getenv("LOCAL_INPUT_XLSX", "data/trading.xlsx")

    refresh_token: str | None = os.getenv("REFRESH_TOKEN")
    cache_file: str = os.getenv("CACHE_FILE", "/tmp/trading_api_cache.json")
    cache_ttl_seconds: int = _env_int("CACHE_TTL_SECONDS", 3600)
    auto_refresh_when_empty: bool = _env_bool("AUTO_REFRESH_WHEN_EMPTY", True)
    auto_refresh_when_stale: bool = _env_bool("AUTO_REFRESH_WHEN_STALE", True)
    gcs_cache_bucket: str | None = os.getenv("GCS_CACHE_BUCKET") or None
    gcs_cache_blob: str = os.getenv("GCS_CACHE_BLOB", "cache/trading_api_cache.json")

    request_sleep_seconds: float = _env_float("REQUEST_SLEEP_SECONDS", 0.25)
    export_output_dir: str = os.getenv("EXPORT_OUTPUT_DIR", "outputs")
    allowed_origins_raw: str = os.getenv("ALLOWED_ORIGINS", "*")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()] or ["*"]

    @property
    def cache_path(self) -> Path:
        return Path(self.cache_file)

    @property
    def output_dir(self) -> Path:
        return Path(self.export_output_dir)


FULL_MARKET_COLUMNS = [
    "Current Price",
    "Annual Return % (5Y)",
    "Yield %",
    "Market Cap",
    "Low 52W",
    "High 52W",
    "P/E Ratio",
    "EPS",
    "1Y Target",
]

BASIC_MARKET_COLUMNS = ["Current Price", "Low 52W", "High 52W"]
ID_STOCK_EXTRA_COLUMNS = ["Position Value", "Allocation %"]


@dataclass(frozen=True)
class SheetJob:
    name: str
    gid: str
    local_sheet_name: str
    output_xlsx: str
    market_columns: list[str]
    symbol_aliases: list[str]
    source_kind: str
    asset_group: str
    header_row: int = 1
    use_yahooquery_fallback: bool = False
    manual_extra_columns: list[str] = field(default_factory=list)

    @property
    def all_output_columns(self) -> list[str]:
        return list(dict.fromkeys(self.market_columns + self.manual_extra_columns))

    @property
    def public_columns(self) -> list[str]:
        if self.asset_group == "stock":
            return FULL_MARKET_COLUMNS
        return BASIC_MARKET_COLUMNS


EXACT_YAHOO_SYMBOL_MAP = {
    "ADS.XE": "ADS.DE",
    "ALV.XE": "ALV.DE",
    "ASML.EAS": "ASML.AS",
    "AUS200 (AXJO)": "^AXJO",
    "BBVA.BM": "BBVA.MC",
    "BEI.XE": "BEI.DE",
    "BMW.XE": "BMW.DE",
    "CABK.BM": "CABK.MC",
    "DAII.TSE (8750)": "8750.T",
    "DKI.TSE (6367)": "6367.T",
    "ENEL.MIL": "ENEL.MI",
    "ENI.MIL": "ENI.MI",
    "ESP35 (IBEX)": "^IBEX",
    "EUSTX50 (STOXX50E)": "^STOXX50E",
    "FRA40 (FCHI)": "^FCHI",
    "GER40 (GDAXI)": "^GDAXI",
    "HEIA.EAS": "HEIA.AS",
    "HIT.TSE (378A)": "378A.T",
    "ISP.MIL": "ISP.MI",
    "ITX.BM": "ITX.MC",
    "JAR.SGX (J36)": "J36.SI",
    "JPN225 (N225)": "^N225",
    "KEE.TSE (6861)": "6861.T",
    "MBG.XE": "MBG.DE",
    "MRK.XE": "MRK.DE",
    "MUR.TSE (6981)": "6981.T",
    "NAS100 (NDX)": "^NDX",
    "NESTE.OMXH": "NESTE.HE",
    "NID.TSE (6594)": "6594.T",
    "NOKIA.OMXH": "NOKIA.HE",
    "OL.TSE (4661)": "4661.T",
    "RACE.MIL": "RACE.MI",
    "SAN.BM": "SAN.MC",
    "SIE.XE": "SIE.DE",
    "SPX500 (SPX)": "^GSPC",
    "STLA.MIL": "STLAM.MI",
    "SVN.TSE (3382)": "3382.T",
    "TCEHY.OTC": "TCEHY",
    "TKY.TSE (8035)": "8035.T",
    "TM.TSE (7203)": "7203.T",
    "TMH.TSE (8766)": "8766.T",
    "UCG.MIL": "UCG.MI",
    "UK100 (FTSE)": "^FTSE",
    "US30 (DJI)": "^DJI",
    "VNA.XE": "VNA.DE",
    "VOW3.XE": "VOW3.DE",
}

EXCHANGE_SUFFIX_MAP = {
    "ASX": ".AX",
    "BM": ".MC",
    "EAS": ".AS",
    "EPA": ".PA",
    "FWB": ".DE",
    "HKEX": ".HK",
    "LSE": ".L",
    "MIL": ".MI",
    "NAS": "",
    "NYSE": "",
    "OMXH": ".HE",
    "OTC": "",
    "SGX": ".SI",
    "SIX": ".SW",
    "TSE": ".T",
    "TSX": ".TO",
    "TSXV": ".V",
    "XE": ".DE",
    "XETRA": ".DE",
}

SPECIAL_CRYPTO_CANDIDATES = {
    "APT": ["APT21794-USD", "APT-USD"],
    "SUI": ["SUI20947-USD", "SUI-USD"],
    "TON": ["TON11419-USD", "TON-USD"],
    "UNI": ["UNI7083-USD", "UNI1-USD", "UNI-USD"],
}

SPECIAL_FOREX_SYMBOLS = {
    "BRENT": "BZ=F",
    "GOLD": "GC=F",
    "NATGAS": "NG=F",
    "SILVER": "SI=F",
    "WTI": "CL=F",
    "XAGUSD": "SI=F",
    "XAUUSD": "GC=F",
    "XBRUSD": "BZ=F",
    "XNGUSD": "NG=F",
    "XTIUSD": "CL=F",
}

JOBS = {
    "mt5_stock": SheetJob(
        name="mt5_stock",
        gid="1243629676",
        local_sheet_name="mt5 stock",
        output_xlsx="trading_mt5_stock_filled.xlsx",
        market_columns=FULL_MARKET_COLUMNS,
        symbol_aliases=["Symbol", "Ticker", "Pair"],
        source_kind="mt5_stock",
        asset_group="stock",
    ),
    "id_stock": SheetJob(
        name="id_stock",
        gid="1892685403",
        local_sheet_name="ID STOCK",
        output_xlsx="trading_id_stock_filled.xlsx",
        market_columns=FULL_MARKET_COLUMNS,
        symbol_aliases=["Symbol"],
        source_kind="id_stock",
        asset_group="stock",
        use_yahooquery_fallback=True,
        manual_extra_columns=ID_STOCK_EXTRA_COLUMNS,
    ),
    "forex": SheetJob(
        name="forex",
        gid="1994520215",
        local_sheet_name="forex",
        output_xlsx="trading_forex_filled.xlsx",
        market_columns=BASIC_MARKET_COLUMNS,
        symbol_aliases=["Symbol", "Pair"],
        source_kind="forex",
        asset_group="forex",
    ),
    "crypto": SheetJob(
        name="crypto",
        gid="2048821090",
        local_sheet_name="crypto",
        output_xlsx="trading_crypto_filled.xlsx",
        market_columns=BASIC_MARKET_COLUMNS,
        symbol_aliases=["Symbol", "Pair", "Ticker"],
        source_kind="crypto",
        asset_group="crypto",
    ),
}
