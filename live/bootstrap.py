# live/bootstrap.py
"""
Her sembol & timeframe için son N kapanmış mum REST ile çekilir ve
strategy.update_bar() aracılığıyla tamponlar hemen doldurulur.
"""
from binance.client import Client
import os, logging, time, math

log = logging.getLogger("Bootstrap")

async def preload_history(client: Client, strategy, symbols, interval="1m", limit=250):
    """Websocket başlamadan önce geçmiş mumları tamponlara işler."""
    # Binance REST interval -> ms süre
    tf_ms = {
        "1m": 60_000, "3m": 180_000, "5m": 300_000,
        "15m": 900_000, "1h": 3_600_000
    }[interval]

    for sym in symbols:
        try:
            klines = await client.futures_klines(symbol=sym,
                                           interval=interval,
                                           limit=limit)
        except Exception as e:
            log.warning("%s preload REST hatası: %s", sym, e)
            continue

        # Sadece kapanmış bar’ı websocket formatına yakınlaştır
        for open_t, o,h,l,c,v, close_t, *_ in klines:
            msg = {
                "e": "kline", "s": sym,
                "k": {
                    "x": True,              # closed
                    "t": open_t,
                    "T": close_t-1,
                    "o": o, "h": h, "l": l, "c": c, "v": v
                }
            }
            strategy.update_bar(sym, msg)

        log.info("Preloaded %s × %s bars into strategy", sym, limit)

        # Son preload bar’ının kapanış zamanını döndür (taze veriyi atlamamak için)
        last_close = klines[-1][6]  # close_time in ms
        now_ms = int(time.time()*1000)
        # Eğer websocket açılana kadar bir iki bar geçmişse strategy eksik kalmasın
        missing = math.floor((now_ms - last_close) / tf_ms)
        if missing:
            log.info("%s son preload’tan bu yana %s bar geçmiş (rest limit yetmedi)", sym, missing)
