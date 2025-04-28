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
        env_path: str | Path | None = None,
    ) -> None:
        # ––– .env ––––––––––––––––––––––––––––––––––––––––––––––––––––––––
        if env_path is None:
            # Locate project‑root/.env  → utils/../.env
            env_path = Path(__file__).resolve().parent.parent / ".env"
        env_path = Path(env_path)
        if env_path.exists():
            load_dotenv(env_path)
        else:
            raise FileNotFoundError(f".env file not found at {env_path}")

        # Expose env keys so that other modules can import them from here
        self.API_KEY: str | None = os.getenv("API_KEY")
        self.API_SECRET: str | None = os.getenv("API_SECRET")

        # ––– YAML ––––––––––––––––––––––––––––––––––––––––––––––––––––––––
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config: dict = yaml.safe_load(f) or {}

    # ––– convenience getters ––––––––––––––––––––––––––––––––––––––––––––
    def get_coins(self) -> list[str]:
        return self.config.get("coins", [])

    def get_timeframes(self) -> list[str]:
        return self.config.get("timeframes", [])

    def get_strategies(self) -> list[dict]:
        """Each element → {"name": str, "parameters": dict}"""
        return self.config.get("strategies", [])

    def get_api_keys(self) -> tuple[str, str]:
        """Return API keys (YAML overrides .env)."""
        api_cfg = self.config.get("api", {})
        key = api_cfg.get("key") or self.API_KEY or ""
        secret = api_cfg.get("secret") or self.API_SECRET or ""
        return key, secret

    def get_general(self) -> dict:
        return self.config.get("general", {})
