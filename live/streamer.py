# streamer.py - Asenkron WebSocket yayınlayıcı (Binance futures kline) (çoklu timeframe desteği).
import asyncio
import logging
from binance import BinanceSocketManager

log = logging.getLogger("Streamer")

class Streamer:
    """
    Verilen semboller ve zaman dilimleri için asenkron kline verisi yayınlar.
    """
    def __init__(self, client, symbols, intervals):
        self.client = client
        # Sembolleri büyük harfe çevir ve formatla
        self.symbols = [sym.replace("/", "").upper() for sym in symbols]
        # interval tek str veya list olabilir
        if isinstance(intervals, (list, tuple)):
            self.intervals = intervals
        else:
            self.intervals = [intervals]
        self.queue = asyncio.Queue()
        self.bsm = BinanceSocketManager(self.client)
        self.tasks = []

    async def _stream_multiplex(self, streams):
        """
        Verilen stream isimleri için çoklu (multiplex) websocket bağlantısı açar.
        """
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
                # Sadece kapanan mumları al
                if k and k.get("x"):
                    sym = data.get("s")
                    bar = {"s": sym, "k": k}
                    await self.queue.put(bar)

    async def start(self):
        """
        Tüm semboller ve zaman dilimleri için yayın akışını başlatır (otomatik gruplayarak).
        """
        
        streams = []
        for sym in self.symbols:
            for interval in self.intervals:
                streams.append(f"{sym.lower()}@kline_{interval}")

        # Çoklu akışları gruplandır (örneğin, her grupta 50 stream)
        max_per_stream = 50
        for i in range(0, len(streams), max_per_stream):
            chunk = streams[i:i + max_per_stream]
            task = asyncio.create_task(self._stream_multiplex(chunk))
            self.tasks.append(task)
        log.info("Streamer başlatıldı (semboller/zaman dilimleri gruplandı): %s x %s", self.symbols, self.intervals)

    async def get(self):
        """
        Kuyruktan bir mesaj (kapanan mum) alır.
        """
        return await self.queue.get()

    async def stop(self):
        """
        Tüm yayın görevlerini durdurur ve Binance bağlantısını kapatır.
        """
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        try:
            await self.client.close_connection()
        except Exception:
            pass
        log.info("Streamer durduruldu.")
