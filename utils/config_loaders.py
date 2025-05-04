from __future__ import annotations
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

__all__ = ["ConfigLoader"]

class ConfigLoader:
    """Read .env and YAML files, exposing helpers for commonly-used fields."""

    def __init__(
        self,
        config_path: str | Path = "config/config.yaml",
        env_path: str | Path = "config/.env",
    ) -> None:
        # ––– Load .env ––––––––––––––––––––––––––––––––––––––––––––––––––––––––
        env_path = Path(env_path) if env_path is not None else Path(__file__).resolve().parent.parent / ".env"
        if not env_path.exists():
            raise FileNotFoundError(f".env file not found at {env_path}")
        load_dotenv(env_path)

        # Expose env keys
        self.API_KEY: str | None = os.getenv("API_KEY")
        self.API_SECRET: str | None = os.getenv("API_SECRET")

        # ––– Load YAML ––––––––––––––––––––––––––––––––––––––––––––––––––––––––
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config: dict = yaml.safe_load(f) or {}

        # Cache default_params section
        self.default_params: dict = self.config.get("default_params", {})

    # ──── Tek satır döndüren getter’lar ──────────────────────────────────────
    def get_mode(self) -> str:
        return str(self.config.get("mode", "BACKTEST"))

    def get_debug(self) -> bool:
        return bool(self.config.get("debug", False))

    def get_risk_pct(self) -> float:
        return float(self.config.get("risk_pct", 0.0))

    def get_base_usdt_per_trade(self) -> float:
        return float(self.config.get("base_usdt_per_trade", 0.0))

    def get_max_concurrent(self) -> int:
        return int(self.config.get("max_concurrent", 1))

    def get_history_limit(self) -> int:
        return int(self.default_params.get("history_limit", 250))

    def get_expire_sec(self) -> int:
        ex = self.default_params.get("expire_sec", 300)
        return int(eval(ex)) if isinstance(ex, str) else int(ex)

    # ──── Tüm stratejilerdeki coin’leri toplayan getter ─────────────────────
    def get_coins(self) -> list[str]:
        """
        Stratejilerde tanımlı tüm coin’leri döndürür.
        Eğer aralarında 'ALL_USDT' varsa yalnızca ['ALL_USDT'] döner.
        """
        coins = set()
        for strat in self.config.get("strategies", []):
            for c in strat.get("coins", []):
                coins.add(c)
        if "ALL_USDT" in coins:
            return ["ALL_USDT"]
        return sorted(coins)

    # ──── Strateji girdilerini düzenleyen metot ─────────────────────────────
    def get_strategies(self) -> list[dict]:
        """
        Her strateji girdisinden:
          - name
          - coins
          - timeframe (tek değer)
          - params (teknik parametreler, list-or-scalar destekli)
          - effective_params (default_params + overrides)
        olacak şekilde bir liste döner.
        """
        raw_strats = self.config.get("strategies", [])
        strategies: list[dict] = []

        for strat in raw_strats:
            name            = strat["name"]
            coins           = strat.get("coins", [])
            timeframes      = strat.get("timeframes", [])
            params_block    = strat.get("params", {})
            overrides_block = strat.get("overrides", {})
            # Liste boyutu kontrolü
            for key, val in {**params_block, **overrides_block}.items():
                if isinstance(val, list) and len(val) != len(timeframes):
                    raise ValueError(
                        f"Config error: '{key}' list length ({len(val)}) != timeframes length ({len(timeframes)})"
                    )

            # Her timeframe için ayrı bir giriş oluştur
            for i, tf in enumerate(timeframes):
                # index veya scalar değeri çeken yardımcı
                def extract(block: dict, key: str):
                    v = block.get(key)
                    return v[i] if isinstance(v, list) else v

                # Teknik parametreler (atr_period, multiplier, vs.)
                per_tf_params = {
                    key: extract(params_block, key)
                    for key in params_block
                }

                # default_params’tan başla, overrides ile üzerine yaz
                eff = self.default_params.copy()
                for key in overrides_block:
                    eff[key] = extract(overrides_block, key)

                strategies.append({
                    "name":             name,
                    "coins":            coins,
                    "timeframe":        tf,
                    "params":           per_tf_params,
                    "effective_params": eff,
                })

        return strategies

    def get_api_keys(self) -> tuple[str, str]:
        """
        YAML içindeki api bölümü öncelikli,
        yoksa .env’den alır.
        """
        api_cfg = self.config.get("api", {})
        key    = api_cfg.get("key")    or self.API_KEY    or ""
        secret = api_cfg.get("secret") or self.API_SECRET or ""
        return key, secret
