# main.py - Ticaret botu giriş noktası (LIVE veya BACKTEST modu).
import asyncio
from live.broker_binance import BinanceBroker
from utils.logger import setup_logger
import sys
import logging

from pathlib import Path


from binance import AsyncClient
from live.live_engine import LiveEngine
from utils.config_loaders import ConfigLoader

async def run_backtest(cfg,log):
    """
    Backtest'i yürütür (Executor içinde, event loop'u bloklamamak için).
    """
    # Backtest için gerekli modüller
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
        try:
            pair = f"{sym.replace('USDT', '')}/USDT"
            df = DataFetcher().fetch_ohlcv(pair, tf)
        except Exception as e:
            log.error("Backtest için veri alınamadı: %s", e)
            return None

    strategy = load_strategy(strat_cfg)
    engine = BacktestEngine(df, strategy, initial_balance=cfg.get("initial_balance", 1000))
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, engine.run)
    return result

async def async_main():
    # Yapılandırma dosyasını yükle
    ROOT = Path(__file__).parent
    CONFIG_PATH = ROOT / "config" / "config.yaml"
    ENV_PATH = ROOT / "config" / ".env"
    try:
        cfg = ConfigLoader(CONFIG_PATH,ENV_PATH)
        log = setup_logger("Main", level=logging.DEBUG if cfg.get_debug() else logging.INFO)

    except FileNotFoundError as e:
        sys.exit(f"⚠ Yapılandırma dosyası bulunamadı: {e}")



    mode = cfg.get_mode().upper()

    if mode == "BACKTEST":
        result = await run_backtest(cfg,log)
        if result:
            print("Final bakiye:", result.get("final_balance", "N/A"))

    elif mode == "LIVE":

        api_key,api_secret = cfg.get_api_keys()
        
        if not (api_key and api_secret):
            sys.exit("⚠ LIVE modu için API_KEY ve API_SECRET tanımlı değil (config veya .env).")

        # Binance AsyncClient oluştur
        try:
            client = await AsyncClient.create(api_key, api_secret)
        except Exception as e:
            sys.exit(f"⚠ Binance istemcisi oluşturulamadı: {e}")

        # Risk yüzdesine göre işlem başına sermayeyi hesapla
        if cfg.get_risk_pct() is not None:
            try:
                account_info = await client.futures_account_balance()
                usdt_balance = 0.0
                for asset in account_info:
                    if asset['asset'] == 'USDT':
                        usdt_balance = float(asset['balance'])
                        break
                risk_pct = cfg.get_risk_pct() / 100.0
                base_usdt = usdt_balance * risk_pct
                # Güncellenen temel işlem tutarını config'e yaz
                log.info("Risk yüzdesi kullanıldı: Hesap bakiyesi=%.2f, risk_pct=%.2f%%, işlem başına USDT=%.2f",
                             usdt_balance, cfg.get_risk_pct(), base_usdt)
            except Exception as e:
                log.error("Hesap bilgisi alınamadı: %s", e)

        broker = BinanceBroker(client)            # ← sarmalayıcı
        engine = LiveEngine(cfg, broker)
        try:
            await engine.run()
        except Exception as e:
            log.error("LiveEngine çalışırken hata: %s", e)
        finally:
            await client.close_connection()

    else:
        sys.exit(f"⚠ Geçersiz mod: {mode} (BACKTEST veya LIVE seçilmeli)")

if __name__ == "__main__":
    asyncio.run(async_main())
