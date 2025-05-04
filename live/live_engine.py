# live_engine.py – SOLID refactor: yalnızca orkestrasyon
import asyncio


from binance import AsyncClient
from strategies import load_strategy
from live.position_manager import PositionManager
from live.streamer import Streamer
from utils.logger import setup_logger
log = setup_logger("LiveEngine")



class LiveEngine:
    """Canlı modda asenkron veri akışlarını işleten, çoklu strateji destekli motor."""
    def __init__(self, cfg, client: AsyncClient):
        self.cfg = cfg
        self.client = client

        # Stratejileri hazırla
        self.strategies = []
        for scfg in cfg.get_strategies():
            self.strategies.append({
                "name": scfg["name"],
                "instance": load_strategy(scfg),
                "coins": scfg.get("coins", []),
                "timeframe": scfg.get("timeframe", ["1h"]),
                "params": scfg.get("effective_params", {})
            })

        self.timeframes = list(s["timeframe"] for s in self.strategies )
        self.pos_mgr = PositionManager(
            client=self.client,
            base_capital=cfg.get_base_usdt_per_trade(),
            max_concurrent=cfg.get_max_concurrent()
        )

        self.symbols = []          # run() içinde doldurulacak

    # -------------------------------------------------
    async def run(self):
        # 1) Sembolleri çöz
        self.symbols = await Streamer.resolve_symbols(self.client, self.cfg.get_coins())
        if not self.symbols:
            log.error("İşlem yapılacak sembol bulunamadı – canlı mod sonlandırıldı.")
            return

        # 2) Geçmiş veriyi yükle
        await Streamer.preload_history(
            client=self.client,
            symbols=self.symbols,
            intervals=self.timeframes,
            strategies=self.strategies,
            global_limit=self.cfg.get_history_limit()
        )

        # 3) Yayını başlat
        streamer = Streamer(self.client, self.symbols, self.timeframes)
        await streamer.start()
        log.info("LiveEngine başladı: %s sembol, %s tf", self.symbols, self.timeframes)

        try:
            while True:
                
                try:
                    bar = await streamer.get()
                except Exception as e:
                    log.error("Veri akışı alınamadı: %s", e)
                    break

                sym, k = bar.get("s"), bar.get("k", {})
                tf = k.get("i")
                if not sym or not tf:
                    continue

                for strat in self.strategies:
                    if tf not in strat["timeframe"]:
                        continue
                    if sym not in strat["coins"] and "ALL_USDT" not in strat["coins"]:
                        continue

                    try:
                        strat["instance"].update_bar(sym, bar)
                        sig = strat["instance"].generate_signal(sym)
                    except Exception as e:
                        log.error("%s sinyal üretirken hata: %s", strat["name"], e)
                        continue
                    
                    try:
                        if sig is None:
                            await self.pos_mgr.update_all()
                        else:
                            await self.pos_mgr.open_position(
                                symbol=sym,
                                side=1 if sig > 0 else -1,
                                strategy_name=strat["name"],
                                timeframes=tf,
                                **{k: strat["params"][k] for k in ["leverage", "sl_pct", "tp_pct", "expire_sec"]}
                            )
                            await self.pos_mgr.update_all()
                    except Exception as e:
                        log.error("%s pozisyon yönetimi hatası: %s", strat["name"], e)

        except asyncio.CancelledError:
            log.info("LiveEngine iptal edildi.")
        except Exception as e:
            log.error("LiveEngine genel hatası: %s", e)
        finally:
            
            await streamer.stop()
            await self.pos_mgr.force_close_all()
            log.info("Canlı mod sonlandırıldı – tüm pozisyonlar kapatıldı.")
