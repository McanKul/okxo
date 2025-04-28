import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """
    EmaCrossoverStrategy
    """

    def __init__(self, fast: int = 5, slow: int = 12, rsi_period: int = 14,
                 oversold: int = 30, overbought: int = 70, **kw):
        super().__init__(fast=fast, slow=slow, rsi_period=rsi_period,
                         oversold=oversold, overbought=overbought, **kw)
        self.f, self.s = fast, slow
        self.rsi_p, self.os, self.ob = rsi_period, oversold, overbought

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.s + 2:
            return None
        fema = talib.EMA(c, timeperiod=self.f)
        sema = talib.EMA(c, timeperiod=self.s)
        rsi = talib.RSI(c, timeperiod=self.rsi_p)
        if fema[-2] <= sema[-2] < fema[-1] and rsi[-1] < self.ob:
            return +1
        if fema[-2] >= sema[-2] > fema[-1] and rsi[-1] > self.os:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, fast=5, slow=12, rsi_period=14,
                         oversold=30, overbought=70) -> pd.Series:
        close = df["close"].values
        fema = talib.EMA(close, timeperiod=fast)
        sema = talib.EMA(close, timeperiod=slow)
        rsi = talib.RSI(close, timeperiod=rsi_period)
        sig = np.zeros_like(close, dtype=int)
        sig[1:][(fema[:-1] <= sema[:-1]) & (fema[1:] > sema[1:]) & (rsi[1:] < overbought)] = 1
        sig[1:][(fema[:-1] >= sema[:-1]) & (fema[1:] < sema[1:]) & (rsi[1:] > oversold)] = -1
        return pd.Series(sig, index=df.index, name="signal")
