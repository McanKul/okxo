import numpy as np
import talib

def rsi_midline_crossover_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    RSI Midline Crossover Strategy

    - period: RSI hesaplama periyodu (varsayılan 14)
    - midline: RSI için orta çizgi eşiği (50)
    - BUY: RSI 50 altından 50 üstüne kesiş yaparsa
    - SELL: RSI 50 üstünden 50 altına kesiş yaparsa
    """
    period = 14
    midline = 50

    # Yeterli veri yoksa sinyal üretme
    if close_prices is None or len(close_prices) < period + 2:
        return None

    # TA-Lib ile RSI serisini hesapla
    rsi_series = talib.RSI(close_prices, timeperiod=period)

    prev_rsi = rsi_series[-2]
    curr_rsi = rsi_series[-1]

    # Geçersiz değer kontrolü
    if np.isnan(prev_rsi) or np.isnan(curr_rsi):
        return None

    # Midline crossover sinyalleri
    if prev_rsi < midline and curr_rsi > midline:
        return "BUY"
    elif prev_rsi > midline and curr_rsi < midline:
        return "SELL"
    else:
        return None

def rsi_crossover_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    RSI Crossover Strategy using TA-Lib.

    BUY  → RSI, oversold_threshold'ün altındayken üzerini kestiğinde
    SELL → RSI, overbought_threshold'ün üstündeyken altını kestiğinde
    """
    period = 14
    overbought_threshold = 70
    oversold_threshold   = 30

    # Yeterli veri yoksa
    if close_prices is None or len(close_prices) < period + 2:
        return None

    # RSI dizisini hesapla
    rsi_series = talib.RSI(np.asarray(close_prices), timeperiod=period)
    prev_rsi, curr_rsi = rsi_series[-2], rsi_series[-1]

    if np.isnan(prev_rsi) or np.isnan(curr_rsi):
        return None

    # SELL: önce üzerindeydi, sonra altına indi
    if prev_rsi > overbought_threshold and curr_rsi < overbought_threshold:
        return "SELL"

    # BUY: önce altındaydı, sonra üstüne çıktı
    if prev_rsi < oversold_threshold and curr_rsi > oversold_threshold:
        return "BUY"

    return None


