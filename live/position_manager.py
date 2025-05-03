# position_manager.py - Asenkron vadeli işlem pozisyonlarını yönetir.
import math
import time
import logging
from binance.exceptions import BinanceAPIException
from binance.enums import *
from binance import AsyncClient  # sadece tip bildirimi için

log = logging.getLogger("PositionManager")

class Position:
    
    def __init__(self, client: AsyncClient, symbol: str, side: str,
                 qty: float, entry_price: float,
                 sl_price: float = None, tp_price: float = None,
                 opened_ts: float = None,
                 tick: int = None, strategy: str = None,
                 expire_sec: int = 3600,
                 timeframes: str = "1h"):
        self.client = client
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.entry = entry_price
        self.sl = sl_price
        self.tp = tp_price
        self.open_ts = opened_ts or time.time()
        self.closed = False
        self.exit_ts = None
        self.exit = None
        self.exit_type = None
        self.expire_sec = expire_sec
        self.tick = tick
        self.timeframes = timeframes
        self.strategy = strategy

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
                quantity=f"{self.qty:.{abs(int(math.log10(self.tick)))}f}"
            )
        except BinanceAPIException as e:
            log.error("Piyasa emriyle kapama hatası %s: %s", self.symbol, e)
            raise

    async def check_exit(self, now: float, max_holding_sec: int = None) -> bool:
        
        if self.closed:
            return True

        price = await self._current_price()

        
        if self.tp and (
            (self.side == SIDE_BUY and price >= self.tp) or
            (self.side == SIDE_SELL and price <= self.tp)
        ):
            await self._close_market()
            self.closed = True
            self.exit_type = "TP"
        
        elif self.sl and (
            (self.side == SIDE_BUY and price <= self.sl) or
            (self.side == SIDE_SELL and price >= self.sl)
        ):
            await self._close_market()
            self.closed = True
            self.exit_type = "SL"
        
        elif max_holding_sec and (now - self.open_ts) >= max_holding_sec:
            await self._close_market()
            self.closed = True
            self.exit_type = "MANUAL"

        if self.closed:
            self.exit_ts = now
            self.exit = price
            log.info("%s [%s] pozisyon kapandı @ %.8f (%s)",
                     self.symbol, self.strategy or self.side, price, self.exit_type)
            try:
                
                await self.client.futures_cancel_all_open_orders(symbol=self.symbol)
            except BinanceAPIException:
                log.info("%s emirler iptal edilirken bir sıkıntı oluştu", self.symbol)

        return self.closed


class PositionManager:
    
    def __init__(self,
                 client: AsyncClient,
                 base_capital: float = 10.0,
                 max_concurrent: int = 1):
        self.client = client
        self.base_cap = base_capital
        
        self.max_open = max_concurrent
        self.open_positions = {}  # key: (symbol, strategy)
        self.history = []

    def round_price(self, raw, tick, up=False):
        
        factor = 1 / tick
        return (math.ceil if up else math.floor)(raw * factor) / factor

    
    async def _symbol_filters(self, symbol: str, qty_f: float) -> tuple[float, float]:
        try:
            info = await self.client.futures_exchange_info()
            step = tick = None
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            lot = float(f['stepSize'])
                            factor = 1 / lot
                            step = math.floor(qty_f * factor) / factor
                        if f['filterType'] == 'PRICE_FILTER':
                            tick = float(f['tickSize'])
                    if tick and step:
                        return step, tick
        
        except Exception as e:
            log.error("LOT_SIZE ve PRICE_FILTER alınamadı %s: %s", symbol, e)
        return 0.0, 0.0

    async def open_position(self,
                            symbol: str,
                            side: int,
                            strategy_name: str,
                            leverage: int,
                            sl_pct: float,
                            tp_pct: float,
                            expire_sec: int,
                            timeframes: str) -> bool:
        key = (symbol, strategy_name)
        if key in self.open_positions:
            return False
        if len(self.open_positions) >= self.max_open:
            return False

        mark_price = float((await self.client.futures_mark_price(symbol=symbol))["markPrice"])
        notional = self.base_cap * leverage
        raw_qty = notional / mark_price
        qty, tick = await self._symbol_filters(symbol, raw_qty)
        if qty <= 0:
            return False

        side_str = SIDE_BUY if side == 1 else SIDE_SELL
        opp_str = SIDE_SELL if side_str == SIDE_BUY else SIDE_BUY

        
        try:
            await self.client.futures_change_margin_type(symbol=symbol, marginType="ISOLATED")
        except BinanceAPIException as e:
        
            if e.code != -4046:
                log.error("%s marj tipi ayarlanamadı: %s", symbol, e)
                return False
        try:
            await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
        except BinanceAPIException as e:
            log.error("%s kaldıraç ayarlanamadı: %s", symbol, e)
            return False

        raw_sl = mark_price * (1 - sl_pct/leverage / 100) if side_str == SIDE_BUY else mark_price * (1 + sl_pct/leverage / 100)
        raw_tp = mark_price * (1 + tp_pct/leverage / 100) if side_str == SIDE_BUY else mark_price * (1 - tp_pct/leverage / 100)

        price_sl = self.round_price(raw_sl, tick, up=(side_str == SIDE_SELL))
        price_tp = self.round_price(raw_tp, tick, up=(side_str == SIDE_BUY))

        
        try:
            await self.client.futures_create_order(
                symbol=symbol,
                side=side_str,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=f"{qty:.{abs(int(math.log10(tick)))}f}"
            )
        except BinanceAPIException as e:
            log.error("%s piyasa emri hatası: %s", symbol, e)
            return False

        
        try:
            await self.client.futures_create_order(
                symbol=symbol,
                side=opp_str,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=f"{price_sl:.{abs(int(math.log10(tick)))}f}",
                closePosition=True
            )
        except BinanceAPIException as e:
            log.warning("%s SL emri hatası: %s", symbol, e)
        try:
            await self.client.futures_create_order(
                symbol=symbol,
                side=opp_str,
                type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=f"{price_tp:.{abs(int(math.log10(tick)))}f}",
                closePosition=True
            )
        except BinanceAPIException as e:
            log.warning("%s TP emri hatası: %s", symbol, e)

        pos = Position(self.client, symbol, side_str, qty, mark_price, price_sl, price_tp, time.time(), tick, strategy=strategy_name, expire_sec=expire_sec, timeframes=timeframes)
        self.open_positions[key] = pos
        log.info("%s [%s] [%s] pozisyon açıldı: miktar=%.4f, SL=%.8f, TP=%.8f",
                 symbol, strategy_name,timeframes, qty, price_sl, price_tp)
        return True



    
    async def update_all(self):
        
        now = time.time()
        to_remove = []
        for key, pos in list(self.open_positions.items()):
            try:
                closed = await pos.check_exit(now, max_holding_sec=pos.expire_sec)
            except Exception as e:
                log.error("Pozisyon kontrol hatası %s: %s", key, e)
                continue
            if closed:
                self.history.append(pos)
                to_remove.append(key)
        for key in to_remove:
            del self.open_positions[key]

    async def force_close_all(self):
        for key, pos in list(self.open_positions.items()):
            try:
                await pos._close_market()
            except Exception:
                pass
            pos.closed = True
            pos.exit_type = "MANUAL"
            self.history.append(pos)
            del self.open_positions[key]
        log.info("Tüm pozisyonlar manuel olarak kapatıldı.")
