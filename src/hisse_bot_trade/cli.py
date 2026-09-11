import argparse
import sys
from pathlib import Path

import pandas as pd

# Windows consoles often default to a non-UTF-8 codepage (e.g. cp1252), which
# can't print paths containing Turkish characters (this project lives under
# a "öğrenme" folder). Force UTF-8 stdout so print() never crashes on that.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .backtest.engine import run_backtest
from .config import Config
from .data.bist_client import fetch_bulk, fetch_ohlcv
from .strategies.rsi_reversion import RsiReversionStrategy, compute_rsi
from .strategies.sma_crossover import SmaCrossoverStrategy
from .universe import load_tickers

# .../hisse-bot-trade/src/hisse_bot_trade/cli.py -> parents[2] is the project root.
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ohlcv"

STRATEGIES = {
    "sma_crossover": lambda cfg: SmaCrossoverStrategy(cfg.fast_sma, cfg.slow_sma),
    "rsi_reversion": lambda cfg: RsiReversionStrategy(cfg.rsi_period, cfg.rsi_oversold, cfg.rsi_overbought),
}


def _cache_path(ticker: str) -> Path:
    return DATA_DIR / f"{ticker}.csv"


def _load_or_fetch_ohlcv(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(ticker)

    if cache_path.exists():
        cached = pd.read_csv(cache_path, parse_dates=["open_time"])
        cached["open_time"] = pd.to_datetime(cached["open_time"], utc=True)
        if len(cached) and cached["open_time"].min() <= start and cached["open_time"].max() >= end:
            window = cached[(cached["open_time"] >= start) & (cached["open_time"] <= end)]
            return window.reset_index(drop=True)

    df = fetch_ohlcv(ticker, start, end)
    if not df.empty:
        df.to_csv(cache_path, index=False)
    return df


def _cache_is_fresh(path: Path) -> bool:
    """A cache file counts as fresh if its last bar is from yesterday or
    later (today's BIST daily bar usually isn't final until market close
    anyway, so 'yesterday or later' avoids needless same-day refetching).
    """
    if not path.exists():
        return False
    try:
        df = pd.read_csv(path, parse_dates=["open_time"])
    except Exception:
        return False
    if df.empty:
        return False
    last_date = pd.to_datetime(df["open_time"].max(), utc=True).date()
    cutoff = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=1)).date()
    return last_date >= cutoff


