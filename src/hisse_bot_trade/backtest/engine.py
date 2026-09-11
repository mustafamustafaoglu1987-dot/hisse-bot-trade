from dataclasses import dataclass

import pandas as pd

from .metrics import compute_metrics


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[dict]
    metrics: dict


def run_backtest(
    df: pd.DataFrame,
    initial_balance: float,
    fee_pct: float,
    stop_loss_pct: float,
    position_size_pct: float,
) -> BacktestResult:
    """Bar-by-bar simulation of a single-symbol, long-only strategy.

    df must already contain a 'signal' column (1 = enter long, -1 = exit
    long, 0 = hold), as produced by a Strategy.generate_signals() call.
    Symbol-agnostic and identical to kripto-bot-trade's engine — the same
    mechanics apply whether the bars are BTCUSDT candles or a BIST stock's
    daily closes.
    """
    balance = initial_balance
    position_qty = 0.0
    entry_price = 0.0
    equity_values = []
    trades: list[dict] = []

    for _, row in df.iterrows():
        price = row["close"]
        signal = row["signal"]

        if position_qty > 0 and price <= entry_price * (1 - stop_loss_pct):
            proceeds = position_qty * price * (1 - fee_pct)
            pnl = proceeds - (position_qty * entry_price)
            balance += proceeds
            trades.append({
                "time": row["open_time"], "side": "sell", "price": price,
                "qty": position_qty, "pnl": pnl, "reason": "stop_loss",
            })
            position_qty = 0.0
            entry_price = 0.0

        elif signal == 1 and position_qty == 0:
            trade_value = balance * position_size_pct
            position_qty = (trade_value * (1 - fee_pct)) / price
            entry_price = price
            balance -= trade_value
            trades.append({
                "time": row["open_time"], "side": "buy", "price": price,
                "qty": position_qty, "pnl": 0.0, "reason": "signal",
            })

        elif signal == -1 and position_qty > 0:
            proceeds = position_qty * price * (1 - fee_pct)
            pnl = proceeds - (position_qty * entry_price)
            balance += proceeds
            trades.append({
                "time": row["open_time"], "side": "sell", "price": price,
                "qty": position_qty, "pnl": pnl, "reason": "signal",
            })
            position_qty = 0.0
            entry_price = 0.0

        equity_values.append(balance + position_qty * price)

    equity_curve = pd.Series(equity_values, index=df.index)
    metrics = compute_metrics(equity_curve, trades, initial_balance)
    return BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics)
