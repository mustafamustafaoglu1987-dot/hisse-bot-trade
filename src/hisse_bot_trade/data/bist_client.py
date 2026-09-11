"""Wrapper over yfinance for BIST equities.

Unlike Binance, Borsa Istanbul has no free, unauthenticated public REST API
of its own -- official data requires a paid license. yfinance (which reads
Yahoo Finance's data, no API key needed) is the most practical free option
for a learner. BIST tickers are addressed on Yahoo Finance with a ".IS"
suffix (e.g. THYAO -> THYAO.IS).

yfinance is known to rate-limit heavy bulk downloads, so fetch_bulk() uses
a single batched yf.download() call for the whole ticker list rather than
one request per ticker, and tolerates individual ticker failures instead of
aborting the whole scan.
"""

import os
import tempfile
from pathlib import Path

import certifi
import pandas as pd


def _ensure_ascii_safe_cacert_env() -> None:
    """yfinance's HTTP layer (curl_cffi) encodes the CA-bundle file path
    using the Windows ANSI codepage before handing it to libcurl. This
    project lives under a path containing Turkish characters ("öğrenme"),
    which cp1252 can't encode, crashing every HTTPS request with a
    UnicodeEncodeError. Work around it by copying the CA bundle to an
    ASCII-only temp path and pointing curl_cffi at it via SSL_CERT_FILE,
    which it already checks before falling back to certifi's own path.
    Must run before `import yfinance` (curl_cffi resolves the cacert path
    once at import time).
    """
    if os.name != "nt" or os.environ.get("SSL_CERT_FILE"):
        return
    try:
        source = Path(certifi.where())
        dest = Path(tempfile.gettempdir()) / "hisse_bot_trade_cacert.pem"
        if not dest.exists() or dest.stat().st_size != source.stat().st_size:
            dest.write_bytes(source.read_bytes())
        os.environ["SSL_CERT_FILE"] = str(dest)
    except OSError:
        pass  # best-effort; original error surfaces if this fails


_ensure_ascii_safe_cacert_env()

import yfinance as yf  # noqa: E402 (must follow the cacert workaround above)

OHLCV_COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]


def _to_yahoo_symbol(ticker: str) -> str:
    ticker = ticker.strip().upper()
    return ticker if ticker.endswith(".IS") else f"{ticker}.IS"


def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=OHLCV_COLUMNS)
    df = raw.reset_index()
    time_col = "Date" if "Date" in df.columns else "Datetime"
    df = df.rename(columns={
        time_col: "open_time", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df[OHLCV_COLUMNS].dropna(subset=["close"]).reset_index(drop=True)


def fetch_ohlcv(ticker: str, start: pd.Timestamp, end: pd.Timestamp, interval: str = "1d") -> pd.DataFrame:
    """Fetch a single BIST ticker's OHLCV history."""
    symbol = _to_yahoo_symbol(ticker)
    raw = yf.Ticker(symbol).history(start=start, end=end, interval=interval, auto_adjust=False)
    return _normalize(raw)


def fetch_bulk(tickers: list[str], period: str = "1y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for many tickers in one yfinance call.

    Returns {ticker: DataFrame}. A ticker that failed or returned no data
    is simply omitted — compare the result keys against the input list to
    see which ones dropped out (the caller should report this, not crash).
    """
    symbols = [_to_yahoo_symbol(t) for t in tickers]
    raw = yf.download(
        symbols, period=period, interval=interval,
        group_by="ticker", threads=True, progress=False, auto_adjust=False,
    )

    results: dict[str, pd.DataFrame] = {}
    for ticker, symbol in zip(tickers, symbols):
        try:
            sub = raw[symbol] if len(symbols) > 1 else raw
        except KeyError:
            continue
        sub = _normalize(sub.dropna(how="all"))
        if not sub.empty:
            results[ticker] = sub

    return results
