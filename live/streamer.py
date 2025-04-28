"""
streamer.py - Asynchronous WebSocket streamer using BinanceSocketManager.
"""
import asyncio
import logging
from binance import BinanceSocketManager

log = logging.getLogger("Streamer")

class Streamer:
    """
    Streams kline data for given symbols asynchronously.
    """
    def __init__(self, client, symbols, interval: str = "1m"):
        self.client = client
        self.symbols = [sym.replace("/", "").upper() for sym in symbols]
        self.interval = interval
        self.queue = asyncio.Queue()
        self.bsm = BinanceSocketManager(self.client)
        self.tasks = []

    async def _stream_symbol(self, symbol: str):
        """
        Stream kline data for one symbol and put closed bars into queue.
        """
        socket = self.bsm.kline_socket(symbol=symbol, interval=self.interval)
        async with socket as stream:
            while True:
                msg = await stream.recv()
                k = msg.get("k", {})
                # Emit only when candle is closed
                if k.get("x"):
                    await self.queue.put(msg)

    async def start(self):
        """
        Start streaming for all symbols asynchronously.
        """
        for sym in self.symbols:
            task = asyncio.create_task(self._stream_symbol(sym))
            self.tasks.append(task)
        log.info("Streamer started for symbols: %s", self.symbols)

    async def get(self):
        """
        Asynchronously get a message (closed bar) from the queue.
        """
        return await self.queue.get()

    async def stop(self):
        """
        Stop all streaming tasks and close the Binance connection.
        """
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        try:
            await self.client.close_connection()
        except Exception:
            pass
        log.info("Streamer stopped.")
