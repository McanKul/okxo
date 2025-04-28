import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy): 

    """
    VolumeSpikeReversalStrategy
    """
    def __init__(self, period: int = 20, threshold: float = 2.0, **kw):
        super().__init__(period=period, threshold=threshold, **kw)
        self.period, self.th = period, threshold

    def _live_signal(self, o, h, l, c, v):
        if v.size < self.period + 1:
            return None
        avg_vol = v[-(self.period + 1):-1].mean()
        if avg_vol == 0 or v[-1] <= self.th * avg_vol:
            return None
        if c[-1] > c[-2]:
            return -1  # tepe
        if c[-1] < c[-2]:
            return +1    # dip
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, period=20, threshold=2.0) -> pd.Series:
        vol = df["volume"].values
        close = df["close"].values
        ma = pd.Series(vol).rolling(period).mean().to_numpy()
        spikes = vol > threshold * ma
        sig = np.zeros_like(close, dtype=int)
        sig[1:][spikes[1:] & (close[1:] > close[:-1])] = -1
        sig[1:][spikes[1:] & (close[1:] < close[:-1])] = 1
        return pd.Series(sig, index=df.index, name="signal")
