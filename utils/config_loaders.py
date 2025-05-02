"""Configuration loader for the trading bot.

This module centralises access to:
  • Environment variables defined in a project‑root .env file
  • Structured settings stored in YAML (default: config/config.yaml)

It intentionally *does not* import any strategy modules to avoid circular
imports.
"""

from __future__ import annotations

import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

__all__ = [
    "ConfigLoader",
]


class ConfigLoader:
    """Read .env and YAML files, exposing helpers for commonly‑used fields."""

    def __init__(
        self,
        config_path: str | Path = "config/config.yaml",
        env_path: str | Path = "config/.env"
    ) -> None:
        # ––– .env ––––––––––––––––––––––––––––––––––––––––––––––––––––––––
        if env_path is None:
            # Locate project‑root/.env  → utils/../.env
            env_path = Path(__file__).resolve().parent.parent / ".env"
            
        if not env_path.exists():
            raise FileNotFoundError(f".env file not found at {env_path}")
        
        load_dotenv(env_path)
        # Expose env keys so that other modules can import them from here
        self.API_KEY: str | None = os.getenv("API_KEY")
        self.API_SECRET: str | None = os.getenv("API_SECRET")

        # ––– YAML ––––––––––––––––––––––––––––––––––––––––––––––––––––––––
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config: dict = yaml.safe_load(f) or {}

        self.default_params = self.config.get("default_params", {})
        
        
    # ––– convenience getters ––––––––––––––––––––––––––––––––––––––––––––
    def get_coins(self) -> list[str]:
        return self.config.get("coins", [])

    def get_timeframes(self) -> list[str]:
        return self.config.get("timeframes", [])

    def get_strategies(self) -> list[dict]:
        strategies = []
        for strat in self.config.get("strategies", []):
            effective_params = self.default_params.copy()
            effective_params.update(strat.get("overrides", {}))

            strategies.append({
                "name": strat["name"],
                "params": strat["params"],
                "timeframes": strat.get("timeframes", ["1h"]),
                "effective_params": effective_params
            })
        return strategies

    def get_api_keys(self) -> tuple[str, str]:
        """Return API keys (YAML overrides .env)."""
        api_cfg = self.config.get("api", {})
        key = api_cfg.get("key") or self.API_KEY or ""
        secret = api_cfg.get("secret") or self.API_SECRET or ""
        return key, secret

    def get_general(self) -> dict:
        return self.config.get("general", {})
    
    def get_base_usdt_per_trade(self) -> float:
        return self.config.get("base_usdt_per_trade", 0.0)
    

    def get_max_concurrent(self) -> int:
        return self.config.get("max_concurrent", 1)
    

    

    
    def get_expire_sec(self) -> int:
        expire_sec = self.default_params.get("expire_sec", 300)
        if isinstance(expire_sec, str):
            return eval(expire_sec)
        return expire_sec

    def get_history_limit(self) -> int:
        return self.config.get("history_limit", 250)
    
    def get_debug(self) ->bool:
        return self.config.get("debug", False)
    
    def get_mode(self) ->str:
        return self.config.get("mode", "BACKTEST")
    
    def get_risk_pct(self) ->float:
        return self.config.get("risk_pct",0)
    