from __future__ import annotations
import logging
import numpy as np, pandas as pd, talib
from utils.logger import setup_logger
from utils.bar_store import BarStore
from utils.model_registry import load as load_model
from strategies.base_strategy import BaseStrategy

# Logger setup
logger = setup_logger(__name__, level=logging.DEBUG)

class Strategy(BaseStrategy):
    # ———— constructor ————
    def __init__(self, bar_store: BarStore, symbol: str, timeframe: str,
                 sl_pct: float = 3.0, **params):
        super().__init__(bar_store, symbol, timeframe, sl_pct, **params)
        self.model_buy  = load_model("volume_rsi_spike", timeframe, "buy")
        self.model_sell = load_model("volume_rsi_spike", timeframe, "sell")

    # ———— canlı sinyal ————
    def _live_signal(self, o, h, l, c, v):
        logger.debug("[LIVE]: Entering _live_signal with raw OHLCV lengths: %d, %d, %d, %d, %d",
                     len(o), len(h), len(l), len(c), len(v))
        raw = self._indicator_signal(c, v)            # +1 / -1 / None
        logger.debug("[LIVE] Raw indicator signal: %s", raw)
        if not raw:
            logger.debug("[LIVE] No raw signal generated, exiting _live_signal.")
            return None

        feats = self._features(o, h, l, c, v)
        logger.debug("[LIVE] Extracted features for model: %s", feats)
        model = self.model_buy if raw == "+1" else self.model_sell
        approve = bool(model.predict(feats)[0])
        logger.info("[LIVE] Model approval: %s for raw signal %s", approve, raw)
        if approve:
            logger.info("[LIVE] Live signal approved: %s", raw)
            return raw
        else:
            logger.debug("[LIVE] Live signal not approved, returning None.")
            return None

    # ———— 1) ham sinyal ————
    def _indicator_signal(self, c, v):
        logger.debug("[IND]: Entering _indicator_signal with close length %d", len(c))
        if len(c) < 60:
            logger.debug("[IND] Not enough data length < 60, returning None.")
            return None

        rsi_p    = int(self.params.get("rsi_period", 14))
        lookback = int(self.params.get("cross_lookback", 4))

        logger.debug("[IND] Computing RSI with period %d", rsi_p)
        rsi  = talib.RSI(c, timeperiod=rsi_p)
        vol  = pd.Series(v, dtype=float)
        ma20 = vol.rolling(20).mean()
        logger.debug("[IND] Last MA20: %s", ma20.iloc[-1])
        if np.isnan(ma20.iloc[-1]):
            logger.debug("[IND] MA20 is NaN, returning None.")
            return None

        # —— BUY tarafı
        spike = self._spike_ok(vol, ma20, self.params.get("buy_vol_mult", 2))
        rsi_prev, rsi_curr = rsi[-2], rsi[-1]
        buy_ok = spike and (rsi_prev < self.params.get("buy_low_th", 32) and rsi_curr > self.params.get("buy_high_th", 38))
        logger.debug("[BUY]: check → spike=%s, rsi_prev=%.2f, rsi_curr=%.2f, buy_ok=%s",
                     spike, rsi_prev, rsi_curr, buy_ok)
        if buy_ok:
            logger.info("[BUY] Indicator SIGNAL → +1 (BUY)")
            return "+1"
        else:
            logger.debug("[BUY] condition not met.")

        # —— SELL tarafı
        spike = self._spike_ok(vol, ma20, self.params.get("sell_vol_mult", 3))
        rsi_prev, rsi_curr = rsi[-2], rsi[-1]
        sell_ok = spike and (rsi_prev > self.params.get("sell_high_th", 70) and rsi_curr < self.params.get("sell_low_th", 65))
        logger.debug("[SELL]: check → spike=%s, rsi_prev=%.2f, rsi_curr=%.2f, sell_ok=%s",
                     spike, rsi_prev, rsi_curr, sell_ok)
        if sell_ok:
            logger.info("[SELL] Indicator SIGNAL → -1 (SELL)")
            return "-1"
        else:
            logger.debug("[SELL] condition not met.")

        logger.debug("[IND] No indicator signal (None).")
        return None

    @staticmethod
    def _spike_ok(vol, ma20, mult):   # yardımcı
        result = vol.iloc[-1] > ma20.iloc[-1] * float(mult)
        logger.debug("[SPIKE]: check → last_vol=%.2f, threshold=%.2f, result=%s",
                     vol.iloc[-1], ma20.iloc[-1] * float(mult), result)
        return result

    # ———— 2) model özellikleri ————
    def _features(self, o, h, l, c, v):
        logger.debug("[FEAT]: Extracting features from OHLCV arrays.")
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

        features = np.array([[rsi_val, ema20, ema50, boll_w, mom_val, adx_val, vol_rat]])
        logger.debug("[FEAT] Features array: %s", features)
        return features

    # ———— toplu back-test (opsiyonel) ————
    @staticmethod
    def generate_signals(df: pd.DataFrame):
        raise NotImplementedError