def rsi_threshold_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    RSI Threshold Strategy using TA-Lib.

    Parameters:
    - close_prices: numpy array of closing prices
    - high_prices, low_prices, volume_prices: unused here but kept for consistency
    """
    # Parametreler
    period = 14  # RSI hesaplama periyodu
    overbought_threshold = 80
    oversold_threshold = 20

    # Yeterli veri yoksa sinyal yok
    if close_prices is None or len(close_prices) < period + 1:
        return None

    # TA-Lib ile RSI hesapla
    rsi_series = talib.RSI(close_prices, timeperiod=period)
    # Son RSI değeri
    rsi = rsi_series[-1]

    # Sonucun geçerli olup olmadığını kontrol et
    if np.isnan(rsi):
        return None

    # Son RSI değerine göre sinyal üret
    if rsi > overbought_threshold:
        return "SELL"
    elif rsi < oversold_threshold:
        return "BUY"
    else:
        return None


# MACD Signal Strategy
def macd_signal_strategy(close_prices, high_prices, low_prices, volume_prices):
    # Parametreler
    fast_period = 12
    slow_period = 26
    signal_period = 9
    
    if close_prices is None or len(close_prices) < slow_period + 1:
        return None
    
    prices = close_prices
    alpha_fast = 2 / (fast_period + 1)
    alpha_slow = 2 / (slow_period + 1)
    alpha_signal = 2 / (signal_period + 1)
    
    # EMA başlangıç değerlerini ilk fiyata ayarla
    ema_fast = prices[0]
    ema_slow = prices[0]
    macd_series = []
    for price in prices:
        # Hızlı ve yavaş EMA'leri güncelle
        ema_fast = alpha_fast * price + (1 - alpha_fast) * ema_fast
        ema_slow = alpha_slow * price + (1 - alpha_slow) * ema_slow
        macd_series.append(ema_fast - ema_slow)
    # Sinyal çizgisini (MACD'nin EMA'sı) hesapla
    signal_val = macd_series[0]
    signal_series = [signal_val]
    for macd_val in macd_series[1:]:
        signal_val = alpha_signal * macd_val + (1 - alpha_signal) * signal_val
        signal_series.append(signal_val)
    # Son iki değer arasındaki kesişimi kontrol et
    if macd_series[-2] < signal_series[-2] and macd_series[-1] > signal_series[-1]:
        return "BUY"
    elif macd_series[-2] > signal_series[-2] and macd_series[-1] < signal_series[-1]:
        return "SELL"
    else:
        return None

# Bollinger Bands Bounce Strategy
def bollinger_bands_bounce_strategy(close_prices, high_prices, low_prices, volume_prices):
    # Parametreler
    period = 20
    std_dev_factor = 2
    
    if close_prices is None or len(close_prices) < period + 1:
        return None
    
    prices = close_prices
    # Önceki ve son periyot için bantları hesapla
    prev_window = prices[-(period+1):-1]
    curr_window = prices[-period:]
    prev_ma = np.mean(prev_window)
    prev_std = np.std(prev_window)
    curr_ma = np.mean(curr_window)
    curr_std = np.std(curr_window)
    prev_upper = prev_ma + std_dev_factor * prev_std
    prev_lower = prev_ma - std_dev_factor * prev_std
    curr_upper = curr_ma + std_dev_factor * curr_std
    curr_lower = curr_ma - std_dev_factor * curr_std
    
    # Fiyat alt bandın altından yukarı sekmiş mi?
    if prices[-2] < prev_lower and prices[-1] > curr_lower:
        return "BUY"
    # Fiyat üst bandın üstünden aşağı sekmiş mi?
    elif prices[-2] > prev_upper and prices[-1] < curr_upper:
        return "SELL"
    else:
        return None

# Volume Spike Reversal Strategy
def volume_spike_reversal_strategy(close_prices, high_prices, low_prices, volume_prices):
    # Parametreler
    period = 20
    volume_threshold = 2.0  # ortalama hacmin katı
    
    if volume_prices is None or len(volume_prices) < period + 1 or close_prices is None or len(close_prices) < 2:
        return None
    
    vol = volume_prices
    prices = close_prices
    # Son periyot (period) ortalama hacmi (güncel hariç)
    avg_vol = np.mean(vol[-(period+1):-1])
    current_vol = vol[-1]
    # Hacimde ani artış (sıçrama) var mı?
    if current_vol > volume_threshold * avg_vol:
        # Fiyat değişiminin yönünü kontrol et
        if prices[-1] > prices[-2]:
            # Yükseliş trendi sonunda hacim patlaması -> tepe noktası
            return "SELL"
        elif prices[-1] < prices[-2]:
            # Düşüş trendi sonunda hacim patlaması -> dip noktası
            return "BUY"
    return None

# RSI + MACD Divergence Strategy
def rsi_macd_divergence_strategy(close_prices, high_prices, low_prices, volume_prices):
    # Parametreler
    rsi_period = 14
    fast_period = 12
    slow_period = 26
    signal_period = 9
    lookback_window = 30  # uyumsuzluk kontrolü için bakılan süre
    
    if close_prices is None:
        return None
    length = len(close_prices)
    if length < max(slow_period + 1, lookback_window + 1):
        return None
    
    prices = close_prices
    # Tüm fiyat verisi için RSI serisini hesapla
    gains = np.zeros(length)
    losses = np.zeros(length)
    for i in range(1, length):
        diff = prices[i] - prices[i-1]
        gains[i] = diff if diff > 0 else 0
        losses[i] = -diff if diff < 0 else 0
    avg_gain = np.mean(gains[1:rsi_period+1])
    avg_loss = np.mean(losses[1:rsi_period+1])
    rsi_series = [None] * length
    # İlk RSI değeri (rsi_period. indekste)
    if avg_loss == 0:
        rsi_series[rsi_period] = 100
    else:
        rs = avg_gain / avg_loss
        rsi_series[rsi_period] = 100 - (100 / (1 + rs))
    curr_avg_gain = avg_gain
    curr_avg_loss = avg_loss
    # Tüm seri için RSI hesapla (Wilder's smoothing)
    for i in range(rsi_period+1, length):
        curr_avg_gain = (curr_avg_gain * (rsi_period - 1) + gains[i]) / rsi_period
        curr_avg_loss = (curr_avg_loss * (rsi_period - 1) + losses[i]) / rsi_period
        if curr_avg_loss == 0:
            rsi_series[i] = 100
        else:
            rs = curr_avg_gain / curr_avg_loss
            rsi_series[i] = 100 - (100 / (1 + rs))
    # Tüm seri için MACD (12,26) ve sinyal (9) serisini hesapla
    alpha_fast = 2 / (fast_period + 1)
    alpha_slow = 2 / (slow_period + 1)
    alpha_signal = 2 / (signal_period + 1)
    ema_fast = prices[0]
    ema_slow = prices[0]
    macd_series = []
    for price in prices:
        ema_fast = alpha_fast * price + (1 - alpha_fast) * ema_fast
        ema_slow = alpha_slow * price + (1 - alpha_slow) * ema_slow
        macd_series.append(ema_fast - ema_slow)
    signal_val = macd_series[0]
    signal_series = [signal_val]
    for macd_val in macd_series[1:]:
        signal_val = alpha_signal * macd_val + (1 - alpha_signal) * signal_val
        signal_series.append(signal_val)
    # Son lookback_window içindeki fiyat zirve/dip noktalarını bul
    window_segment = prices[-(lookback_window+1):]
    prev_segment = window_segment[:-1]
    current_price = window_segment[-1]
    prev_max_idx_local = int(np.argmax(prev_segment))
    prev_min_idx_local = int(np.argmin(prev_segment))
    prev_max_price = prev_segment[prev_max_idx_local]
    prev_min_price = prev_segment[prev_min_idx_local]
    prev_max_idx = length - (lookback_window + 1) + prev_max_idx_local
    prev_min_idx = length - (lookback_window + 1) + prev_min_idx_local
    
    # Uyumsuzluk kontrolü
    signal = None
    # Ayı uyumsuzluğu: fiyat yeni zirvede fakat RSI ve MACD önceki zirvenin altında
    if current_price > prev_max_price:
        if rsi_series[prev_max_idx] is not None:
            if rsi_series[-1] < rsi_series[prev_max_idx] and macd_series[-1] < macd_series[prev_max_idx]:
                signal = "SELL"
    # Boğa uyumsuzluğu: fiyat yeni dipte fakat RSI ve MACD önceki dipten yukarıda
    if current_price < prev_min_price:
        if rsi_series[prev_min_idx] is not None:
            if rsi_series[-1] > rsi_series[prev_min_idx] and macd_series[-1] > macd_series[prev_min_idx]:
                signal = "BUY"
    return signal

import numpy as np
import talib

def ema_crossover_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    EMA Crossover Strategy:
     - Fast EMA (5) ↑ Slow EMA (12) → BUY
     - Fast EMA (5) ↓ Slow EMA (12) → SELL
     - Filtre: RSI(14) ile aşırı alım/satım iptali
    """
    # Parametreler
    fast, slow, rsi_period = 5, 12, 14
    overbought, oversold = 70, 30

    if len(close_prices) < slow + 1:
        return None

    fast_ema = talib.EMA(close_prices, timeperiod=fast)
    slow_ema = talib.EMA(close_prices, timeperiod=slow)
    rsi      = talib.RSI(close_prices, timeperiod=rsi_period)

    prev_f, curr_f = fast_ema[-2], fast_ema[-1]
    prev_s, curr_s = slow_ema[-2], slow_ema[-1]
    curr_rsi = rsi[-1]

    # crossover
    if prev_f <= prev_s and curr_f > curr_s and curr_rsi < overbought:
        return "BUY"
    if prev_f >= prev_s and curr_f < curr_s and curr_rsi > oversold:
        return "SELL"
    return None


