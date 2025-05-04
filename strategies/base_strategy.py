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



class BaseStrategy(IStrategy):
    def __init__(self, bar_store, symbol, timeframe, **params):
        self.bar_store = bar_store      # <–– merkezi tampon
        self.symbol     = symbol
        self.tf         = timeframe
        self.params     = params
        self._sl_pct    = params.get("sl_pct", 3.0)

    # artık kendi _buf’u yok!

    # ........................................................ live API
    def update_bar(self, symbol: str, bar: dict) -> None:
        # bu metot merkezi tamponu dolduracak şekilde güncellenmez;
        # çünkü Streamer doğrudan BarStore.add_bar() çağıracak.
        pass  # BaseStrategy bu işi yapmaz

    def generate_signal(self, _sym: str = None) -> Optional[str]:
        buf = self.bar_store.get_ohlcv(self.symbol, self.tf)
        if len(buf["close"]) < 2:
            return None
        import numpy as np
        c = np.asarray(buf["close"], dtype=float)
        h = np.asarray(buf["high"],  dtype=float)
        l = np.asarray(buf["low"],   dtype=float)
        o = np.asarray(buf["open"],  dtype=float)
        v = np.asarray(buf["volume"],dtype=float)
       
        return self._live_signal(o, h, l, c, v)
    
    def sl_pct(self) -> float:          # artık soyut değil
        return self._sl_pct
    