# live/streamer.py
import asyncio, time
from collections import defaultdict
from utils.bar_store import BarStore
from utils.logger import setup_logger
from utils.interfaces import IStreamer
from binance import BinanceSocketManager
import asyncio

log = setup_logger("Streamer")

TF_SEC = {"1m":60, "5m":300, "15m":900, "30m":1800,
          "1h":3600, "2h":7200, "4h":14400,
          "6h":21600, "8h":28800, "12h":43200}

class Streamer(IStreamer):
    
    def __init__(self, client, symbols, intervals, bar_store: BarStore):
        self.client   = client
        self.symbols  = [s.upper().replace("/","") for s in symbols]
        self.intervals= intervals
        self.bar_store= bar_store
        self.queue    = asyncio.Queue()
        self.bsm      = BinanceSocketManager(self.client)
        
        # partial bar tamponu
        self.partial = defaultdict(
            lambda: {"o":None,"h":0,"l":1e18,"c":None,
                     "v":0,"start":None,"i":None,"x":False}
        )

    # -----------------------------------------------------------------
    async def _fetch_kline(self, client, sym, tf, limit):
        try:
            kl = await client.futures_klines(symbol=sym, interval=tf, limit=limit)
            return sym, tf, kl
        except Exception as e:
            log.warning("%s | %s preload hata: %s", sym, tf, e)
            return sym, tf, None
    
    async def preload_history(self, symbols, intervals, limit=250, batch=50):
        tasks = []
        for tf in intervals:
            for sym in symbols:
                tasks.append(self._fetch_kline(self.client, sym, tf, limit))

        # batch‑batch gönder, Binance weight sınırına takılma
        for i in range(0, len(tasks), batch):
            chunk = tasks[i:i + batch]
            results = await asyncio.gather(*chunk)
            for sym, tf, klines in results:
                if not klines:
                    continue
                for k in klines:
                    self.bar_store.add_bar(sym, tf, {
                        "t":k[0],"T":k[6],"o":k[1],"h":k[2],
                        "l":k[3],"c":k[4],"v":k[5],
                        "x":True,"i":tf})
                log.info("Preloaded %s × %s bars (%s)",
                        sym, len(klines), tf)

            # Binance weight rahatlasın
            await asyncio.sleep(1)

    # -----------------------------------------------------------------
    async def _stream_aggregate(self):
        sock = self.bsm.futures_socket(path="!miniTicker@arr")
        async with sock as stream:
            async for arr in stream:
                ts = int(arr[0]["E"]//1000)
                for t in arr:
                    sym = t["s"]
                    if sym not in self.symbols: continue
                    self._update_partial(sym, float(t["c"]),
                                         float(t["q"]), ts)

    def _update_partial(self, sym, price, vol, ts):
        for tf in self.intervals:
            bucket = ts - ts % TF_SEC[tf]
            buf = self.partial[(sym, tf)]
            if buf["start"] != bucket:          # bar kapanıyor
                if buf["start"] is not None:    # eski barı kapat
                    buf["x"] = True
                    self.bar_store.add_bar(sym, tf, buf.copy())
                    asyncio.create_task(
                        self.queue.put({"s":sym, "k":buf.copy()}))
                buf.update(o=price,h=price,l=price,c=price,
                           v=vol,start=bucket,i=tf,x=False)
            else:                               # bar açık
                buf["c"] = price
                buf["h"] = max(buf["h"], price)
                buf["l"] = min(buf["l"], price)
                buf["v"] += vol

    # -----------------------------------------------------------------
    async def start(self):
        self.task = asyncio.create_task(self._stream_aggregate())
        log.info("Aggregate miniTicker stream açıldı – %s sembol | tf=%s",
                 len(self.symbols), self.intervals)

    async def stop(self):
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)
        await self.client.close_connection()
        log.info("Streamer durduruldu.")

    # IStreamer interface
    def get_queue(self): return self.queue
    async def get(self):  return await self.queue.get()

    # -----------------------------------------------------------------
    @staticmethod
    async def resolve_symbols(client, coins_spec):
        """
        coins_spec  ->  ["BTCUSDT", ...]   veya   "ALL_USDT"   veya ["ALL_USDT"]
        """
        # 1) Liste ama tek elemanı ALL_USDT ise —> toplu mod
        if isinstance(coins_spec, (list, tuple)) and len(coins_spec) == 1 \
        and coins_spec[0].upper() == "ALL_USDT":
            coins_spec = "ALL_USDT"

        if coins_spec == "ALL_USDT":
            try:
                info = await client.futures_exchange_info()
                return [s["symbol"] for s in info["symbols"]
                        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"]
            except Exception as e:
                log.error("Exchange info alınamadı: %s", e)
                return []

        # 2) Normal liste yolu
        return [sym.upper().replace("/", "")
                for sym in coins_spec if isinstance(sym, str)]
