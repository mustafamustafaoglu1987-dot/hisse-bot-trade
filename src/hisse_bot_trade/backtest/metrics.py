import pandas as pd


def compute_metrics(equity_curve: pd.Series, trades: list[dict], initial_balance: float) -> dict:
    final_equity = equity_curve.iloc[-1] if len(equity_curve) else initial_balance
    total_return_pct = (final_equity / initial_balance - 1) * 100

    if len(equity_curve):
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown_pct = drawdown.min() * 100
    else:
        max_drawdown_pct = 0.0

    closed_trades = [t for t in trades if t["side"] == "sell"]
    wins = [t for t in closed_trades if t["pnl"] > 0]
    win_rate_pct = (len(wins) / len(closed_trades) * 100) if closed_trades else 0.0

    return {
        "initial_balance": initial_balance,
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "num_trades": len(closed_trades),
        "win_rate_pct": win_rate_pct,
    }
