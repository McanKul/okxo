# live_engine.py – SOLID refactor: yalnızca orkestrasyon
import asyncio
from utils.interfaces import IBroker, IStrategy
from strategies import load_strategy
from live.position_manager import PositionManager
from live.broker_binance import BinanceBroker
from live.streamer import Streamer
from utils.logger import setup_logger
log = setup_logger("LiveEngine")



class LiveEngine:
    """Canlı modda asenkron veri akışlarını işleten, çoklu strateji destekli motor."""
    def __init__(self, cfg, client):
        # Broker soyutlaması
        self.broker = BinanceBroker(client)  # ileride başka broker buraya
        self.cfg = cfg
        self.strategies: list[dict] = []
        for scfg in cfg.get_strategies():
            inst: IStrategy = load_strategy(scfg)
            self.strategies.append({**scfg, "instance": inst})
        self.timeframes = sorted({s["timeframe"] for s in self.strategies})
        self.pos_mgr = PositionManager(self.broker, base_capital=cfg.get_base_usdt_per_trade(),
                                       max_concurrent=cfg.get_max_concurrent())
        self.symbols = []

    # -------------------------------------------------
    async def run(self):
        # Sembolleri çözüp preload et
        self.symbols = await Streamer.resolve_symbols(self.broker.client, self.cfg.get_coins())
        await Streamer.preload_history(self.broker.client, self.symbols, self.timeframes,
                                       self.strategies, global_limit=self.cfg.get_history_limit())
        streamer = Streamer(self.broker.client, self.symbols, self.timeframes)
        await streamer.start()
        log.info("Canlı motor başladı: %s sembol | tf=%s", len(self.symbols), self.timeframes)
        try:
            while True:
                bar = await streamer.get()
                sym, k = bar["s"], bar["k"]
                tf = k["i"]
                for strat in self.strategies:
                    if tf != strat["timeframe"] or sym not in strat["coins"]:
                        continue
                    inst: IStrategy = strat["instance"]
                    inst.update_bar(sym, bar)
                    sig = inst.generate_signal(sym)
                    if sig:
                        await self.pos_mgr.open_position(sym, 1 if sig=="+1" else -1,
                                                          strat["name"], leverage=strat["effective_params"]["leverage"],
                                                          sl_pct=strat["effective_params"]["sl_pct"],
                                                          tp_pct=strat["effective_params"]["tp_pct"],
                                                          expire_sec=strat["effective_params"]["expire_sec"],
                                                          timeframes=tf)
                    else:
                        await self.pos_mgr.update_all()
        finally:
            
            await streamer.stop()
            
