"""Simple vectorised back‑testing engine with long **and** short support.

Signal convention (per‑bar):
    +1  → open/hold LONG      (close SHORT if one is open)
     0  → FLAT  (close any open position)
    −1  → open/hold SHORT     (close LONG  if one is open)

A *position* is represented by an integer:
    +1 → long, −1 → short, 0 → no position.

The engine assumes *one trade at a time* (no pyramiding) and full‑balance
allocation per trade for simplicity.
"""
from __future__ import annotations

from typing import List, Dict, Any
import pandas as pd

__all__ = ["BacktestEngine"]


class BacktestEngine:  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        data: pd.DataFrame,
        strategy,
        initial_balance: float = 1_000.0,
    ) -> None:
        """Create a new engine.

        Parameters
        ----------
        data : pd.DataFrame
            Must have datetime index and columns ['open', 'high', 'low', 'close', 'volume']
        strategy : BaseStrategy
            Object implementing ``generate_signals(df) -> pd.Series`` with the
            signal convention detailed in this module docstring.
        initial_balance : float, default 1000.0
            Starting capital.
        """
        self.data = data.copy()
        self.strategy = strategy
        self.initial_balance = float(initial_balance)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        df = self.data.copy()
        signals: pd.Series = self.strategy.generate_signals(df).reindex(df.index)

        balance: float = self.initial_balance
        position: int = 0          # +1 long, −1 short, 0 flat
        entry_price: float | None = None

        equity_curve: List[float] = []
        trades: List[float] = []   # realised PnL per trade

        for ts, price in df["close"].items():
            sig = signals.loc[ts]

            # --- Position management -----------------------------------
            if position == 0:
                if sig == 1:  # open long
                    position = 1
                    entry_price = price
                elif sig == -1:  # open short
                    position = -1
                    entry_price = price
            elif position == 1:  # currently long
                if sig <= 0:  # close long (sig 0 or -1)
                    pnl = price - entry_price  # long profit
                    balance += pnl
                    trades.append(pnl)
                    position = 0
                    entry_price = None
                    # If signal == -1, open new short on next iteration
                    if sig == -1:
                        position = -1
                        entry_price = price
            elif position == -1:  # currently short
                if sig >= 0:  # close short (sig 0 or +1)
                    pnl = entry_price - price  # short profit
                    balance += pnl
                    trades.append(pnl)
                    position = 0
                    entry_price = None
                    if sig == 1:  # open new long immediately
                        position = 1
                        entry_price = price

            # --- Equity curve -----------------------------------------
            if position == 1:  # unrealised long
                equity_curve.append(balance + (price - entry_price))
            elif position == -1:  # unrealised short
                equity_curve.append(balance + (entry_price - price))
            else:
                equity_curve.append(balance)

        # ------------------------------------------------------------------
        # Liquidate any open position at the last close price
        # ------------------------------------------------------------------
        if position != 0 and entry_price is not None:
            final_price = df["close"].iloc[-1]
            pnl = (final_price - entry_price) if position == 1 else (entry_price - final_price)
            balance += pnl
            trades.append(pnl)
            equity_curve[-1] = balance

        return {
            "equity_curve": pd.Series(equity_curve, index=df.index, name="equity"),
            "trades": trades,
            "final_balance": balance,
        }
