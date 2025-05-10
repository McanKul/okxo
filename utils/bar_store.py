# utils/bar_store.py
from collections import defaultdict
from typing import Dict, List

class BarStore:
    """
    Tüm sembol‑timeframe kombinasyonları için ortak OHLCV tamponu.
    ▸ add_bar(...)   : Streamer içinden bar ekler
    ▸ get_ohlcv(...) : Stratejiler buradan veri çeker
    """

    def __init__(self, maxlen: int = 600):
        self._maxlen = maxlen
        # data[(symbol, timeframe)] = {"open": [...], "high": [...], ...}
        self._data: Dict[tuple[str, str], Dict[str, List[float]]] = defaultdict(
            lambda: {"open": [], "high": [], "low": [], "close": [], "volume": []}
        )

    # ---------------- Streamer tarafından çağrılır -----------------
    def add_bar(self, symbol: str, tf: str, k: dict) -> None:
        """Binance kline JSON’dan kapanan mumu ekle."""
        if not k.get("x"):   # mum kapanmadı
            return
        buf = self._data[(symbol, tf)]
        buf["open"].append(float(k["o"]))
        buf["high"].append(float(k["h"]))
        buf["low"].append(float(k["l"]))
        buf["close"].append(float(k["c"]))
        buf["volume"].append(float(k["v"]))

        # maxlen koruması
        for arr in buf.values():
            if len(arr) > self._maxlen:
                del arr[: len(arr) - self._maxlen]

    # ---------------- Stratejiler tarafından çağrılır --------------
    def get_ohlcv(self, symbol: str, tf: str) -> dict[str, List[float]]:
        """Kopya değil referans döner – strateji doğrudan kullanabilir."""
        return self._data[(symbol, tf)]
