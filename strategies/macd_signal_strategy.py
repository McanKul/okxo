# strategies/macd_signal_strategy.py
import pandas as pd
import numpy as np
import talib
from strategies.base_strategy import BaseStrategy

# ---------------------------------------------------------------------------
class Strategy(BaseStrategy):
    """
    MacdSignalStrategy
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, **kw):
        super().__init__(fast=fast, slow=slow, signal=signal, **kw)
        self.fast = fast
        self.slow = slow
        self.sig = signal

    def _live_signal(self, o, h, l, c, v):
        if c.size < self.slow + 1:
            return None
        macd, macd_sig, _ = talib.MACD(c, self.fast, self.slow, self.sig)
        prev_m, curr_m = macd[-2], macd[-1]
        prev_s, curr_s = macd_sig[-2], macd_sig[-1]
        if np.isnan([prev_m, curr_m, prev_s, curr_s]).any():
            return None
        if prev_m < prev_s and curr_m > curr_s:
            return +1
        if prev_m > prev_s and curr_m < curr_s:
            return -1
        return None

    @staticmethod
    def generate_signals(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.Series:
        macd, macd_sig, _ = talib.MACD(df["close"].values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        crossover_up = (macd[:-1] < macd_sig[:-1]) & (macd[1:] > macd_sig[1:])
        crossover_dn = (macd[:-1] > macd_sig[:-1]) & (macd[1:] < macd_sig[1:])
        sig = np.zeros_like(macd, dtype=int)
        sig[1:][crossover_up] = 1
        sig[1:][crossover_dn] = -1
        return pd.Series(sig, index=df.index, name="signal")
