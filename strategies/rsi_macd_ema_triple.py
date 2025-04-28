import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    
    """
    RsiMacdEmaTripleStrategy
    """

    def __init__(self, rsi_period: int = 14, **kw):
        super().__init__(rsi_period=rsi_period, **kw)
        self.p = rsi_period

    def _live_signal(self, o, h, l, c, v):
        if c.size < 202:                          # EMA200 + buffer
            return None
        rsi = talib.RSI(c, timeperiod=self.p)
        macd, macd_sig, _ = talib.MACD(c)
        ema50 = talib.EMA(c, timeperiod=50)
        ema200 = talib.EMA(c, timeperiod=200)
        if rsi[-2] < 30 <= rsi[-1] and macd[-2] < macd_sig[-2] < macd[-1] > macd_sig[-1] and ema50[-1] > ema200[-1]:
            return +1
        if rsi[-2] > 70 >= rsi[-1] and macd[-2] > macd_sig[-2] > macd[-1] < macd_sig[-1] and ema50[-1] < ema200[-1]:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, rsi_period=14) -> pd.Series:
        close = df["close"].values
        rsi = talib.RSI(close, timeperiod=rsi_period)
        macd, macd_sig, _ = talib.MACD(close)
        ema50 = talib.EMA(close, timeperiod=50)
        ema200 = talib.EMA(close, timeperiod=200)
        buy = ((rsi[:-1] < 30) & (rsi[1:] >= 30) &
               (macd[:-1] < macd_sig[:-1]) & (macd[1:] > macd_sig[1:]) &
               (ema50[1:] > ema200[1:]))
        sell = ((rsi[:-1] > 70) & (rsi[1:] <= 70) &
                (macd[:-1] > macd_sig[:-1]) & (macd[1:] < macd_sig[1:]) &
                (ema50[1:] < ema200[1:]))
        sig = np.zeros_like(close, dtype=int)
        sig[1:][buy] = 1
        sig[1:][sell] = -1
        return pd.Series(sig, index=df.index, name="signal")
