import ccxt
import time

# Binance API anahtarlarınızı buraya ekleyin
api_key = ''
api_secret = ''

# Binance bağlantısı oluştur
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})

def fetch_usdt_symbols_1m_candles():
    try:
        markets = exchange.load_markets()
        usdt_symbols = [symbol for symbol in markets if 'USDT' in markets[symbol]['quote']]
        
        for symbol in usdt_symbols:
            try:
                candles = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=1)
                if candles:
                    print(f"Symbol: {symbol}, Close Price: {candles[0][4]}")
                else:
                    print(f"Symbol: {symbol}, No 1-minute candles available")
            except ccxt.NetworkError as e:
                print(f"NetworkError: {e}")
            except ccxt.ExchangeError as e:
                print(f"ExchangeError: {e}")
    except ccxt.NetworkError as e:
        print(f"NetworkError (load_markets): {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError (load_markets): {e}")

def main():
    while True:
        fetch_usdt_symbols_1m_candles()
        # Her 1 dakikada bir kontrol et
        time.sleep(60)

if __name__ == '__main__':
    main()