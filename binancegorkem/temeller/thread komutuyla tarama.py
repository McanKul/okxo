import threading
import time
from binance.client import Client



def process_symbol(client, symbol):
    klines = client.futures_klines(symbol=symbol, interval='1m', limit=2)
    # Son 1 dakikalık mumun kapanış fiyatını al
    close_price = float(klines[-1][4])
    # İlk 1 dakikalık mumun kapanış fiyatını al
    prev_close_price = float(klines[0][4])
    # Fiyat değişimini hesapla
    price_change = ((close_price - prev_close_price) / prev_close_price) * 100

    # Fiyat değişimi %1 ve üzerindeyse
    if price_change >= 0.1:
        print(f"{symbol}: Son 1 dakikalık mum %1 ve üzerinde yükseldi.")
        # Burada short işlem açabilirsiniz
    elif price_change <= -0.1:
        print(f"{symbol}: Son 1 dakikalık mum %1 ve üzerinde düştü.")
        # Burada long işlem açabilirsiniz

def main():
    def task(symbol):
        process_symbol(client, symbol)

    # Binance API anahtarlarınızı buraya girin
    api_key = ''
    api_secret = ''

    # Client'ı oluştur
    client = Client(api_key, api_secret)

    # Tüm vadeli işlem coinlerini al
    exchange_info = client.futures_exchange_info()
    symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]

    # Thread'leri başlat
    threads = []
    for symbol in symbols:
        thread = threading.Thread(target=lambda: task(symbol))
        thread.start()
        threads.append(thread)

    # Thread'lerin bitmesini bekle
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()