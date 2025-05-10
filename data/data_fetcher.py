# data/data_fetcher.py
import pandas as pd
# CCXT kütüphanesini kullanarak Binance verisi çekebiliyoruz
import ccxt
import threading
import time
from binance import ThreadedWebsocketManager

class DataFetcher:
    def __init__(self, api_key=None, api_secret=None):
        self.exchange = ccxt.binance({
            'apiKey': api_key, 
            'secret': api_secret,
            'enableRateLimit': True
        })
    
    def fetch_ohlcv(self, symbol, timeframe="1m", since=None, limit=1000):
        """
        Binance'tan OHLCV verisi çeker (timestamp, open, high, low, close, volume).
        Parametreler:
            symbol: "BTC/USDT" gibi
            timeframe: '1m', '5m', '15m', '1h', '1d'
            since: Unix zaman damgası (ms). Bu tarihten itibaren veri çeker.
            limit: Maksimum çekilecek bar sayısı.
        """
        try:
            data = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        except Exception as e:
            print(f"Veri çekme hatası: {e}")
            return pd.DataFrame()  # Hata durumunda boş DataFrame
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def resample_ohlcv(self, df, timeframe):
        """
        Veriyi verilen zaman dilimine yeniden örnekler.
        Örneğin, 1 dakikadan 5 dakikaya dönüştürme.
        timeframe: pandas-uyumlu string: '5T' (5dk), '15T', '1H', '1D' vb.
        """
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        df_resampled = df.resample(timeframe).agg(ohlc_dict).dropna()
        return df_resampled


class WebsocketFetcher:
    def __init__(self, api_key, api_secret):
        self.twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
        self.twm.start()
    
    def start_klines_socket(self, symbol, interval, callback):
        """
        Gerçek zamanlı klines verisini başlatır. callback ile her yeni bar işlenir.
        """
        def handle_socket_message(msg):
            # msg 'kline' tipinde bir sözlük olarak gelir
            callback(msg)
        
        # Binance Python SDK websocket manager kullanımı
        self.twm.start_kline_socket(symbol=symbol.replace('/', ''), interval=interval, callback=handle_socket_message)
