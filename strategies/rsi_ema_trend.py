import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """
    RsiEmaTrendStrategy
    """

    def __init__(self, rsi_period: int = 14, ema_fast: int = 50, ema_slow: int = 200, **kw):
        super().__init__(rsi_period=rsi_period, ema_fast=ema_fast, ema_slow=ema_slow, **kw)
        self.rsi_p, self.f, self.s = rsi_period, ema_fast, ema_slow

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.s + 2:
            return None
        fast = talib.EMA(c, timeperiod=self.f)
        slow = talib.EMA(c, timeperiod=self.s)
        rsi = talib.RSI(c, timeperiod=self.rsi_p)
        if fast[-1] > slow[-1] and rsi[-2] < 50 <= rsi[-1]:
            return +1
        if fast[-1] < slow[-1] and rsi[-2] > 50 >= rsi[-1]:
            return  -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, rsi_period=14, ema_fast=50, ema_slow=200) -> pd.Series:
        close = df["close"].values
        fast = talib.EMA(close, timeperiod=ema_fast)
        slow = talib.EMA(close, timeperiod=ema_slow)
        rsi = talib.RSI(close, timeperiod=rsi_period)
        sig = np.zeros_like(close, dtype=int)
        sig[1:][(fast[1:] > slow[1:]) & (rsi[:-1] < 50) & (rsi[1:] >= 50)] = 1
        sig[1:][(fast[1:] < slow[1:]) & (rsi[:-1] > 50) & (rsi[1:] <= 50)] = -1
        return pd.Series(sig, index=df.index, name="signal")
