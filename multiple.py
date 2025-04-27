from gpt import *
import numpy as np
import talib

def rsi_macd_confirm_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    RSI + MACD Onaylı Strateji:
    - AL sinyali: Hem RSI hem MACD aynı anda AL sinyali üretirse.
    - SAT sinyali: Hem RSI hem MACD aynı anda SAT sinyali üretirse.
    RSI burada 30/70 eşiklerini kullanarak kesişim yakalıyor, MACD ise sinyal çizgisi kesişimi.
    """
    close_prices = np.asarray(close_prices, dtype=float)
    high_prices  = np.asarray(high_prices,  dtype=float)
    low_prices   = np.asarray(low_prices,   dtype=float)
    volume_prices = np.asarray(volume_prices, dtype=float)
    # Yeterli veri kontrolü
    if close_prices is None or len(close_prices) < 100:
        return None
    # Son değerler için RSI ve MACD sinyalini hesapla
    rsi_sig = rsi_crossover_strategy(close_prices, high_prices, low_prices, volume_prices)
    macd_sig = macd_signal_strategy(close_prices, high_prices, low_prices, volume_prices)
    if rsi_sig == "BUY" and macd_sig == "BUY":
        return "BUY"
    if rsi_sig == "SELL" and macd_sig == "SELL":
        return "SELL"
    return None

def rsi_ema_trend_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    RSI Midline + EMA Trend Stratejisi:
    - Trend yönü EMA50 ve EMA200 ile belirlenir.
    - RSI 50 seviyesini trend yönünde kestiğinde sinyal üretir.
    """
    if close_prices is None or len(close_prices) < 200:
        return None
    closes = np.array(close_prices)
    # EMA değerlerini hesapla (TA-Lib kullanılabilir)
    short_ema = talib.EMA(closes, timeperiod=50)
    long_ema  = talib.EMA(closes, timeperiod=200)
    if np.isnan(short_ema[-1]) or np.isnan(long_ema[-1]):
        return None  # EMA henüz hesaplanamıyorsa
    trend_up = short_ema[-1] > long_ema[-1]
    trend_down = short_ema[-1] < long_ema[-1]
    # RSI’nin son iki değeri ile 50 kesişimini kontrol et
    rsi_series = talib.RSI(closes, timeperiod=14)
    prev_rsi, curr_rsi = rsi_series[-2], rsi_series[-1]
    if np.isnan(prev_rsi) or np.isnan(curr_rsi):
        return None
    # Yükselen trendde RSI 50'yi aşağıdan yukarı keserse AL
    if trend_up and prev_rsi < 50 and curr_rsi >= 50:
        return "BUY"
    # Düşen trendde RSI 50'yi yukarıdan aşağı keserse SAT
    if trend_down and prev_rsi > 50 and curr_rsi <= 50:
        return "SELL"
    return None


def rsi_macd_ema_triple_strategy(close_prices,
                                 high_prices,
                                 low_prices,
                                 volume_prices):
    """
    Triple-Confirm Strategy
    -------------------------------------------------------------
    AL (BUY)   : • RSI 30 bölgesinden yukarı kesiş (oversold çıkışı)  VE
                 • MACD bullish crossover                              VE
                 • EMA50 > EMA200  (yukarı trend onayı)

    SAT (SELL) : • RSI 70 bölgesinden aşağı kesiş (overbought çıkışı) VE
                 • MACD bearish crossover                             VE
                 • EMA50 < EMA200 (aşağı trend onayı)
    Diğer durumlarda None döner.
    """
    # ————— Veri yeterliliği —————
    if close_prices is None or len(close_prices) < 200 + 2:
        return None            # EMA200 + RSI için yeterli veri yok

    closes = np.asarray(close_prices, dtype=float)

    # ————— 1) RSI kesişimi —————
    rsi_series = talib.RSI(closes, timeperiod=14)
    prev_rsi, curr_rsi = rsi_series[-2], rsi_series[-1]

    if np.isnan(prev_rsi) or np.isnan(curr_rsi):
        return None

    rsi_buy  = prev_rsi < 30 and curr_rsi >= 30       # oversold çıkışı
    rsi_sell = prev_rsi > 70 and curr_rsi <= 70       # overbought çıkışı

    # ————— 2) MACD kesişimi —————
    macd, macd_signal, _ = talib.MACD(closes,
                                      fastperiod=12,
                                      slowperiod=26,
                                      signalperiod=9)
    prev_macd, prev_sig = macd[-2], macd_signal[-2]
    curr_macd, curr_sig = macd[-1], macd_signal[-1]

    macd_buy  = prev_macd < prev_sig and curr_macd > curr_sig   # bullish
    macd_sell = prev_macd > prev_sig and curr_macd < curr_sig   # bearish

    # ————— 3) EMA trend filtresi —————
    ema50  = talib.EMA(closes, timeperiod=50)[-1]
    ema200 = talib.EMA(closes, timeperiod=200)[-1]

    if np.isnan(ema50) or np.isnan(ema200):
        return None

    trend_up   = ema50 > ema200
    trend_down = ema50 < ema200

    # ————— Nihai sinyal (üçlü onay) —————
    if rsi_buy and macd_buy and trend_up:
        return "BUY"
    if rsi_sell and macd_sell and trend_down:
        return "SELL"
    return None
