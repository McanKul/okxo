# utils/model_registry.py
import pickle, pathlib
from functools import lru_cache
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent / "models"

@lru_cache(maxsize=None)
def load(strategy: str, timeframe: str, side: str) -> Any:
    path = ROOT / strategy / f"{timeframe}_{side}.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)
