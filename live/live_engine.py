# live_engine.py - Asenkron canlı işlem motoru.
import asyncio
import logging
import time

from binance import AsyncClient
from strategies import load_strategy
from live.position_manager import PositionManager
from live.streamer import Streamer


class LiveEngine:
    """
    Canlı modda asenkron veri akışlarını işleyen işlem motoru.
    """
    def __init__(self,cfg,client: AsyncClient):
        self.cfg = cfg;
        self.client = client
        self.tf = cfg.get_timeframes()[0]  # todo sadece ilk time frame alıyoruz şimdilik
        # Stratejiyi yükle (ilk strateji kullanılıyor)
        self.strategy = load_strategy(cfg.get_strategies()[0]) #todo sadece ilk stratejiyi alıyoruz şimdilik
        # Pozisyon yöneticisini oluştur
        self.pos_mgr = PositionManager(
            client=self.client,
            base_capital=cfg.get_base_usdt_per_trade(),
            leverage=cfg.get_leverage(),
            max_concurrent=cfg.get_max_concurrent(),
            default_sl_pct=cfg.get_sl_pct(),
            default_tp_pct=cfg.get_tp_pct(),
            max_holding_seconds=cfg.get_expire_sec()
        )
        self.symbols = []

    async def _resolve_symbols(self):
        """
        Sembol listesini belirle: config'teki listeden veya ALL_USDT kullanılarak.
        """
        coins = self.cfg.get_coins()
        
        if coins == "ALL_USDT":
            try:
                info = await self.client.futures_exchange_info()
                return [s['symbol'] for s in info['symbols']
                        if s['quoteAsset'] == "USDT" and s['status'] == "TRADING"]
            except Exception as e:
                logging.error("Exchange info alınamadı: %s", e)
                return []
        symbols = []
        for sym in coins:
            if isinstance(sym, str):
                symbols.append(sym.replace("/", "").upper())
        return symbols

    async def preload_history(self, limit=250):
        """
        Geçmiş mum verisini önceden yükle (opsiyonel).
        """
        for sym in self.symbols:
            try:
                klines = await self.client.futures_klines(symbol=sym, interval=self.tf, limit=limit)
            except Exception as e:
                logging.warning(f"{sym} için geçmiş verisi alınamadı: {e}")
                continue
            for k in klines:
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
        # Sembolleri çöz
        resolved = await self._resolve_symbols()
        if not resolved:
            logging.error("İşlem yapılacak sembol bulunamadı. Canlı mod sonlandırılıyor.")
            return
        self.symbols = resolved

        # Geçmiş veri ön yüklemesi
        history_limit = self.cfg.get_history_limit()
        await self.preload_history(limit=history_limit)
        logging.info("Canlı mod başladı: Semboller=%s, Zaman dilimi=%s", self.symbols, self.tf)

        # Streaming başlat
        streamer = Streamer(self.client, self.symbols, self.tf)
        await streamer.start()
        logging.info("Veri yayınlama başlatıldı.")

        try:
            while True:
                # Kuyruktan gelen mum verisini al
                try:
                    bar = await streamer.get()
                except Exception as e:
                    logging.error("Veri akışı alınamadı: %s", e)
                    break

                sym = bar.get("s")
                k = bar.get("k", {})
                if not sym or not k:
                    continue

                # Stratejiyi güncelle ve sinyal üret
                self.strategy.update_bar(sym, bar)
                sig = None
                try:
                    sig = self.strategy.generate_signal(sym)
                except Exception as e:
                    logging.error("Sinyal üretirken hata: %s", e)

                # Pozisyon yönetimi
                try:
                    if sig is None:
                        # Sinyal yok: mevcut pozisyonları güncelle
                        await self.pos_mgr.update_all()
                        continue
                    if sig > 0:
                        await self.pos_mgr.open_long(sym)
                    elif sig < 0:
                        await self.pos_mgr.open_short(sym)
                    # Açılan pozisyon sonrası veya sinyal sonrası pozisyon güncellemesi
                    await self.pos_mgr.update_all()
                except Exception as e:
                    logging.error("Pozisyon açma/güncelleme hatası: %s", e)

        except asyncio.CancelledError:
            logging.info("LiveEngine iptal edildi.")
        except Exception as e:
            logging.error("LiveEngine genel hatası: %s", e)
        finally:
            # Streaming durdur ve pozisyonları kapat
            await streamer.stop()
            await self.pos_mgr.force_close_all()
            logging.info("Canlı mod sonlandırıldı ve pozisyonlar kapatıldı.")
