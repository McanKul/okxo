"""
position_manager.py - Manage leveraged futures positions asynchronously.
"""
import math
import time
import logging
from binance.exceptions import BinanceAPIException
from binance.enums import *
from binance import AsyncClient  # for type hinting

log = logging.getLogger("PositionManager")

class Position:
    """
    Represents a single leveraged perpetual futures position.
    """
    def __init__(self, client: AsyncClient, symbol: str, side: str,
                 qty: float, entry_price: float,
                 sl_price: float = None, tp_price: float = None,
                 opened_ts: float = None):
        self.client = client
        self.symbol = symbol
        self.side = side  # SIDE_BUY or SIDE_SELL
        self.qty = qty
        self.entry = entry_price
        self.sl = sl_price
        self.tp = tp_price
        self.open_ts = opened_ts or time.time()
        self.closed = False
        self.exit_ts = None
        self.exit = None
        self.exit_type = None  # "SL", "TP", or "MANUAL"

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
            log.error("Market close error %s — %s", self.symbol, e)
            raise

    async def check_exit(self, now: float, max_holding_sec: int = None) -> bool:
        """
        Check if SL/TP or max holding time triggered for this position.
        Returns True if position was closed.
        """
        if self.closed:
            return True

        price = await self._current_price()

        # Take Profit
        if self.tp and (
            (self.side == SIDE_BUY  and price >= self.tp) or
            (self.side == SIDE_SELL and price <= self.tp)
        ):
            await self._close_market()
            self.closed = True
            self.exit_type = "TP"
        # Stop Loss
        elif self.sl and (
            (self.side == SIDE_BUY  and price <= self.sl) or
            (self.side == SIDE_SELL and price >= self.sl)
        ):
            await self._close_market()
            self.closed = True
            self.exit_type = "SL"
        # Max holding time exceeded
        elif max_holding_sec and (now - self.open_ts) >= max_holding_sec:
            await self._close_market()
            self.closed = True
            self.exit_type = "MANUAL"

        if self.closed:
            self.exit_ts = now
            self.exit = price
            log.info("%s %s closed @ %.8f (%s)",
                     self.symbol, self.side, price, self.exit_type)
            try:
                await self.client.futures_cancel_all_open_orders(symbol=self.symbol)
            except BinanceAPIException:
                pass
        return self.closed

class PositionManager:
    """
    Manage multiple futures positions with risk settings.
    """
    def __init__(self,
                 client: AsyncClient,
                 base_capital: float = 10.0,
                 leverage: int = 1,
                 max_concurrent: int = 3,
                 default_sl_pct: float = 3.0,
                 default_tp_pct: float = 6.0,
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
        info = await self.client.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        lot = float(f['stepSize'])
                        factor = 1 / lot
                        return math.floor(qty_f * factor) / factor
        return 0.0

    async def open_position(self,
                            symbol: str,
                            side: int,
                            sl_pct: float = None,
                            tp_pct: float = None) -> bool:
        """
        Open a new position:
        side: +1 for BUY, -1 for SELL.
        sl_pct / tp_pct: stop loss / take profit percentages (pre-leverage).
        """
        if symbol in self.open_positions:
            return False
        if len(self.open_positions) >= self.max_open:
            return False

        mark = float((await self.client.futures_mark_price(symbol=symbol))["markPrice"])
        notional = self.base_cap * self.leverage
        raw_qty = notional / mark
        qty = await self._round_qty(symbol, raw_qty)
        if qty <= 0:
            return False

        side_str = SIDE_BUY if side == 1 else SIDE_SELL
        opp_str = SIDE_SELL if side_str == SIDE_BUY else SIDE_BUY

        # Set isolated margin and leverage
        try:
            await self.client.futures_change_margin_type(symbol=symbol, marginType="ISOLATED")
        except BinanceAPIException as e:
            if e.code != -4046:
                log.error("%s margin type err %s", symbol, e)
                return False
        try:
            await self.client.futures_change_leverage(symbol=symbol, leverage=self.leverage)
        except BinanceAPIException as e:
            log.error("%s leverage err %s", symbol, e)
            return False

        # Create market order to open position
        try:
            await self.client.futures_create_order(
                symbol=symbol,
                side=side_str,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=f"{qty:.8f}"
            )
        except BinanceAPIException as e:
            log.error("%s market order err %s", symbol, e)
            return False

        # Calculate SL and TP prices
        sl_pct = self.def_sl_pct if sl_pct is None else sl_pct
        tp_pct = self.def_tp_pct if tp_pct is None else tp_pct
        price_sl = mark * (1 - sl_pct/100) if side_str == SIDE_BUY else mark * (1 + sl_pct/100)
        price_tp = mark * (1 + tp_pct/100) if side_str == SIDE_BUY else mark * (1 - tp_pct/100)

        # Create stop-loss and take-profit orders
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
            log.warning("%s SL/TP order error %s", symbol, e)

        pos = Position(self.client, symbol, side_str, qty, mark, price_sl, price_tp, time.time())
        self.open_positions[symbol] = pos
        log.info("%s %s OPEN qty=%s SL=%.8f TP=%.8f",
                 symbol, side_str, qty, price_sl, price_tp)
        return True

    async def open_long(self, symbol: str, sl_pct: float = None, tp_pct: float = None) -> bool:
        return await self.open_position(symbol, 1, sl_pct=sl_pct, tp_pct=tp_pct)

    async def open_short(self, symbol: str, sl_pct: float = None, tp_pct: float = None) -> bool:
        return await self.open_position(symbol, -1, sl_pct=sl_pct, tp_pct=tp_pct)

    async def update_all(self):
        """
        Check and close positions that hit SL/TP or expired.
        """
        now = time.time()
        to_remove = []
        for sym, pos in list(self.open_positions.items()):
            closed = await pos.check_exit(now, self.max_hold_s)
            if closed:
                self.history.append(pos)
                to_remove.append(sym)
        for sym in to_remove:
            del self.open_positions[sym]

    async def force_close_all(self):
        """
        Force close all open positions (e.g., on shutdown).
        """
        for sym, pos in list(self.open_positions.items()):
            try:
                await pos._close_market()
            except BinanceAPIException:
                pass
            pos.closed = True
            pos.exit_type = "MANUAL"
            self.history.append(pos)
            del self.open_positions[sym]
        log.info("All positions closed (manual)")
