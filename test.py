import pandas as pd
import numpy as np
from itertools import product
from multiprocessing import Pool, cpu_count
from functools import partial

# Veriyi yükle
df = pd.read_csv("Data/BTC_1hour.csv")
df["close"] = df["close"].astype(float)
df["volume"] = df["volume"].astype(float)
prices = df["close"].to_numpy()
volumes = df["volume"].to_numpy()


def macd_ema_strategy(data):
    ema12 = pd.Series(data).ewm(span=12).mean()
    ema26 = pd.Series(data).ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    ema200 = pd.Series(data).ewm(span=200).mean()

    if macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
        if data[-1] > ema200.iloc[-1]:
            return "BUY"
    elif macd.iloc[-2] > signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]:
        if data[-1] < ema200.iloc[-1]:
            return "SELL"
    return None

def bollinger_bounce(data):
    close = pd.Series(data)
    sma = close.rolling(window=20).mean()
    std = close.rolling(window=20).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    if close.iloc[-2] < lower.iloc[-2] and close.iloc[-1] > lower.iloc[-1]:
        return "BUY"
    elif close.iloc[-2] > upper.iloc[-2] and close.iloc[-1] < upper.iloc[-1]:
        return "SELL"
    return None

def triple_ema_reversal(data):
    close = pd.Series(data)
    ema_21 = close.ewm(span=21).mean()
    ema_55 = close.ewm(span=55).mean()
    ema_100 = close.ewm(span=100).mean()

    if ema_21.iloc[-2] < ema_55.iloc[-2] and ema_21.iloc[-1] > ema_55.iloc[-1] and close.iloc[-1] > ema_100.iloc[-1]:
        return "BUY"
    elif ema_21.iloc[-2] > ema_55.iloc[-2] and ema_21.iloc[-1] < ema_55.iloc[-1] and close.iloc[-1] < ema_100.iloc[-1]:
        return "SELL"
    return None

def rsi_divergence_lite(data):
    close = pd.Series(data)
    delta = close.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] < 30 and rsi.iloc[-2] < rsi.iloc[-1]:
        return "BUY"
    elif rsi.iloc[-1] > 70 and rsi.iloc[-2] > rsi.iloc[-1]:
        return "SELL"
    return None

def volume_rsi_oversold(data, volume):
    close = pd.Series(data)
    delta = close.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    vol_series = pd.Series(volume)
    vol_avg = vol_series.rolling(window=20).mean()
    if rsi.iloc[-1] < 30 and vol_series.iloc[-1] > vol_avg.iloc[-1] * 1.5:
        return "BUY"
    return None

def evaluate_futures_result(prices, entry_index, position_type,
                            capital=1000, leverage=20,
                            target_profit=5, stop_loss=50):
    entry_price = prices[entry_index]
    position_size = (capital * leverage) / entry_price
    tp = entry_price + (target_profit / position_size) if position_type == "BUY" else entry_price - (target_profit / position_size)
    sl = entry_price - (stop_loss / position_size) if position_type == "BUY" else entry_price + (stop_loss / position_size)

    for i in range(1, 21):
        if entry_index + i >= len(prices):
            break
        price = prices[entry_index + i]
        if position_type == "BUY" and price >= tp:
            return "WIN"
        if position_type == "BUY" and price <= sl:
            return "LOSS"
        if position_type == "SELL" and price <= tp:
            return "WIN"
        if position_type == "SELL" and price >= sl:
            return "LOSS"
    return "HOLD"

# Strateji testi (volume olup olmamasına göre)
def test_strategy_with_params(strategy_func, prices, volume, name, tp, sl):
    results = {"WIN": 0, "LOSS": 0, "HOLD": 0, "TOTAL": 0}
    for i in range(100, len(prices) - 20):
        data_slice = prices[i-100:i]
        signal = strategy_func(data_slice) if volume is None else strategy_func(data_slice, volume[i-100:i])
        if signal:
            result = evaluate_futures_result(prices, i, signal, target_profit=tp, stop_loss=sl)
            results[result] += 1
            results["TOTAL"] += 1
    winrate = (results["WIN"] / results["TOTAL"] * 100) if results["TOTAL"] > 0 else 0
    return {
        "strategy": name,
        "take_profit": tp,
        "stop_loss": sl,
        "winrate": round(winrate, 2),
        "details": results
    }

# Her parametre kombinasyonunu test et
def run_all_params_for_strategy(strategy_func, name, prices, volumes, tp_range, sl_range):
    print(f"Başlıyor: {name}")
    volume_needed = "volume" in strategy_func.__code__.co_varnames
    volume_data = volumes if volume_needed else None

    param_combinations = list(product(tp_range, sl_range))
    results = []

    for idx, (tp, sl) in enumerate(param_combinations, 1):
        print(f"[{name}] Test {idx}/{len(param_combinations)} → TP: {tp}, SL: {sl}")
        result = test_strategy_with_params(strategy_func, prices, volume_data, name, tp, sl)
        results.append(result)

    sorted_results = sorted(results, key=lambda x: x["winrate"], reverse=True)
    return {
        "strategy": name,
        "best_10": sorted_results[:10],
        "worst_10": sorted_results[-10:]
    }

# Stratejiler listesi
strategies = [
    (macd_ema_strategy, "MACD + EMA Crossover"),
    (bollinger_bounce, "Bollinger Bands Bounce"),
    (triple_ema_reversal, "Triple EMA Reversal"),
    (rsi_divergence_lite, "RSI Divergence Lite"),
    (volume_rsi_oversold, "Volume + RSI Oversold")
]

tp_range = range(1, 101)
sl_range = range(50, 101)

# Paralel çalıştır
if __name__ == "__main__":
    with Pool(processes=min(cpu_count(), len(strategies))) as pool:
        func = partial(run_all_params_for_strategy, prices=prices, volumes=volumes,
                       tp_range=tp_range, sl_range=sl_range)
        results = pool.starmap(func, strategies)

    for strategy_result in results:
        print(f"\n=== {strategy_result['strategy']} ===")
        print(">>> BEST 10:")
        for r in strategy_result['best_10']:
            print(f"TP: {r['take_profit']}, SL: {r['stop_loss']}, Winrate: {r['winrate']}%, Details: {r['details']}")
        print(">>> WORST 10:")
        for r in strategy_result['worst_10']:
            print(f"TP: {r['take_profit']}, SL: {r['stop_loss']}, Winrate: {r['winrate']}%, Details: {r['details']}")
