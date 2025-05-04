# live/streamer.py  – SOLID refactor: sembol çözümleme + geçmiş veri yükleme buraya taşındı
import asyncio

from binance import BinanceSocketManager
from utils.logger import setup_logger
log = setup_logger("Streamer")
class Streamer:
    """
    Verilen semboller ve zaman dilimleri için asenkron kline verisi yayınlar
    + sembol çözümleme ve geçmiş veri ön‑yükleme yardımcıları.
    """
    def __init__(self, client, symbols, intervals):
        self.client = client
        self.symbols = [s.replace("/", "").upper() for s in symbols]
        self.intervals = intervals if isinstance(intervals, (list, tuple)) else [intervals]
        self.queue = asyncio.Queue()
        self.bsm = BinanceSocketManager(self.client)
        self.tasks = []

    # ---------- Yardımcı statik metotlar ----------
    @staticmethod
    async def resolve_symbols(client, coins_spec):
        """
        coins_spec:  ["BTCUSDT","ETHUSDT"]  veya  "ALL_USDT"
        """
        if coins_spec == "ALL_USDT":
            try:
                info = await client.futures_exchange_info()
                return [s['symbol'] for s in info['symbols']
                        if s['quoteAsset'] == "USDT" and s['status'] == "TRADING"]
            except Exception as e:
                log.error("Exchange info alınamadı: %s", e)
                return []
        return [sym.replace("/", "").upper()
                for sym in coins_spec
                if isinstance(sym, str)]

    @staticmethod
    async def preload_history(client, symbols, intervals, strategies, global_limit=250):
        for tf in intervals:
            for sym in symbols:
                for strat in strategies:
                    if tf != strat["timeframe"]:  # sadece o timeframe ile eşleşen strateji
                        continue

                    try:
                        limit = strat["params"].get("history_limit", global_limit)
                        klines = await client.futures_klines(symbol=sym, interval=tf, limit=limit)
                    except Exception as e:
                        log.warning("%s | %s preload hatası: %s (%r)", sym, tf, str(e), e)
                        continue

                    for k in klines:
                        bar = {
                            "s": sym,
                            "k": {
                                "t": k[0], "T": k[6],
                                "o": k[1], "h": k[2],
                                "l": k[3], "c": k[4],
                                "v": k[5], "n": k[8],
                                "x": True, "i": tf
                            }
                        }
                        strat["instance"].update_bar(sym, bar)

                    log.info("Preloaded %s × %s bars (%s)", sym, limit, tf)
    # ---------- Dahili akış ----------
    async def _stream_multiplex(self, streams):
        try:
            socket = self.bsm.futures_multiplex_socket(streams)
        except Exception as e:
            log.error("Multiplex soket açılamadı: %s", e)
            return

        async with socket as stream:
            while True:
                try:
                    msg = await stream.recv()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    log.error("Veri akışı hatası: %s", e)
                    break
                data = msg.get("data", {})
                k = data.get("k", {})
                if k and k.get("x"):          # sadece kapanan mum
                    await self.queue.put({"s": data.get("s"), "k": k})

    # ---------- Dış API ----------
    async def start(self):
        streams = [f"{sym.lower()}@kline_{tf}"
                   for sym in self.symbols
                   for tf in self.intervals]

        
        max_per_stream = 50
        for i in range(0, len(streams), max_per_stream):
            chunk = streams[i:i + max_per_stream]
            self.tasks.append(asyncio.create_task(self._stream_multiplex(chunk)))

        log.info("Streamer başladı: %s sembol – %s tf", len(self.symbols), self.intervals)

    async def get(self):
        
        return await self.queue.get()

    async def stop(self):
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        try:
            await self.client.close_connection()
        except Exception:
            pass
        log.info("Streamer durduruldu.")
