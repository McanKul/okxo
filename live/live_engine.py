# live_engine.py – SOLID refactor: yalnızca orkestrasyon
import asyncio
from utils.bar_store import BarStore
from utils.interfaces import IBroker, IStrategy
from strategies import load_strategy
from live.position_manager import PositionManager
from live.broker_binance import BinanceBroker
from live.streamer import Streamer
from utils.logger import setup_logger
log = setup_logger("LiveEngine")


class LiveEngine:
    def __init__(self, cfg, broker:IBroker):
        self.cfg     = cfg
        self.broker  = broker          # IBroker implementasyonu
        self.bar_store = BarStore()    # ⬅︎ merkezi tampon artık burada!

        # — Strateji konfiglerini hazırlayıp örneklerini yarat —
        self.strategies = []
        for scfg in cfg.get_strategies():
            instance = load_strategy(scfg,
                                     bar_store = self.bar_store,
                                     symbol     = scfg["coins"][0],   # örnek
                                     timeframe  = scfg["timeframe"])
            self.strategies.append({**scfg, "instance": instance})
        self.pos_mgr = PositionManager(self.broker, base_capital=cfg.get_base_usdt_per_trade(),
                                       max_concurrent=cfg.get_max_concurrent())
        # — Zaman dilimlerini çıkar —
        self.timeframes = list(s["timeframe"] for s in self.strategies)
        # Streamer henüz oluşturulmadı; run() içinde —
        self.streamer = None
        self.symbols  = []

    # -------------------------------------------------------------
    async def run(self):
        # 1) Sembolleri çöz
        self.symbols = await Streamer.resolve_symbols(
            self.broker.client, self.cfg.get_coins())

        # 2) Streamer oluştur (BarStore referansı veriyoruz)
        self.streamer = Streamer(self.broker.client,
                                 self.symbols,
                                 self.timeframes,
                                 bar_store=self.bar_store)

        # 3) Geçmiş mumları yükle
        await self.streamer.preload_history(
            self.symbols, self.timeframes,
            global_limit=self.cfg.get_history_limit())

        # 4) Canlı akışı başlat
        await self.streamer.start()
        log.info("Canlı motor başladı: %s sembol | tf=%s",
                 len(self.symbols), self.timeframes)

        try:
            while True:
                bar = await self.streamer.get()      # sadece tetikleyici
                sym, tf = bar["s"], bar["k"]["i"]

                for s in self.strategies:
                    if sym not in s["coins"] or tf != s["timeframe"]:
                        continue
                    inst = s["instance"]
                    sig  = inst.generate_signal(sym)  # BarStore'dan okuyor

                    if sig:
                        await self.pos_mgr.open_position(
                            sym,  1 if sig == "+1" else -1,
                            s["name"],
                            leverage   = s["effective_params"]["leverage"],
                            sl_pct     = s["effective_params"]["sl_pct"],
                            tp_pct     = s["effective_params"]["tp_pct"],
                            expire_sec = s["effective_params"]["expire_sec"],
                            timeframes = tf)
                    else:
                        await self.pos_mgr.update_all()
        finally:
            await self.streamer.stop()