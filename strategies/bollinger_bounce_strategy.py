# strategies/bollinger_bounce_strategy.py
import pandas as pd
from strategies.base_strategy import BaseStrategy
import talib
import numpy as np

# ---------------------------------------------------------------------------
class Strategy(BaseStrategy):
    """Bollinger Bands bounce +2σ."""

    def __init__(self, period: int = 20, dev: float = 2.0, **kw):
        super().__init__(period=period, dev=dev, **kw)
        self.period = period
        self.dev = dev

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.period + 2:
            return None
        upper, mid, lower = talib.BBANDS(c, timeperiod=self.period, nbdevup=self.dev, nbdevdn=self.dev)
        prev_c, curr_c = c[-2], c[-1]
        prev_u, curr_u = upper[-2], upper[-1]
        prev_l, curr_l = lower[-2], lower[-1]
        # bounce
        if prev_c < prev_l and curr_c > curr_l:
            return +1
        if prev_c > prev_u and curr_c < curr_u:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, period=20, dev=2.0) -> pd.Series:
        close = df["close"].values
        upper, mid, lower = talib.BBANDS(close, timeperiod=period, nbdevup=dev, nbdevdn=dev)
        sig = np.zeros_like(close, dtype=int)
        bounce_up = (close[:-1] < lower[:-1]) & (close[1:] > lower[1:])
        bounce_dn = (close[:-1] > upper[:-1]) & (close[1:] < upper[1:])
        sig[1:][bounce_up] = 1
        sig[1:][bounce_dn] = -1
        return pd.Series(sig, index=df.index, name="signal")
