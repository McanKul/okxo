import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """
    RsiMacdConfirmStrategy
    """

    def __init__(self, rsi_period: int = 14, **kw):
        super().__init__(rsi_period=rsi_period, **kw)
        self.p = rsi_period


    def _live_signal(self, o, h, l, c, v):
        if c.size < self.p + 2:
            return None
        rsi = talib.RSI(c, timeperiod=self.p)
        macd, macd_sig, _ = talib.MACD(c)
        buy = rsi[-2] < 20 <= rsi[-1] and macd[-2] < macd_sig[-2] < macd[-1] > macd_sig[-1]
        sell = rsi[-2] > 80 >= rsi[-1] and macd[-2] > macd_sig[-2] > macd[-1] < macd_sig[-1]
        if buy:
            return +1
        if sell:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, rsi_period=14) -> pd.Series:
        close = df["close"].values
        rsi = talib.RSI(close, timeperiod=rsi_period)
        macd, macd_sig, _ = talib.MACD(close)
        sig = np.zeros_like(close, dtype=int)
        sig[1:][(rsi[:-1] < 20) & (rsi[1:] >= 20) & (macd[:-1] < macd_sig[:-1]) & (macd[1:] > macd_sig[1:])] = 1
        sig[1:][(rsi[:-1] > 80) & (rsi[1:] <= 80) & (macd[:-1] > macd_sig[:-1]) & (macd[1:] < macd_sig[1:])] = -1
        return pd.Series(sig, index=df.index, name="signal")
