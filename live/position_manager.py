# position_manager.py - Asenkron vadeli işlem pozisyonlarını yönetir.
import math
import time
import logging
from binance.exceptions import BinanceAPIException
from binance.enums import *
from binance import AsyncClient  # sadece tip bildirimi için

log = logging.getLogger("PositionManager")

class Position:
    """
    Tek bir vadeli işlem pozisyonunu temsil eder.
    """
    def __init__(self, client: AsyncClient, symbol: str, side: str,
                 qty: float, entry_price: float,
                 sl_price: float = None, tp_price: float = None,
                 opened_ts: float = None):
        self.client = client
        self.symbol = symbol
        self.side = side  # SIDE_BUY veya SIDE_SELL
        self.qty = qty
        self.entry = entry_price
        self.sl = sl_price
        self.tp = tp_price
        self.open_ts = opened_ts or time.time()
        self.closed = False
        self.exit_ts = None
        self.exit = None
        self.exit_type = None  # "SL", "TP" veya "MANUAL"

    async def _current_price(self) -> float:
        res = await self.client.futures_mark_price(symbol=self.symbol)
        return float(res["markPrice"])

    async def _close_market(self):
        opp = SIDE_SELL if self.side == SIDE_BUY else SIDE_BUY
        try:
            await self.client.futures_create_order(
                symbol=self.symbol,
                side=opp,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=f"{self.qty:.8f}"
            )
        except BinanceAPIException as e:
            log.error("Piyasa emriyle kapama hatası %s: %s", self.symbol, e)
            raise

    async def check_exit(self, now: float, max_holding_sec: int = None) -> bool:
        """
        SL/TP veya maksimum bekleme süresi tetiklenip tetiklenmediğini kontrol eder.
        Pozisyon kapatıldıysa True döner.
        """
        if self.closed:
            return True

        price = await self._current_price()

        # Take Profit kontrolü
        if self.tp and (
            (self.side == SIDE_BUY and price >= self.tp) or
            (self.side == SIDE_SELL and price <= self.tp)
        ):
            await self._close_market()
            self.closed = True
            self.exit_type = "TP"
        # Stop Loss kontrolü
        elif self.sl and (
            (self.side == SIDE_BUY and price <= self.sl) or
            (self.side == SIDE_SELL and price >= self.sl)
        ):
            await self._close_market()
            self.closed = True
            self.exit_type = "SL"
        # Maksimum bekleme süresi kontrolü
        elif max_holding_sec and (now - self.open_ts) >= max_holding_sec:
            await self._close_market()
            self.closed = True
            self.exit_type = "MANUAL"

        if self.closed:
            self.exit_ts = now
            self.exit = price
            log.info("%s %s pozisyon kapandı @ %.8f (%s)",
                     self.symbol, self.side, price, self.exit_type)
            try:
                # Açık tüm siparişleri iptal et
                await self.client.futures_cancel_all_open_orders(symbol=self.symbol)
            except BinanceAPIException:
                pass

        return self.closed


