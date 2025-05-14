# tests/test_volume_rsi_spike_logging.py

import logging
import numpy as np
import pytest
from strategies.volume_rsi_spike import Strategy

def make_array(length=61, start=1.0):
    return np.arange(start, start + length, dtype=float)

@pytest.mark.asyncio
async def test_indicator_logs_for_buy(monkeypatch, caplog):
    # 1) DummyModel ve talib.RSI patch’leri (önceki testlerden kopya)
    class DummyModel:
        def predict(self, X): return np.array([1])
    monkeypatch.setattr(
        "strategies.volume_rsi_spike.load_model",
        lambda name, timeframe, side: DummyModel()
    )
    # Fake RSI: son-1 düşük, son yüksek → buy branch
    monkeypatch.setattr(
        "strategies.volume_rsi_spike.talib.RSI",
        lambda carray, timeperiod: np.array([0.0]*(len(carray)-2) + [1.0,5.0], dtype=float)
    )

    # 2) caplog ayarları
    caplog.set_level(logging.DEBUG, logger="strategies.volume_rsi_spike")

    # 3) Strategy oluştur ve sinyal üret
    params = {
        "rsi_period": 2, "cross_lookback": 2,
        "buy_low_th": 2, "buy_high_th": 3, "buy_vol_mult": 1,
        "sell_low_th": 999, "sell_high_th": 1000, "sell_vol_mult": 1000,
    }
    strat = Strategy(None, "SYM", "1m", sl_pct=1.0, **params)
    o = make_array(); h = o+1; l = o-1; c = o.copy()
    v = np.array([100.0]*60 + [300.0], dtype=float)

    raw = strat._indicator_signal(c, v)
    assert raw == "+1"

    # 4) Log içeriğini kontrol et
    logs = caplog.text
    assert "[BUY]" in logs
    assert "Indicator SIGNAL → +1 (BUY)" in logs
