import pandas as pd

from hisse_bot_trade.strategies.sma_crossover import SmaCrossoverStrategy


def test_sma_crossover_detects_golden_and_death_cross():
    # Flat, then a dip, then a sharp rise, then flattening again.
    # fast(2)/slow(4) SMA: golden cross at index 8, death cross at index 11.
    close = [10, 10, 10, 10, 5, 5, 5, 5, 12, 12, 12, 12]
    df = pd.DataFrame({
        "open_time": pd.date_range("2024-01-01", periods=len(close), freq="D"),
        "close": close,
    })

    strategy = SmaCrossoverStrategy(fast_period=2, slow_period=4)
    result = strategy.generate_signals(df)

    buy_rows = result.index[result["signal"] == 1].tolist()
    sell_rows = result.index[result["signal"] == -1].tolist()

    assert buy_rows == [8]
    assert sell_rows == [11]
