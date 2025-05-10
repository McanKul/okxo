"""
Strateji paketi – yeni *.py dosyası eklediğinde
otomatik tanınması için küçük yardımcılar içerir.
"""

import importlib
from pathlib import Path

# project_root/strategies klasöründeki tüm .py dosyaları
_STRAT_DIR = Path(__file__).resolve().parent
_IGNORE    = {"__init__.py", "__pycache__"}

def _discover():
    """Klasördeki tüm strateji modüllerini döndürür  {name: module_object}"""
    mods = {}
    for f in _STRAT_DIR.glob("*.py"):
        if f.name in _IGNORE:
            continue
        name = f.stem
        mods[name] = importlib.import_module(f"strategies.{name}")
    return mods

# Keşfet ve modül sözlüğünü önbelleğe al
_STRAT_MODULES = _discover()

# ────────────────────────────────────────────────────────────────────────────
def load_strategy(cfg_entry: dict, *, bar_store, symbol: str, timeframe: str):
    """
    cfg_entry: ConfigLoader.get_strategies() çıktısındaki bir eleman
        {
          "name": "super_trend",
          "params": {...},
          "effective_params": {...},
          ...
        }

    bar_store : merkezi BarStore nesnesi
    symbol    : "BTCUSDT" vb.
    timeframe : "1m", "15m" vb.

    Dönüş  → Strategy sınıfından örnek (IStrategy)
    """
    name       = cfg_entry["name"]
    tech_param = cfg_entry.get("params", {})
    runtime    = cfg_entry.get("effective_params", {})

    if name not in _STRAT_MODULES:
        raise ValueError(f"Strateji bulunamadı: {name}")

    mod = _STRAT_MODULES[name]
    
    if not hasattr(mod, "Strategy"):
        raise AttributeError(f"{name}.py içinde Strategy sınıfı tanımlı değil.")

    # Teknik + runtime parametrelerini birleştir
    kwargs = {**runtime, **tech_param,
              "bar_store": bar_store,
              "symbol":    symbol,
              "timeframe": timeframe}

    return mod.Strategy(**kwargs)
