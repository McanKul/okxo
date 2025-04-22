import numpy as np
import pandas as pd

def compute_rsi(close_prices, period=14):
    delta = np.diff(close_prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = np.convolve(gain, np.ones((period,)) / period, mode='valid')
    avg_loss = np.convolve(loss, np.ones((period,)) / period, mode='valid')

    rs = avg_gain / (avg_loss + 1e-10)  # 0'a bölmeyi engelle
    rsi = 100 - (100 / (1 + rs))

    return np.concatenate(([None]*(period), rsi))

def compute_ema(prices, period=14):
    ema = pd.Series(prices).ewm(span=period, adjust=False).mean()
    return ema.to_numpy()

def compute_macd(prices):
    ema12 = compute_ema(prices, 12)
    ema26 = compute_ema(prices, 26)
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().to_numpy()
    return macd_line, signal_line

def compute_bollinger_bands(prices, period=20, num_std=2):
    prices = pd.Series(prices)
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()

    upper_band = sma + num_std * std
    lower_band = sma - num_std * std
    return upper_band.to_numpy(), lower_band.to_numpy()


def detect_volume_spike(volumes, period=20, multiplier=2):
    volumes = pd.Series(volumes)
    avg_volume = volumes.rolling(window=period).mean()
    return volumes > (avg_volume * multiplier)
