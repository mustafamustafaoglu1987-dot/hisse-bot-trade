from dataclasses import dataclass


@dataclass
class Config:
    """Strategy and risk parameters, kept as plain fields (not hardcoded in
    strategy code) so they can be tweaked and the effect observed in
    backtests. Mirrors kripto-bot-trade's Config for consistency.
    """

    interval: str = "1d"  # BIST: daily is the reliable timeframe via yfinance

    # Fees / risk management
    fee_pct: float = 0.0015         # typical BIST aracı kurumu komisyonu, ~%0.15
    stop_loss_pct: float = 0.05     # BIST stocks move less violently intraday than crypto; wider stop
    position_size_pct: float = 0.10  # fraction of balance risked per trade
    initial_balance: float = 10000.0  # TL

    # SMA crossover strategy
    fast_sma: int = 20
    slow_sma: int = 50

    # RSI mean-reversion strategy
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
