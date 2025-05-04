# live/broker_binance.py
from binance.client import Client
from binance.enums import *
from utils.logger import setup_logger

class BinanceBroker:
    """En yalın emir / bakiye sarmalayıcı."""

    def __init__(self, client):
        self.client = client
        self.log = setup_logger("BinanceBroker")

    # ------------ basic helpers -----------------
    async def balance(self, asset="USDT") -> float:
        for bal in await self.client.futures_account_balance():
            if bal["asset"] == asset:
                return float(bal["balance"])
        return 0.0

    async def position_amt(self, symbol) -> float:
        p = next((x for x in await self.client.futures_position_information(symbol=symbol)
                  if float(x["positionAmt"]) != 0), None)
        return float(p["positionAmt"]) if p else 0.0

    # ------------ trading wrappers --------------
    async def market_order(self, symbol, side, qty):
        return await self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=qty
        )

    async def close_position(self, symbol):
        amt = await self.position_amt(symbol)
        if amt == 0:
            return
        side = SIDE_SELL if amt > 0 else SIDE_BUY
        await self.market_order(symbol, side, abs(amt))
