# strategies/volume_rsi_spike.py
from __future__ import annotations
import numpy as np, pandas as pd, talib
from utils.bar_store import BarStore
from utils.model_registry import load as load_model
from strategies.base_strategy import BaseStrategy


class Strategy(BaseStrategy):
    # ———— constructor ————
    def __init__(self, bar_store: BarStore, symbol: str, timeframe: str,
                 sl_pct: float = 3.0, **params):
        super().__init__(bar_store, symbol, timeframe, sl_pct, **params)
        self.model_buy  = load_model("volume_rsi_spike", timeframe, "buy")
        self.model_sell = load_model("volume_rsi_spike", timeframe, "sell")
    
    # ———— canlı sinyal ————
    def _live_signal(self, o, h, l, c, v):
        raw = self._indicator_signal(c, v)            # +1 / -1 / None
        if not raw:
            return None

        feats = self._features(o, h, l, c, v)
        model = self.model_buy if raw == "+1" else self.model_sell
        approve = bool(model.predict(feats)[0])
        return raw if approve else None

    # ———— 1) ham sinyal ————
    def _indicator_signal(self, c, v):
        if len(c) < 60:
            return None

        rsi_p    = int(self.params.get("rsi_period", 14))
        lookback = int(self.params.get("cross_lookback", 4))

        rsi  = talib.RSI(c, timeperiod=rsi_p)
        vol  = pd.Series(v, dtype=float)
        ma20 = vol.rolling(20).mean()
        if np.isnan(ma20.iloc[-1]):
            return None

        rng = range(-lookback, 0)

        # —— BUY tarafı
        if self._spike_ok(vol, ma20,
                          self.params.get("buy_vol_mult", 2)) and \
           any(rsi[i-1] < self.params.get("buy_low_th", 32)
               and rsi[i] > self.params.get("buy_high_th", 38) for i in rng):
            return "+1"

        # —— SELL tarafı
        if self._spike_ok(vol, ma20,
                          self.params.get("sell_vol_mult", 3)) and \
           any(rsi[i-1] > self.params.get("sell_high_th", 70)
               and rsi[i] < self.params.get("sell_low_th", 65) for i in rng):
            return "-1"

        return None

    @staticmethod
    def _spike_ok(vol, ma20, mult):   # yardımcı
        return vol.iloc[-1] > ma20.iloc[-1] * float(mult)

    # ———— 2) model özellikleri ————
    def _features(self, o, h, l, c, v):
        close, high, low = map(np.asarray, (c, h, l))
        vol = pd.Series(v, dtype=float)

        rsi_val = talib.RSI(close, timeperiod=self.params.get("rsi_period", 14))[-1]
        ema20   = talib.EMA(close, 20)[-1]
        ema50   = talib.EMA(close, 50)[-1]
        up, mid, lo = talib.BBANDS(close, 20, 2, 2)
        boll_w  = (up[-1] - lo[-1]) / mid[-1]
        mom_val = talib.MOM(close, 10)[-1]
        adx_val = talib.ADX(high, low, close, 20)[-1]
        vol_rat = vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]

        return np.array([[rsi_val, ema20, ema50, boll_w, mom_val, adx_val, vol_rat]])

    # ———— toplu back‑test (opsiyonel) ————
    @staticmethod
    def generate_signals(df: pd.DataFrame):
        raise NotImplementedError
