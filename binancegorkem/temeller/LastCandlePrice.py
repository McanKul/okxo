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

def fetch_futures_symbols_1m_candles(symbol):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=2)
        if len(candles) >= 2:
            price_change = ((candles[-1][4] - candles[-2][4]) / candles[-2][4]) * 100.0
            print(f"Symbol: {symbol}, Last Candle Price Change: {price_change:.2f}%")
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
        while True:
            for symbol in symbols:
                try:
                    fetch_futures_symbols_1m_candles(symbol)
                except ccxt.NetworkError as e:
                    print(f"NetworkError: {e}")
                except ccxt.ExchangeError as e:
                    print(f"ExchangeError: {e}")

            # Her 1 dakikada bir kontrol et
            time.sleep(60)
    except ccxt.NetworkError as e:
        print(f"NetworkError: {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError: {e}")

if __name__ == '__main__':
    main()