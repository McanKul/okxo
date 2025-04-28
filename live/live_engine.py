"""
live_engine.py - Asynchronous live trading engine.

Uses Binance AsyncClient and websockets to stream market data and execute trades.
"""
import asyncio
import logging
import time

from binance import AsyncClient
from strategies import load_strategy
from live.position_manager import PositionManager
from live.streamer import Streamer

class LiveEngine:
    """
    LiveEngine for handling live trading mode with asynchronous data streams.
    """
    def __init__(self, cfg, client: AsyncClient):
        self.cfg = cfg
        self.client = client
        self.symbols = []
        self.tf = cfg["timeframes"][0]  # Assuming at least one timeframe
        self.strategy = load_strategy(cfg["strategies"][0])
        self.symbols = []  # will be filled in async resolve
        self.pos_mgr = PositionManager(
            client=self.client,
            base_capital=cfg.get("base_usdt_per_trade", 10.0),
            leverage=cfg.get("leverage", 1),
            max_concurrent=cfg.get("max_concurrent", 1),
            default_sl_pct=cfg.get("sl_pct", 3.0),
            default_tp_pct=cfg.get("tp_pct", 6.0),
            max_holding_seconds=cfg.get("expire_sec", 300)
        )

    async def _resolve_symbols(self):
        """
        Resolve symbol list: use ALL_USDT or list from config.
        """
        coins = self.cfg.get("coins", [])
        if coins == "ALL_USDT":
            try:
                info = await self.client.futures_exchange_info()
            except Exception as e:
                logging.error("Error fetching exchange info: %s", e)
                return []
            return [s['symbol'] for s in info['symbols']
                    if s['quoteAsset'] == "USDT" and s['status'] == "TRADING"]
        symbols = []
        for sym in coins:
            if isinstance(sym, str):
                symbols.append(sym.replace("/", ""))
        return symbols

    async def preload_history(self, limit=250):
        """
        Preload historical candle data before starting live stream.
        """
        for sym in self.symbols:
            try:
                klines = await self.client.futures_klines(symbol=sym, interval=self.tf, limit=limit)
            except Exception as e:
                logging.warning(f"{sym} preload failed: {e}")
                continue
            for k in klines:
                # k: [open_time, open, high, low, close, volume, close_time, ...]
                bar = {
                    "s": sym,
                    "k": {
                        "t": k[0],
                        "T": k[6],
                        "o": k[1],
                        "h": k[2],
                        "l": k[3],
                        "c": k[4],
                        "v": k[5],
                        "n": k[8],
                        "x": True,
                    }
                }
                self.strategy.update_bar(sym, bar)

    async def run(self):
        # Resolve symbols (asynchronous)
        resolved = await self._resolve_symbols()
        
        if not resolved:
            logging.error("No symbols to trade. Exiting LiveEngine.")
            return
        self.symbols = resolved

        # Preload history if desired (based on config)
        history_limit = self.cfg.get("history_limit", 250)
        await self.preload_history(limit=history_limit)
        logging.info("program başladı")
        # Initialize streamer for live data
        streamer = Streamer(self.client, self.symbols, self.tf)
        await streamer.start()
        logging.info("LiveEngine started. Listening to market data...")

        try:
            while True:
                bar = await streamer.get()
                sym = bar.get("s")
                k = bar.get("k", {})
                if not sym or not k:
                    continue
                # Update strategy with new bar
                self.strategy.update_bar(sym, bar)
                # Generate trading signal
                sig = self.strategy.generate_signal(sym)
                # No signal: just update positions
                if sig is None:
                    await self.pos_mgr.update_all()
                    continue

                # Open new position based on signal
                if sig > 0:
                    await self.pos_mgr.open_long(sym)
                elif sig < 0:
                    await self.pos_mgr.open_short(sym)

                # Check exits for all positions
                await self.pos_mgr.update_all()

        except asyncio.CancelledError:
            logging.info("LiveEngine run cancelled.")
        except Exception as e:
            logging.error("Error in LiveEngine: %s", e)
        finally:
            # Stop streaming and close all positions
            await streamer.stop()
            await self.pos_mgr.force_close_all()
