import requests
import time
import datetime
import pandas as pd
from tqdm import tqdm
import os

# 1. USDT coinlerini al
def get_usdt_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    data = requests.get(url).json()
    usdt_symbols = [
        s['symbol'] for s in data['symbols']
        if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL'
    ]
    return usdt_symbols

# 2. Belirli coin, zaman aralığı ve tarih aralığına göre kline verisi çek
def get_klines(symbol, interval, start_time, end_time):
    url = "https://fapi.binance.com/fapi/v1/klines"
    all_data = []

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1500
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"HATA: {symbol} - {interval} - Kod: {response.status_code}")
            break

        data = response.json()
        if not data:
            break

        all_data.extend(data)
        start_time = data[-1][0] + 1
        time.sleep(0.1)  # Rate limit

    df = pd.DataFrame(all_data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
    ])

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    return df

# 3. 5 yıl önce timestamp
def get_5_years_ago_timestamp():
    dt = datetime.datetime.utcnow() - datetime.timedelta(days=5*365)
    return int(dt.timestamp() * 1000)

# 4. Main çalışma
def main():
    intervals = {
        "1m": "1minute", "3m": "3minute", "5m": "5minute", "15m": "15minute", "30m": "30minute",
        "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour", "8h": "8hour", "12h": "12hour",
        "1d": "1day", "3d": "3day", "1w": "1week", "1M": "1month"
    }

    symbols = get_usdt_symbols()
    start_time = get_5_years_ago_timestamp()
    end_time = int(datetime.datetime.utcnow().timestamp() * 1000)

    os.makedirs("Data", exist_ok=True)

    for symbol in tqdm(symbols, desc="Coinler"):
        base = symbol.replace("USDT", "")
        for interval, interval_name in intervals.items():
            filename = f"Data/{base}_{interval_name}.csv"
            if os.path.exists(filename):
                print(f"{filename} zaten var, atlanıyor.")
                continue

            print(f"{symbol} - {interval} veri çekiliyor...")
            try:
                df = get_klines(symbol, interval, start_time, end_time)
                if not df.empty:
                    df.to_csv(filename, index=False)
                    print(f"{filename} kaydedildi.")
                    time.sleep(60)
                else:
                    print(f"{symbol} - {interval} boş veri.")
            except Exception as e:
                print(f"HATA: {symbol} - {interval}: {e}")
                continue

if __name__ == "__main__":
    main()
