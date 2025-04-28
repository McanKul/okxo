# strategies/rsi_strategy.py
import pandas as pd
from strategies.base_strategy import BaseStrategy
import talib
import numpy as np

class Strategy(BaseStrategy):
    """
    RSI THRESHOLD STRATEGY
    """

    def __init__(self, rsi_period: int = 14, rsi_overbought: int = 80, rsi_oversold: int = 20, **kw):
        super().__init__(rsi_period=rsi_period, overbought=rsi_overbought, oversold=rsi_oversold, **kw)
        self.rsi_period = rsi_period
        self.ob = rsi_overbought
        self.os = rsi_oversold

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.rsi_period:
            return None
        rsi = talib.RSI(c, timeperiod=self.rsi_period)[-1]
        if np.isnan(rsi):
            return None
        if rsi > self.ob:
            return -1
        if rsi < self.os:
            return +1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, rsi_period: int = 14, overbought: int = 80, oversold: int = 20) -> pd.Series:
        rsi = talib.RSI(df["close"].values, timeperiod=rsi_period)
        sig = np.where(rsi > overbought, -1, np.where(rsi < oversold, 1, 0))
        return pd.Series(sig, index=df.index, name="signal")

