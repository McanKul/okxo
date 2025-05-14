# tests/conftest.py
import pytest
import pandas as pd

from utils.interfaces import IBroker
from live.broker_binance import BinanceBroker
from live.position_manager import PositionManager

# tests/conftest.py
import pytest
from utils.config_loaders import ConfigLoader

@pytest.fixture(autouse=True)
def patch_config_loader(monkeypatch):
    # Her zaman "test" modu dönsün
    monkeypatch.setattr(ConfigLoader, "get_mode", lambda self: "test")


class DummyBroker(IBroker):
    def __init__(self):
        self.client = self

    async def get_mark_price(self, symbol: str) -> float:
        return 100.0

    async def market_order(self, symbol: str, side: str, qty: float):
        return True

    async def close_position(self, symbol: str):
        pass

    async def position_amt(self, symbol: str) -> float:
        return 0.0

    async def ensure_isolated_margin(self, symbol: str):
        pass

    async def place_stop_market(self, symbol, side, qty, stopPrice):
        pass

    async def place_take_profit(self, symbol, side, qty, price):
        pass

    async def set_leverage(self, symbol, leverage: int):
        pass

@pytest.fixture
def sample_df():
    # super_trend ve data_fetcher için ortak DataFrame
    return pd.DataFrame({
        "high":  [10, 11, 12, 13, 14],
        "low":   [5, 6, 7, 8,  9],
        "close": [7, 8, 9, 10, 11],
        "volume":[100,120,130,140,150]
    })

@pytest.fixture
def dummy_broker():
    return DummyBroker()

@pytest.fixture
def position_manager(dummy_broker):
    return PositionManager(dummy_broker, base_capital=100, max_concurrent=2)

@pytest.fixture(autouse=True)
def patch_config_loader(monkeypatch):
    # Her zaman "test" modu dönsün
    monkeypatch.setattr(ConfigLoader, "get_mode", lambda self: "test")
