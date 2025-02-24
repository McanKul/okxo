import ccxt
import time
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Binance API anahtarlarınızı buraya ekleyin
api_key = ''
api_secret = ''

# Binance bağlantısı oluştur
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})

def fetch_futures_symbols_1m_candles(symbol):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=2)
        if len(candles) >= 2:
            price_change = ((candles[1][4] - candles[0][4]) / candles[0][4]) * 100.0
            if price_change > 0.01 or price_change < -0.01:
                print(f"Symbol: {symbol}, Last 1 Minute Price Change: {price_change:.2f}%")
        else:
            print(f"Symbol: {symbol}, Not enough data for calculation")
    except ccxt.NetworkError as e:
        print(f"NetworkError: {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError: {e}")

def main():
    try:
        markets = exchange.fapiPublicGetExchangeInfo()
        symbols = [market['symbol'] for market in markets['symbols'] if market['quoteAsset'] == 'USDT']
        
        # 1 dakika beklemek için başlangıç zamanını kaydet
        start_time = time.time()
        
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time >= 10:
                for symbol in symbols:
                    try:
                        fetch_futures_symbols_1m_candles(symbol)
                    except ccxt.NetworkError as e:
                        print(f"NetworkError: {e}")
                    except ccxt.ExchangeError as e:
                        print(f"ExchangeError: {e}")
                
                # Başlangıç zamanını güncelle
                start_time = time.time()

            # Küçük bir bekleme süresi ekleyerek döngüyü kontrol et
            time.sleep(1)
    except ccxt.NetworkError as e:
        print(f"NetworkError: {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError: {e}")

if __name__ == '__main__':
    main()