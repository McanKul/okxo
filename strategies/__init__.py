# strategies/__init__.py
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
        mod  = importlib.import_module(f"strategies.{name}")
        mods[name] = mod
    return mods

# Keşfet ve modül sözlüğünü önbelleğe al
_STRAT_MODULES = _discover()

def load_strategy(cfg_entry: dict):
    """
    cfg_entry:  config.yaml içindeki
        { name: rsi_macd_triple, params: { … } }

    Dönüş → StrategyWrapper sınıfı
      - .update_bar(symbol, bar_json)
      - .generate_signal(symbol)   →  +1 BUY, -1 SELL, 0/None
      - .sl_pct()                 →  stop-loss yüzdesi (pnl hesabı için)
    """
    name   = cfg_entry["name"]
    params = cfg_entry.get("params", {})

    if name not in _STRAT_MODULES:
        raise ValueError(f"Strateji bulunamadı: {name}")

    mod = _STRAT_MODULES[name]

    # Modül içinde 'Strategy' sınıfı bekliyoruz
    if not hasattr(mod, "Strategy"):
        raise AttributeError(
            f"{name}.py içinde Strategy sınıfı tanımlı değil."
        )

    return mod.Strategy(**params)
