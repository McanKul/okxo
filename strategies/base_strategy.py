"""strategies/enhanced_strategies.py

Tamamen vektörleştirilmiş, TA‑Lib tabanlı **yüksek performanslı** strateji koleksiyonu.

alt sınıfını örnekler.
"""
from __future__ import annotations

from abc import abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional
from utils.interfaces import IStrategy
import numpy as np
import pandas as pd
import talib


# ---------------------------------------------------------------------------
class BaseStrategy(IStrategy):
    """Canlı WebSocket + Backtest hibrit arayüz."""

    def __init__(self, **params):
        self.params = params
        # sembole özgü tamponlar (OHLCV dizileri)
        self._buf: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: {"open": [], "high": [], "low": [], "close": [], "volume": []}
        )
        # backtest için: SL yüzdesi (kaldıraç öncesi)
        self._sl_pct: float = params.get("sl_pct", 3.0)

    # ........................................................ live API .....
    def update_bar(self, symbol: str, bar: dict) -> None:
        """Binance kline JSON → kapanan mumu diziye ekler."""
        k = bar["k"]
        if not k["x"]:  # mum kapanmadı
            return
        buf = self._buf[symbol]
        buf["open"].append(float(k["o"]))
        buf["high"].append(float(k["h"]))
        buf["low"].append(float(k["l"]))
        buf["close"].append(float(k["c"]))
        buf["volume"].append(float(k["v"]))
        # buffer uzunluğunu sınırlı tut
        maxlen = 600
        for arr in buf.values():
            if len(arr) > maxlen:
                del arr[: len(arr) - maxlen]

    @abstractmethod
    def _live_signal(self, o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray) -> Optional[str]:
        """+1 / -1 / None"""

    def generate_signal(self, symbol: str) -> Optional[str]:
        buf = self._buf.get(symbol)
        if not buf or len(buf["close"]) < 2:
            return None
        o = np.asarray(buf["open"], dtype=float)
        h = np.asarray(buf["high"], dtype=float)
        l = np.asarray(buf["low"], dtype=float)
        c = np.asarray(buf["close"], dtype=float)
        v = np.asarray(buf["volume"], dtype=float)
        return self._live_signal(o, h, l, c, v)

    # ........................................................ back‑test ....
    @staticmethod
    @abstractmethod
    def generate_signals(df: pd.DataFrame) -> pd.Series:
        """Vektörleştirilmiş +1/0/-1 sinyal serisi döndürür."""

    # ........................................................ yardımcı .....
    def sl_pct(self) -> float:  # Engine, risk hesap için kullanır
        return self._sl_pct


