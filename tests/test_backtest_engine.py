import pandas as pd

from hisse_bot_trade.backtest.engine import run_backtest


def test_backtest_engine_matches_hand_calculated_equity():
    df = pd.DataFrame({
        "open_time": pd.date_range("2024-01-01", periods=4, freq="D"),
        "close": [100, 100, 110, 120],
        "signal": [0, 1, 0, -1],
    })

    result = run_backtest(
        df,
        initial_balance=1000.0,
        fee_pct=0.0,
        stop_loss_pct=0.5,
        position_size_pct=0.5,
    )

    assert result.equity_curve.tolist() == [1000.0, 1000.0, 1050.0, 1100.0]
    assert result.metrics["num_trades"] == 1
    assert result.metrics["win_rate_pct"] == 100.0
    assert round(result.metrics["total_return_pct"], 4) == 10.0


def test_backtest_engine_stop_loss_closes_position():
    df = pd.DataFrame({
        "open_time": pd.date_range("2024-01-01", periods=3, freq="D"),
        "close": [100, 100, 90],
        "signal": [0, 1, 0],
    })

    result = run_backtest(
        df,
        initial_balance=1000.0,
        fee_pct=0.0,
        stop_loss_pct=0.05,
        position_size_pct=0.5,
    )

    sell_trades = [t for t in result.trades if t["side"] == "sell"]
    assert len(sell_trades) == 1
    assert sell_trades[0]["reason"] == "stop_loss"
    assert result.metrics["win_rate_pct"] == 0.0
