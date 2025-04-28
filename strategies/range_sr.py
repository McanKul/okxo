import pandas as pd
import numpy as np
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """
    RangeSupportResistanceStrategy
    """

    def __init__(self, lookback: int = 20, **kw):
        super().__init__(lookback=lookback, **kw)
        self.lb = lookback

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.lb + 2:
            return None
        support = l[-(self.lb + 1):-1].min()
        resistance = h[-(self.lb + 1):-1].max()
        if c[-2] < support <= c[-1]:
            return +1
        if c[-2] > resistance >= c[-1]:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, lookback=20) -> pd.Series:
        close, high, low = df["close"].values, df["high"].values, df["low"].values
        sig = np.zeros_like(close, dtype=int)
        for i in range(lookback + 1, len(close)):
            sup = low[i - lookback - 1:i - 1].min()
            res = high[i - lookback - 1:i - 1].max()
            if close[i - 1] < sup <= close[i]:
                sig[i] = 1
            elif close[i - 1] > res >= close[i]:
                sig[i] = -1
        return pd.Series(sig, index=df.index, name="signal")
