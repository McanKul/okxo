import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    """SupertrendStrategy with ConfigLoader integration."""

    def __init__(self, atr_period: int = 10, multiplier: float = 2.0, **kw):
        super().__init__(atr_period=atr_period, multiplier=multiplier, **kw)
        self.atr_period = atr_period
        self.multiplier = multiplier

    def _live_signal(self, o, h, l, c, v):
        if len(c) < self.atr_period + 2:
            return None

        # Supertrend calculation
        atr = talib.ATR(h, l, c, timeperiod=self.atr_period)
        upperband = (h + l) / 2 + (self.multiplier * atr)
        lowerband = (h + l) / 2 - (self.multiplier * atr)

        supertrend = np.zeros_like(c)
        supertrend[0] = upperband[0]

        for i in range(1, len(c)):
            if c[i - 1] <= supertrend[i - 1]:
                supertrend[i] = min(upperband[i], supertrend[i - 1])
            else:
                supertrend[i] = max(lowerband[i], supertrend[i - 1])

        # Signal generation logic
        if c[-2] <= supertrend[-2] and c[-1] > supertrend[-1]:
            return +1  # Bullish crossover
        elif c[-2] >= supertrend[-2] and c[-1] < supertrend[-1]:
            return -1  # Bearish crossover
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, atr_period=10, multiplier=2.0) -> pd.Series:
        """Vectorized Supertrend Signal Generation."""
        h, l, c = df["high"].values, df["low"].values, df["close"].values

        atr = talib.ATR(h, l, c, timeperiod=atr_period)
        upperband = (h + l) / 2 + multiplier * atr
        lowerband = (h + l) / 2 - multiplier * atr

        supertrend = np.zeros_like(c)
        supertrend[0] = upperband[0]

        for i in range(1, len(c)):
            if c[i - 1] <= supertrend[i - 1]:
                supertrend[i] = min(upperband[i], supertrend[i - 1])
            else:
                supertrend[i] = max(lowerband[i], supertrend[i - 1])

        trend = c > supertrend
        signals = np.zeros(len(c), dtype=int)
        signals[1:][(~trend[:-1]) & trend[1:]] = 1  # Bullish crossover
        signals[1:][trend[:-1] & (~trend[1:])] = -1  # Bearish crossover

        return pd.Series(signals, index=df.index, name="signal")
