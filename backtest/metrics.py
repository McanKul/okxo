# backtest/metrics.py
import numpy as np
import pandas as pd

def sharpe_ratio(equity_curve, risk_free_rate=0.0):
    """
    Equity curve'in (zaman serisi bakiye) günlük getirilerinden Sharpe oranını hesaplar.
    risk_free_rate: yıllık risksiz getiri (varsayılan 0 kabul ediliyor).
    """
    returns = equity_curve.pct_change().dropna()
    excess_returns = returns - (risk_free_rate/252)  # Günlük riskfreesiz
    if excess_returns.std() == 0:
        return np.nan
    sharpe = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
    return sharpe

def sortino_ratio(equity_curve, target=0.0):
    """
    Sortino oranı hesaplar (ayrıca riski hedef altında kalma olarak alır).
    target: Hedef getiri (varsayılan 0).
    """
    returns = equity_curve.pct_change().dropna()
    downside_returns = returns[returns < target]
    # Downside volatility (hedef altı oynaklık)
    if len(downside_returns) == 0:
        return np.nan
    sigma_down = downside_returns.std()
    if sigma_down == 0:
        return np.nan
    sortino = np.sqrt(252) * ((returns.mean() - target) / sigma_down)
    return sortino

def max_drawdown(equity_curve):
    """
    Maksimum drawdown hesaplar: zirve-dip azami düşüş yüzdesi.
    """
    cum_max = equity_curve.cummax()
    drawdowns = (equity_curve - cum_max) / cum_max
    max_dd = drawdowns.min()
    return abs(max_dd)

def profit_factor(trades):
    """
    Profit Factor: kazançlı işlemlerin toplamı / zararlı işlemlerin toplamı (pozitif değerle)
    """
    if len(trades) == 0:
        return np.nan
    wins = [t for t in trades if t > 0]
    losses = [abs(t) for t in trades if t < 0]
    if sum(losses) == 0:
        return np.nan
    pf = sum(wins) / sum(losses)
    return pf

def expectancy(trades):
    """
    Expectancy: Ortalama işlem getirisi * kazanma oranı - zarar oranı * ortalama zarar.
    """
    n = len(trades)
    if n == 0:
        return 0
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    win_rate = len(wins)/n
    loss_rate = len(losses)/n
    avg_win = np.mean(wins) if wins else 0
    avg_loss = -np.mean(losses) if losses else 0
    exp = (win_rate * avg_win) - (loss_rate * avg_loss)
    return exp

def calculate_metrics(equity_series, trades):
    """
    Tüm metrikleri hesaplayıp bir sözlükte döndürür.
    """
    metrics = {
        'Sharpe': sharpe_ratio(equity_series),
        'Sortino': sortino_ratio(equity_series),
        'MaxDrawdown': max_drawdown(equity_series),
        'ProfitFactor': profit_factor(trades),
        'Expectancy': expectancy(trades),
        'TotalProfit': equity_series.iloc[-1] - equity_series.iloc[0]
    }
    return metrics
