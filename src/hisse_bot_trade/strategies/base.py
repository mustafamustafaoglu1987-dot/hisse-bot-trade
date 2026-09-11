from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Common interface every strategy implements.

    generate_signals() takes an OHLCV DataFrame (must contain a 'close'
    column) and returns the same DataFrame with an added 'signal' column:
        1  -> enter long (only acted on if currently flat)
       -1  -> exit long (only acted on if currently holding a position)
        0  -> no action

    Symbol-agnostic: the same interface works for a single BIST ticker's
    OHLCV DataFrame, mirroring kripto-bot-trade's strategy contract.
    """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ...
