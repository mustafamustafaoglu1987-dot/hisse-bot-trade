import pandas as pd

from .base import Strategy


class SmaCrossoverStrategy(Strategy):
    """Golden cross (fast SMA crosses above slow SMA) -> buy.
    Death cross (fast SMA crosses below slow SMA) -> sell.
    """

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["sma_fast"] = df["close"].rolling(self.fast_period).mean()
        df["sma_slow"] = df["close"].rolling(self.slow_period).mean()

        above = df["sma_fast"] > df["sma_slow"]
        prev_above = above.shift(1, fill_value=False)
        crossed_up = above & ~prev_above
        crossed_down = ~above & prev_above

        df["signal"] = 0
        df.loc[crossed_up, "signal"] = 1
        df.loc[crossed_down, "signal"] = -1
        return df