def bollinger_rsi_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    Bollinger Bands + RSI Bounce:
     - BB(20,2σ) alt banda dokunup dönüş + RSI<30 → BUY
     - BB üst banda dokunup dönüş + RSI>70 → SELL
    """
    period, dev_up, dev_down, rsi_period = 20, 2, 2, 14
    overbought, oversold = 70, 30

    if len(close_prices) < period:
        return None

    upper, middle, lower = talib.BBANDS(close_prices, timeperiod=period,
                                       nbdevup=dev_up, nbdevdn=dev_down)
    rsi = talib.RSI(close_prices, timeperiod=rsi_period)

    price = close_prices[-1]
    prev_price = close_prices[-2]
    curr_rsi = rsi[-1]

    # alt banda dokunup yukarı yön
    if prev_price < lower[-2] and price > lower[-1] and curr_rsi < oversold:
        return "BUY"
    # üst banda dokunup aşağı yön
    if prev_price > upper[-2] and price < upper[-1] and curr_rsi > overbought:
        return "SELL"
    return None


def range_support_resistance_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    Basit Destek/Direnç Range Stratejisi:
     - Son N çubuk içindeki yüksek/düşükleri destek/direnç olarak al.
     - Fiyat destekten dönerse BUY, dirençten dönerse SELL.
    """
    lookback = 20  # destek/direnç hesap periyodu
    if len(close_prices) < lookback + 1:
        return None

    window_highs = high_prices[-(lookback+1):-1]
    window_lows  = low_prices[-(lookback+1):-1]
    support = np.min(window_lows)
    resistance = np.max(window_highs)

    prev, curr = close_prices[-2], close_prices[-1]

    # destekten döndü mü?
    if prev < support and curr > support:
        return "BUY"
    # dirençten döndü mü?
    if prev > resistance and curr < resistance:
        return "SELL"
    return None


def supertrend_strategy(close_prices, high_prices, low_prices, volume_prices):
    """
    SuperTrend (ATR Tabanlı) Strategy:
     - ATR(10) x multiplier(2)
     - Fiyat üst trend çizgisi kırdıysa BUY, alt kırdıysa SELL
    """
    atr_period, multiplier = 10, 2
    if len(close_prices) < atr_period + 1:
        return None

    # ATR ve temel Band genişliği
    atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=atr_period)
    basic_upper = (high_prices + low_prices) / 2 + multiplier * atr
    basic_lower = (high_prices + low_prices) / 2 - multiplier * atr

    # SuperTrend çizgisi (basit, önceki ST kullanarak)
    st = np.zeros_like(close_prices)
    trend = np.zeros_like(close_prices, dtype=bool)  # True=up, False=down
    for i in range(1, len(close_prices)):
        if close_prices[i-1] <= basic_upper[i-1]:
            st[i] = basic_upper[i]
        else:
            st[i] = basic_lower[i]
        trend[i] = close_prices[i] > st[i]

    prev_trend, curr_trend = trend[-2], trend[-1]
    if not prev_trend and curr_trend:
        return "BUY"
    if prev_trend and not curr_trend:
        return "SELL"
    return None
