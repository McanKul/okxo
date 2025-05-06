from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from utils.bar_store import BarStore
from utils.interfaces import IStrategy

class BaseStrategy(IStrategy):
    """
    BarStore‑tabanlı ortak strateji sınıfı.
    Her strateji tek sembol + tek timeframe için örneklenir.
    """

    def __init__(
        self,
        bar_store: BarStore,
        symbol: str,
        timeframe: str,
        sl_pct: float = 3.0,
        **params,
    ):
        self.bar_store = bar_store
        self.symbol    = symbol
        self.tf        = timeframe
        self._sl_pct   = sl_pct
        self.params    = params          # ATR vb. teknik parametreler
        
    def update_bar(self, symbol: str, bar: dict) -> None:
        return
    # ------------- CANLI API -------------
    @abstractmethod
    def _live_signal(
        self,
        o: np.ndarray,
        h: np.ndarray,
        l: np.ndarray,
        c: np.ndarray,
        v: np.ndarray,
    ) -> Optional[str]:
        """"+1" | "-1" | None"""

    def generate_signal(self, _sym: str = None) -> Optional[str]:
        buf = self.bar_store.get_ohlcv(self.symbol, self.tf)
        if len(buf["close"]) < 2:
            return None

        o = np.asarray(buf["open"],   dtype=float)
        h = np.asarray(buf["high"],   dtype=float)
        l = np.asarray(buf["low"],    dtype=float)
        c = np.asarray(buf["close"],  dtype=float)
        v = np.asarray(buf["volume"], dtype=float)
        return self._live_signal(o, h, l, c, v)

    # ------------- BACKTEST API ----------
    @staticmethod
    @abstractmethod
    def generate_signals(df: pd.DataFrame) -> pd.Series:
        """Vectorized +1/0/‑1 sinyalleri döndürür."""

    # ------------- Yardımcı --------------
    def sl_pct(self) -> float:
        """PositionManager risk hesabı için."""
        return self._sl_pct
