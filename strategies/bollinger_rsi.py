import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """
    BollingerRsiStrategy
    """

    def __init__(self, period: int = 20, dev: float = 2.0,
                 rsi_period: int = 14, oversold: int = 30, overbought: int = 70, **kw):
        super().__init__(period=period, dev=dev, rsi_period=rsi_period,
                         oversold=oversold, overbought=overbought, **kw)
        self.p, self.d = period, dev
        self.rsi_p, self.os, self.ob = rsi_period, oversold, overbought

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.p + 2:
            return None
        upper, _, lower = talib.BBANDS(c, timeperiod=self.p, nbdevup=self.d, nbdevdn=self.d)
        rsi = talib.RSI(c, timeperiod=self.rsi_p)
        if c[-2] < lower[-2] <= c[-1] and rsi[-1] < self.os:
            return +1
        if c[-2] > upper[-2] >= c[-1] and rsi[-1] > self.ob:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, period=20, dev=2.0,
                         rsi_period=14, oversold=30, overbought=70) -> pd.Series:
        close = df["close"].values
        upper, _, lower = talib.BBANDS(close, timeperiod=period, nbdevup=dev, nbdevdn=dev)
        rsi = talib.RSI(close, timeperiod=rsi_period)
        sig = np.zeros_like(close, dtype=int)
        sig[1:][(close[:-1] < lower[:-1]) & (close[1:] > lower[1:]) & (rsi[1:] < oversold)] = 1
        sig[1:][(close[:-1] > upper[:-1]) & (close[1:] < upper[1:]) & (rsi[1:] > overbought)] = -1
        return pd.Series(sig, index=df.index, name="signal")
