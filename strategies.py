from indicators import calculate_rsi, calculate_ema, calculate_macd, calculate_bollinger_bands, calculate_stochastic, calculate_williams_r
import numpy as np

# 1. RSI ve EMA Crossover Stratejisi
def rsi_ema_stratejisi(window):
    rsi = calculate_rsi(window, period=14)
    ema = calculate_ema(window, period=14)

    if rsi[-1] < 30 and window[-1] > ema[-1]:  # RSI aşırı satım, fiyat EMA'yı yukarı doğru kesiyor
        return "BUY"
    elif rsi[-1] > 70 and window[-1] < ema[-1]:  # RSI aşırı alım, fiyat EMA'yı aşağı doğru kesiyor
        return "SELL"
    else:
        return None

# 2. Double EMA Crossover Stratejisi
def double_ema_crossover(window):
    short_ema = calculate_ema(window, period=9)
    long_ema = calculate_ema(window, period=21)

    if short_ema[-1] > long_ema[-1]:
        return "BUY"
    elif short_ema[-1] < long_ema[-1]:
        return "SELL"
    else:
        return None

# 3. Trend Tersine Dönüş Stratejisi (RSI + MACD)
def trend_reversal_strategy(window, high, low, close):
    rsi = calculate_rsi(window, period=14)
    macd, macdsignal, macdhist = calculate_macd(window, fastperiod=12, slowperiod=26, signalperiod=9)

    # RSI aşırı alım veya aşırı satım seviyelerinde ve MACD sıfır çizgisine yaklaşması
    if rsi[-1] > 70 and macd[-1] < macdsignal[-1]:
        return "SELL"
    elif rsi[-1] < 30 and macd[-1] > macdsignal[-1]:
        return "BUY"
    else:
        return None

# 4. Bollinger Bands Bounce
def bollinger_bands_bounce(window, high, low, close):
    upperband, middleband, lowerband = calculate_bollinger_bands(window, period=20)
    
    if close[-1] > upperband[-1]:  # Fiyat üst bandı aşıyor
        return "SELL"
    elif close[-1] < lowerband[-1]:  # Fiyat alt bandı aşıyor
        return "BUY"
    else:
        return None

# 5. MACD + RSI Divergence (Lite Version)
def macd_rsi_divergence(window, high, low, close):
    rsi = calculate_rsi(window, period=14)
    macd, macdsignal, macdhist = calculate_macd(window, fastperiod=12, slowperiod=26, signalperiod=9)

    if macdhist[-1] > 0 and rsi[-1] < 30:
        return "BUY"
    elif macdhist[-1] < 0 and rsi[-1] > 70:
        return "SELL"
    else:
        return None

# 6. Volume + RSI Oversold
def volume_rsi_oversold(window, volume):
    rsi = calculate_rsi(window, period=14)
    
    if rsi[-1] < 30 and volume[-1] > np.mean(volume[-10:]):  # RSI aşırı satım, hacim artışı
        return "BUY"
    elif rsi[-1] > 70 and volume[-1] > np.mean(volume[-10:]):  # RSI aşırı alım, hacim artışı
        return "SELL"
    else:
        return None

# 7. Donchian Channel Breakout
def donchian_channel_breakout(window, high, low, close):
    upper = max(window)
    lower = min(window)

    if close[-1] > upper:
        return "BUY"
    elif close[-1] < lower:
        return "SELL"
    else:
        return None

# 8. Pivot Point Support/Resistance
def pivot_point_support_resistance(window, high, low, close):
    pivot = (high[-1] + low[-1] + close[-1]) / 3
    support = pivot - (high[-1] - low[-1])
    resistance = pivot + (high[-1] - low[-1])

    if close[-1] > resistance:
        return "BUY"
    elif close[-1] < support:
        return "SELL"
    else:
        return None

# 9. Ichimoku Cloud
def ichimoku_cloud(window, high, low, close):
    # Cloud'ı hesaplamak için gerekli fonksiyonları ekleyin
    # Bu çok karmaşık olduğu için burada varsayılan bir implementasyon yok, Ichimoku hesaplamaları talep edebilirsiniz
    return None

# 10. Parabolic SAR
def parabolic_sar(window, high, low, close):
    # Parabolic SAR hesaplaması için TA-Lib kullanılabilir
    return None
