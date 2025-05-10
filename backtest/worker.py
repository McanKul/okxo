# backtest/worker.py
from backtest.backtester import BacktestEngine
from utils.config_loaders import ConfigLoader
from data.data_fetcher import DataFetcher

def run_backtest_task(task):
    """
    task: tuple (symbol, timeframe, strategy_class, strategy_params, initial_balance, date_range)
    Her görevde bir coinin bir zaman diliminde verilen strateji ile backtestini yapar.
    """
    symbol, timeframe, StrategyClass, params, initial_balance, start_date, end_date = task
    
    # 1) Veri çek
    fetcher = DataFetcher(ConfigLoader.get_api_keys[0], ConfigLoader.get_api_keys[1])
    df = fetcher.fetch_ohlcv(symbol, timeframe, since=start_date)
    if df.empty:
        return None
    
    # 2) Strateji yarat
    strategy = StrategyClass(params)
    
    # 3) Backtest çalıştır
    engine = BacktestEngine(df, strategy, initial_balance=initial_balance)
    result = engine.run()
    
    # 4) Metrikleri hesaplayıp döndür (daha sonra metrics modülüne taşıyabiliriz)
    from backtest.metrics import calculate_metrics
    equity_series = result['equity_curve']
    trades = result['trades']
    metrics = calculate_metrics(equity_series, trades)
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'strategy': StrategyClass.__name__,
        'metrics': metrics
    }
