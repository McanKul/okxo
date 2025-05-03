# live_engine.py - Asenkron canlı işlem motoru (çoklu strateji desteği).
import asyncio
import logging
import time

from binance import AsyncClient
from strategies import load_strategy
from live.position_manager import PositionManager
from live.streamer import Streamer

log = logging.getLogger("LiveEngine")

class LiveEngine:
    """
    Canlı modda asenkron veri akışlarını işleyen, çoklu strateji destekli işlem motoru.
    """
    def __init__(self, cfg, client: AsyncClient):
        self.cfg = cfg
        self.client = client

        # Tüm stratejileri yükle ve parametreleri sakla
        self.strategies = []  # her biri: {name, instance, timeframes, params}
        for strat_cfg in cfg.get_strategies():
            instance = load_strategy(strat_cfg)
            self.strategies.append({
                "name": strat_cfg["name"],
                "instance": instance,
                "timeframes": strat_cfg.get("timeframes", ["1h"]),
                "params": strat_cfg.get("effective_params", {})
            })

        # Pozisyon yöneticisi: base_capital ve max_concurrent global parametreler
        self.pos_mgr = PositionManager(
            client=self.client,
            base_capital=cfg.get_base_usdt_per_trade(),
            max_concurrent=cfg.get_max_concurrent()
        )

        self.symbols = []
        # Abone olunacak tüm zaman dilimleri (benzersiz)
        self.timeframes = sorted({tf for s in self.strategies for tf in s["timeframes"]})

    async def _resolve_symbols(self):
        
        coins = self.cfg.get_coins()
        
        if coins == "ALL_USDT":
            try:
                info = await self.client.futures_exchange_info()
                return [s['symbol'] for s in info['symbols']
                        if s['quoteAsset'] == "USDT" and s['status'] == "TRADING"]
            except Exception as e:
                log.error("Exchange info alınamadı: %s", e)
                return []
        return [sym.replace("/", "").upper() for sym in coins if isinstance(sym, str)]

    async def preload_history(self, limit=250):
        """
        Geçmiş mum verisini zaman dilimlerine göre önceden yükle.
        """
        for tf in self.timeframes:
            for sym in self.symbols:
                try:
                    klines = await self.client.futures_klines(symbol=sym, interval=tf, limit=limit)
                except Exception as e:
                    log.warning("%s için geçmiş verisi %s zaman diliminde alınamadı: %s", sym, tf, e)
                    continue
                for k in klines:
                    bar = {"s": sym, "k": {"t": k[0], "T": k[6],
                                              "o": k[1], "h": k[2],
                                              "l": k[3], "c": k[4],
                                              "v": k[5], "n": k[8],
                                              "x": True,
                                              "i": tf}}
                    # Her strateji, ilgili timeframe için bar güncellemesi
                    for strat in self.strategies:
                        if tf in strat["timeframes"]:
                            strat["instance"].update_bar(sym, bar)

    async def run(self):
        # Sembolleri çöz ve geçmiş veriyi yükle
        self.symbols = await self._resolve_symbols()
        if not self.symbols:
            log.error("İşlem yapılacak sembol bulunamadı. Canlı mod sonlandırılıyor.")
            return


        await self.preload_history(limit=self.cfg.get_history_limit())
        log.info("Canlı mod başladı: Semboller=%s, Zaman dilimleri=%s", self.symbols, self.timeframes)

        # Streaming başlat
        streamer = Streamer(self.client, self.symbols, self.timeframes)
        await streamer.start()
        log.info("Veri yayınlama başlatıldı.")

        try:
            while True:

                try:
                    bar = await streamer.get()
                except Exception as e:
                    log.error("Veri akışı alınamadı: %s", e)
                    break

                sym = bar.get("s")
                k = bar.get("k", {})
                tf = k.get("i")
                if not sym or not k or not tf:
                    continue

                # Strateji bazlı sinyal üretimi
                for strat in self.strategies:
                    if tf not in strat["timeframes"]:
                        continue
                    try:
                        strat["instance"].update_bar(sym, bar)
                        sig = strat["instance"].generate_signal(sym)
                    except Exception as e:
                        log.error("%s sinyal üretirken hata: %s", strat["name"], e)
                        continue

                    # Pozisyon açma/güncelleme
                    try:
                        if sig is None:
                            await self.pos_mgr.update_all()
                        elif sig > 0:
                            await self.pos_mgr.open_position(
                                symbol=sym,
                                side=1,
                                strategy_name=strat["name"],
                                timeframes=tf,
                                **{k: strat["params"][k] for k in ["leverage","sl_pct","tp_pct","expire_sec"]}
                            )
                            await self.pos_mgr.update_all()
                        elif sig < 0:
                            await self.pos_mgr.open_position(
                                symbol=sym,
                                side=-1,
                                strategy_name=strat["name"],
                                timeframes=tf,
                                **{k: strat["params"][k] for k in ["leverage","sl_pct","tp_pct","expire_sec"]}
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
            log.info("Canlı mod sonlandırıldı ve pozisyonlar kapatıldı.")