class PositionManager:
    """
    Birden fazla vadeli işlem pozisyonunu risk ayarlarıyla yöneten sınıf.
    """
    def __init__(self,
                 client: AsyncClient,
                 base_capital: float = 0.0,
                 leverage: int = 1,
                 max_concurrent: int = 1,
                 default_sl_pct: float = 0.0,
                 default_tp_pct: float = 0.0,
                 max_holding_seconds: int = 300):
        self.client = client
        self.base_cap = base_capital
        self.leverage = leverage
        self.max_open = max_concurrent
        self.def_sl_pct = default_sl_pct
        self.def_tp_pct = default_tp_pct
        self.max_hold_s = max_holding_seconds

        self.open_positions = {}
        self.history = []

    async def _round_qty(self, symbol: str, qty_f: float) -> float:
        try:
            info = await self.client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            lot = float(f['stepSize'])
                            factor = 1 / lot
                            return math.floor(qty_f * factor) / factor
        except Exception as e:
            log.error("LOT_SIZE filtresi alınamadı %s: %s", symbol, e)
        return 0.0

    async def open_position(self,
                            symbol: str,
                            side: int,
                            sl_pct: float = None,
                            tp_pct: float = None) -> bool:
        """
        Yeni pozisyon açar.
        side: +1 (BUY), -1 (SELL).
        sl_pct / tp_pct: Stop loss / take profit yüzdeleri (kaldıraç öncesi).
        """
        if symbol in self.open_positions:
            return False
        if len(self.open_positions) >= self.max_open:
            return False

        mark_price = float((await self.client.futures_mark_price(symbol=symbol))["markPrice"])
        notional = self.base_cap * self.leverage
        raw_qty = notional / mark_price
        qty = await self._round_qty(symbol, raw_qty)
        if qty <= 0:
            return False

        side_str = SIDE_BUY if side == 1 else SIDE_SELL
        opp_str = SIDE_SELL if side_str == SIDE_BUY else SIDE_BUY

        # İzole marj ve kaldıraç ayarla
        try:
            await self.client.futures_change_margin_type(symbol=symbol, marginType="ISOLATED")
        except BinanceAPIException as e:
            # Kaldıraç zaten ayarlı olabilir
            if e.code != -4046:
                log.error("%s marj tipi ayarlanamadı: %s", symbol, e)
                return False
        try:
            await self.client.futures_change_leverage(symbol=symbol, leverage=self.leverage)
        except BinanceAPIException as e:
            log.error("%s kaldıraç ayarlanamadı: %s", symbol, e)
            return False

        # Pozisyon açmak için piyasa emri
        try:
            await self.client.futures_create_order(
                symbol=symbol,
                side=side_str,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=f"{qty:.8f}"
            )
        except BinanceAPIException as e:
            log.error("%s piyasa emri hatası: %s", symbol, e)
            return False

        # SL ve TP yüzdelerini belirle (parametre veya varsayılan)
        sl_pct = self.def_sl_pct if sl_pct is None else sl_pct
        tp_pct = self.def_tp_pct if tp_pct is None else tp_pct
        price_sl = mark_price * (1 - sl_pct/100) if side_str == SIDE_BUY else mark_price * (1 + sl_pct/100)
        price_tp = mark_price * (1 + tp_pct/100) if side_str == SIDE_BUY else mark_price * (1 - tp_pct/100)

        # Stop-loss ve take-profit emirleri oluştur
        try:
            await self.client.futures_create_order(
                symbol=symbol,
                side=opp_str,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=f"{price_sl:.8f}",
                closePosition=True
            )
            await self.client.futures_create_order(
                symbol=symbol,
                side=opp_str,
                type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=f"{price_tp:.8f}",
                closePosition=True
            )
        except BinanceAPIException as e:
            log.warning("%s SL/TP emri hatası: %s", symbol, e)

        pos = Position(self.client, symbol, side_str, qty, mark_price, price_sl, price_tp, time.time())
        self.open_positions[symbol] = pos
        log.info("%s %s pozisyon açıldı: miktar=%s, SL=%.8f, TP=%.8f",
                 symbol, side_str, qty, price_sl, price_tp)
        return True

    async def open_long(self, symbol: str, sl_pct: float = None, tp_pct: float = None) -> bool:
        return await self.open_position(symbol, 1, sl_pct=sl_pct, tp_pct=tp_pct)

    async def open_short(self, symbol: str, sl_pct: float = None, tp_pct: float = None) -> bool:
        return await self.open_position(symbol, -1, sl_pct=sl_pct, tp_pct=tp_pct)

    async def update_all(self):
        """
        SL/TP veya süre sonu tetiklenen pozisyonları kontrol et ve kapat.
        """
        now = time.time()
        to_remove = []
        for sym, pos in list(self.open_positions.items()):
            try:
                closed = await pos.check_exit(now, self.max_hold_s)
            except Exception as e:
                log.error("Pozisyon kontrol hatası %s: %s", sym, e)
                continue
            if closed:
                self.history.append(pos)
                to_remove.append(sym)
        for sym in to_remove:
            del self.open_positions[sym]

    async def force_close_all(self):
        """
        Tüm açık pozisyonları kapat (örn. kapanışta).
        """
        for sym, pos in list(self.open_positions.items()):
            try:
                await pos._close_market()
            except Exception:
                pass
            pos.closed = True
            pos.exit_type = "MANUAL"
            self.history.append(pos)
            del self.open_positions[sym]
        log.info("Tüm pozisyonlar manuel olarak kapatıldı.")