def _scan_fetch(tickers: list[str], period: str, interval: str) -> dict[str, pd.DataFrame]:
    """Bulk-fetch the scan universe, reusing same-day cache per ticker so a
    repeated scan doesn't re-hit yfinance (which rate-limits bulk calls).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}
    to_fetch = []
    for ticker in tickers:
        path = _cache_path(ticker)
        if _cache_is_fresh(path):
            df = pd.read_csv(path, parse_dates=["open_time"])
            df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
            results[ticker] = df
        else:
            to_fetch.append(ticker)

    if to_fetch:
        fresh = fetch_bulk(to_fetch, period=period, interval=interval)
        for ticker, df in fresh.items():
            df.to_csv(_cache_path(ticker), index=False)
            results[ticker] = df

    return results


def cmd_backtest(args: argparse.Namespace) -> None:
    cfg = Config()
    ticker = args.ticker.upper()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")

    df = _load_or_fetch_ohlcv(ticker, start, end)
    if df.empty:
        print(f"Veri alınamadı: {ticker} — sembol/tarih aralığını kontrol edin.")
        return

    strategy = STRATEGIES[args.strategy](cfg)
    signaled = strategy.generate_signals(df)
    result = run_backtest(
        signaled,
        initial_balance=cfg.initial_balance,
        fee_pct=cfg.fee_pct,
        stop_loss_pct=cfg.stop_loss_pct,
        position_size_pct=cfg.position_size_pct,
    )

    buy_hold_return_pct = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
    m = result.metrics

    print(f"\n=== Backtest: {args.strategy} on {ticker} ({args.start} -> {args.end}) ===")
    print(f"Initial balance:     {m['initial_balance']:.2f}")
    print(f"Final equity:        {m['final_equity']:.2f}")
    print(f"Total return:        {m['total_return_pct']:.2f}%")
    print(f"Buy & hold return:   {buy_hold_return_pct:.2f}%")
    print(f"Max drawdown:        {m['max_drawdown_pct']:.2f}%")
    print(f"Number of trades:    {m['num_trades']}")
    print(f"Win rate:            {m['win_rate_pct']:.2f}%")

    if args.plot:
        _plot_equity(signaled, result, ticker, args)


def _plot_equity(signaled: pd.DataFrame, result, ticker: str, args: argparse.Namespace) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(signaled["open_time"], result.equity_curve, label="Strategy equity")
    ax.set_title(f"{args.strategy} on {ticker}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Equity")
    ax.legend()
    out_path = Path("equity_curve.png")
    fig.savefig(out_path)
    print(f"Saved equity curve to {out_path.resolve()}")


def cmd_scan(args: argparse.Namespace) -> None:
    cfg = Config()
    tickers = load_tickers()
    print(f"{len(tickers)} hisse taranıyor (evren dosyası: data/bist100_tickers.txt)...")

    bulk = _scan_fetch(tickers, period=args.period, interval=cfg.interval)
    missing = [t for t in tickers if t not in bulk]
    status = f"Başarıyla çekildi: {len(bulk)}/{len(tickers)}"
    if missing:
        status += f" (başarısız: {', '.join(missing)})"
    print(status)

    strategy = STRATEGIES[args.strategy](cfg)
    min_bars = max(cfg.slow_sma, cfg.rsi_period) + 1

    rows = []
    for ticker, df in bulk.items():
        if len(df) < min_bars:
            continue  # yetersiz geçmiş veri — gösterge hesaplanamaz
        signaled = strategy.generate_signals(df)
        last = signaled.iloc[-1]
        rsi_value = last["rsi"] if "rsi" in signaled.columns else compute_rsi(df["close"], cfg.rsi_period).iloc[-1]
        rows.append({
            "ticker": ticker,
            "close": last["close"],
            "rsi": rsi_value,
            "signal": last["signal"],
        })

    if not rows:
        print("Hiçbir hisse için yeterli veri/gösterge hesaplanamadı.")
        return

    table = pd.DataFrame(rows)
    if args.sort == "oversold":
        table = table.sort_values("rsi", ascending=True)
    elif args.sort == "overbought":
        table = table.sort_values("rsi", ascending=False)
    else:
        table = table.sort_values("ticker")
    table = table.head(args.limit)

    print(f"\n=== BIST Tarama: {args.strategy}, sıralama={args.sort} (ilk {args.limit}) ===")
    print(f"{'Ticker':<10}{'Kapanış':>12}{'RSI':>10}{'Sinyal':>10}")
    side_labels = {1: "AL", -1: "SAT", 0: "-"}
    for _, row in table.iterrows():
        side = side_labels[int(row["signal"])]
        print(f"{row['ticker']:<10}{row['close']:>12.2f}{row['rsi']:>10.2f}{side:>10}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hisse_bot_trade")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Run a historical backtest on a single BIST ticker")
    bt.add_argument("--ticker", required=True, help="BIST kodu, örn. THYAO (.IS otomatik eklenir)")
    bt.add_argument("--strategy", choices=list(STRATEGIES), default="sma_crossover")
    bt.add_argument("--start", required=True, help="YYYY-MM-DD")
    bt.add_argument("--end", required=True, help="YYYY-MM-DD")
    bt.add_argument("--plot", action="store_true")
    bt.set_defaults(func=cmd_backtest)

    sc = sub.add_parser("scan", help="Scan the BIST universe (data/bist100_tickers.txt) for current RSI/SMA state")
    sc.add_argument("--strategy", choices=list(STRATEGIES), default="rsi_reversion")
    sc.add_argument("--period", default="1y", help="yfinance period for the scan window, e.g. 6mo, 1y, 2y")
    sc.add_argument("--sort", choices=["oversold", "overbought", "ticker"], default="oversold")
    sc.add_argument("--limit", type=int, default=20)
    sc.set_defaults(func=cmd_scan)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
