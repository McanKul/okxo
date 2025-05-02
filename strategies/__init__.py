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
    cfg_entry: config_loader tarafından sağlanan yapı
        {
          name: rsi_threshold_strategy,
          params: { ... },
          timeframes: [ ... ],
          effective_params: { sl_pct, tp_pct, leverage, ... }
        }

    Dönüş → Strategy sınıfı (örnek)
    """
    name = cfg_entry["name"]
    params = cfg_entry.get("params", {})
    runtime = cfg_entry.get("effective_params", {})

    if name not in _STRAT_MODULES:
        raise ValueError(f"Strateji bulunamadı: {name}")

    mod = _STRAT_MODULES[name]


    if not hasattr(mod, "Strategy"):
        raise AttributeError(f"{name}.py içinde Strategy sınıfı tanımlı değil.")

    # param + effective_param birleşimi → kwargs olarak Strategy'e geç
    merged_params = {**runtime, **params}
    return mod.Strategy(**merged_params)
