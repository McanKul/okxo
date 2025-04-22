from strategies import rsi_ema_stratejisi, double_ema_crossover, trend_reversal_strategy, bollinger_bands_bounce, macd_rsi_divergence, volume_rsi_oversold
import pandas as pd

# Veriyi yükle
df = pd.read_csv("Data/BTC_1hour.csv")
close_prices = df["close"].astype(float).to_numpy()  # Kapanış fiyatları
high_prices = df["high"].astype(float).to_numpy()  # En yüksek fiyatlar
low_prices = df["low"].astype(float).to_numpy()  # En düşük fiyatlar
volume_prices = df["volume"].astype(float).to_numpy()  # Hacim

def evaluate_futures_result(prices, entry_index, position_type, capital=1000, leverage=20, target_profit=5, stop_loss=50):
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


def test_strategies(close_prices, high_prices, low_prices, volume_prices):
    strategies = {
        "RSI + EMA Crossover": rsi_ema_stratejisi,
        "Double EMA Crossover": double_ema_crossover,
        "Trend Reversal (RSI + MACD)": trend_reversal_strategy,
        "Bollinger Bands Bounce": bollinger_bands_bounce,
        "MACD + RSI Divergence": macd_rsi_divergence,
        "Volume + RSI Oversold": volume_rsi_oversold,
    }
    
    results = {}
    
    for strategy_name, strategy_func in strategies.items():
        wins = 0
        losses = 0
        holds = 0
        total = 0
        
        for i in range(100, len(close_prices)):  # 100'üncü indeksten itibaren işlemleri başlatıyoruz
            window = close_prices[i-100:i]
            signal = strategy_func(window, high_prices[i-100:i], low_prices[i-100:i], close_prices[i-100:i])

            if signal:
                # Bu sinyalin sonucunu evaluate_futures_result ile değerlendiriyoruz
                result = evaluate_futures_result(close_prices, i, signal)  # 'i' giriş indeksi, 'signal' pozisyon tipi
                if result == "WIN":
                    wins += 1
                elif result == "LOSS":
                    losses += 1
                elif result == "HOLD":
                    holds += 1
                total += 1
        
        if total > 0:
            win_rate = (wins / total) * 100
            results[strategy_name] = {
                "WIN": wins, "LOSS": losses, "HOLD": holds, "TOTAL": total, "WIN_RATE": win_rate
            }
    
    return results


# Stratejileri test etme
results = test_strategies(close_prices, high_prices, low_prices, volume_prices)

# Sonuçları yazdırma
for strategy_name, result in results.items():
    print(f"\nStrategy: {strategy_name}")
    print(f"✅ WIN: {result['WIN']} | ❌ LOSS: {result['LOSS']} | ⏳ HOLD: {result['HOLD']} | Total: {result['TOTAL']}")
    print(f"🏆 Win Rate: {round(result['WIN_RATE'], 2)} %")
