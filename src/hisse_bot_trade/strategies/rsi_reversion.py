import pandas as pd

from .base import Strategy


def compute_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


class RsiReversionStrategy(Strategy):
    """RSI drops below `oversold` -> buy (expecting a bounce).
    RSI rises above `overbought` -> sell (expecting a pullback).
    """

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["rsi"] = compute_rsi(df["close"], self.period)

        was_above_oversold = df["rsi"].shift(1) >= self.oversold
        crossed_into_oversold = was_above_oversold & (df["rsi"] < self.oversold)

        was_below_overbought = df["rsi"].shift(1) <= self.overbought
        crossed_into_overbought = was_below_overbought & (df["rsi"] > self.overbought)

        df["signal"] = 0
        df.loc[crossed_into_oversold, "signal"] = 1
        df.loc[crossed_into_overbought, "signal"] = -1
        return df
