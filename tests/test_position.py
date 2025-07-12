# tests/test_position.py
import pytest
from mocks.mock_strategy import MockStrategy
from live.position_manager import PositionManager
from utils.interfaces import IBroker

@pytest.mark.asyncio
async def test_position_opening():
    class DummyBroker(IBroker):
        async def market_order(self, s, side, qty): return True
        async def close_position(self, s): pass
        async def position_amt(self, s): return 0.0

    strategy = MockStrategy(signal="+1")
    pos_mgr = PositionManager(DummyBroker(), base_capital=100, max_concurrent=5)
    result = await pos_mgr.open_position("BTCUSDT", 1, strategy, "1m", 3, 5, 300)
    assert result is True
