"""
main.py - Entry point for trading bot (live or backtest mode).

Requires:
- python-binance (AsyncClient)
- PyYAML (for configuration)
- Other modules: pandas, strategies, backtest, data_fetcher as needed.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml

from binance import AsyncClient
from live.live_engine import LiveEngine

async def run_backtest(cfg):
    """
    Run backtest in executor to avoid blocking the event loop.
    """
    # Imports for backtesting (assumes these modules are available)
    from utils.io import load_ohlcv_csv
    from strategies import load_strategy
    from backtest.backtester import BacktestEngine
    from data.data_fetcher import DataFetcher

    sym = cfg["coins"][0]
    tf = cfg["timeframes"][0]
    strat_cfg = cfg["strategies"][0]
    csv_path = Path(f"data/{sym}_{tf}.csv")

    if csv_path.exists():
        df = load_ohlcv_csv(csv_path)
    else:
        # Fetch data if not available
        try:
            pair = f"{sym.replace('USDT', '')}/USDT"
            df = DataFetcher().fetch_ohlcv(pair, tf)
        except Exception as e:
            logging.error("Failed to fetch data for backtest: %s", e)
            return None

    strategy = load_strategy(strat_cfg)
    engine = BacktestEngine(df, strategy, initial_balance=cfg.get("initial_balance", 1000))
    # Run backtest synchronously in executor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, engine.run)
    return result

async def async_main():
    # Load configuration
    ROOT = Path(__file__).parent
    CONFIG_PATH = ROOT / "config"/"config.yaml"
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit(f"⚠ Configuration file not found: {CONFIG_PATH}")

    logging.basicConfig(
        level=logging.INFO if cfg.get("debug", False) else logging.WARNING,
        format="%(asctime)s %(levelname)s: %(message)s"
    )

    mode = cfg.get("mode", "BACKTEST").upper()

    if mode == "BACKTEST":
        result = await run_backtest(cfg)
        if result:
            print("Final balance:", result.get("final_balance", "N/A"))

    elif mode == "LIVE":
        
        # Ensure API keys are set
        load_dotenv(ROOT / "config" / ".env", override=False)
        api_key = cfg.get("api_key") or os.getenv("API_KEY")
        api_secret = cfg.get("api_secret") or os.getenv("API_SECRET")
        if not (api_key and api_secret):
            sys.exit("⚠ LIVE mode requires API_KEY and API_SECRET in config or .env")

        # Initialize Binance async client
        
        client = await AsyncClient.create(api_key, api_secret)
        engine = LiveEngine(cfg, client)
        await engine.run()
        # Close Binance client connection
        await client.close_connection()

    else:
        sys.exit(f"⚠ Invalid mode: {mode}  (choose BACKTEST or LIVE)")

if __name__ == "__main__":
    asyncio.run(async_main())
