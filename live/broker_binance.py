# live/broker_binance.py
from binance.client import Client
from binance.enums import *
import os, logging, math

class BinanceBroker:
    """En yalın emir / bakiye sarmalayıcı."""

    def __init__(self, api_key: str|None = None, api_secret: str|None = None):
        self.client = Client(
            api_key or os.getenv("API_KEY"),
            api_secret or os.getenv("API_SECRET"),
            {"timeout": 50}
        )

    # ------------ basic helpers -----------------
    def balance(self, asset="USDT") -> float:
        for bal in self.client.futures_account_balance():
            if bal["asset"] == asset:
                return float(bal["balance"])
        return 0.0

    def position_amt(self, symbol) -> float:
        p = next((x for x in self.client.futures_position_information(symbol=symbol)
                  if float(x["positionAmt"]) != 0), None)
        return float(p["positionAmt"]) if p else 0.0

    # ------------ trading wrappers --------------
    def market_order(self, symbol, side, qty):
        return self.client.futures_create_order(
            symbol     = symbol,
            side       = side,
            type       = FUTURE_ORDER_TYPE_MARKET,
            quantity   = qty
        )

    def close_position(self, symbol):
        amt = self.position_amt(symbol)
        if amt == 0:
            return
        side = SIDE_SELL if amt > 0 else SIDE_BUY
        self.market_order(symbol, side, abs(amt))
