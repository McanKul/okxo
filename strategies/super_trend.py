import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """
    SupertrendStrategy
    """

    def __init__(self, atr_period: int = 10, multiplier: int = 2, **kw):
        super().__init__(atr_period=atr_period, multiplier=multiplier, **kw)
        self.atr_p, self.mult = atr_period, multiplier

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.atr_p + 2:
            return None
        atr = talib.ATR(h, l, c, timeperiod=self.atr_p)
        upper = (h + l) / 2 + self.mult * atr
        lower = (h + l) / 2 - self.mult * atr
        st = upper.copy()
        for i in range(1, len(c)):
            st[i] = min(upper[i], st[i - 1]) if c[i - 1] <= st[i - 1] else max(lower[i], st[i - 1])
        trend_now, trend_prev = c[-1] > st[-1], c[-2] > st[-2]
        if not trend_prev and trend_now:
            return +1
        if trend_prev and not trend_now:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, atr_period=10, multiplier=2) -> pd.Series:
        h, l, c = df["high"].values, df["low"].values, df["close"].values
        atr = talib.ATR(h, l, c, timeperiod=atr_period)
        upper = (h + l) / 2 + multiplier * atr
        lower = (h + l) / 2 - multiplier * atr
        st = np.copy(upper)
        for i in range(1, len(c)):
            st[i] = min(upper[i], st[i - 1]) if c[i - 1] <= st[i - 1] else max(lower[i], st[i - 1])
        trend = c > st
        sig = np.zeros_like(c, dtype=int)
        sig[1:][(~trend[:-1]) & trend[1:]] = 1
        sig[1:][trend[:-1] & (~trend[1:])] = -1
        return pd.Series(sig, index=df.index, name="signal")
