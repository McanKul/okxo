# tests/mocks/mock_strategy.py
from utils.interfaces import IStrategy
import pandas as pd

class MockStrategy(IStrategy):
    def __init__(self, signal=None):
        self._signal = signal

    def update_bar(self, symbol: str, bar: dict):
        pass

    def generate_signal(self, symbol: str):
        return self._signal

    @staticmethod
    def generate_signals(df: pd.DataFrame) -> pd.Series:
        return pd.Series([None] * len(df))

    def sl_pct(self) -> float:
        return 3.0

