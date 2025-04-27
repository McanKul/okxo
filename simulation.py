# simulation.py  – FULL METRIC GRID
# -------------------------------------------------------------
#  python simulation.py                     # LOOK = 110
#  python simulation.py --look 200          # LOOK = 200
# -------------------------------------------------------------
from pathlib import Path
import argparse, json, sys
import numpy as np
import math

# ----------------------------- argümanlar ------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("--look", type=int, default=110, help="LOOKAHEAD bar sayısı")
args = ap.parse_args()
LOOK = args.look
# -----------------------------------------------------------------------------


ROOT = Path(__file__).resolve().parent
SIMU = ROOT / "simutations"

required = ("entry.npy", "prices.npy", "dirs.npy")   # + strat.npy opsiyonel
if any(not (SIMU / f).exists() for f in required):
    sys.exit("⚠  .npy dosyaları eksik – önce precompute_excurcions.py’yi çalıştırın.")

entry   = np.load(SIMU / "entry.npy")          # (K,)
prices  = np.load(SIMU / "prices.npy")         # (K, LOOK_MAX)
dirs    = np.load(SIMU / "dirs.npy")           # (K,)
if (SIMU / "strat.npy").exists():
    strat_id = np.load(SIMU / "strat.npy")     # (K,)
else:
    strat_id = None                            # opsiyonel

tp_levels  = np.arange(1, 50)     # 1-49 %
sl_levels  = np.arange(1, 50)
lev_levels = np.arange(1, 50)
CAPITAL    = 100.0                # 1 işlem nominal
DAY_BARS   = 60*24                # 1-dakikalık veride 1 gün

results = []

# ------------------------------------------------------------- helpers
def sharpe_ratio(pnls):
    if len(pnls) < 2:
        return 0.0
    mu  = np.mean(pnls)
    std = np.std(pnls, ddof=1)
    return 0.0 if std == 0 else (mu / std * math.sqrt(DAY_BARS / LOOK))

# ------------------------------------------------------------ main grid
for lev in lev_levels:
    tp_grid = tp_levels / lev / 100.0     # net yüzdeler
    sl_grid = sl_levels / lev / 100.0

    for tp_idx, tp_thr in enumerate(tp_grid):
        for sl_idx, sl_thr in enumerate(sl_grid):
            tp_pct = int(tp_levels[tp_idx])
            sl_pct = int(sl_levels[sl_idx])

            # toplama değişkenleri
            wins = losses = expires = 0
            hold_lengths, win_list, loss_list, pnl_list = [], [], [], []

            for k in range(len(entry)):
                dir_ = dirs[k]
                e_px = entry[k]
                path = prices[k, :LOOK]

                rel = (path / e_px - 1.0) * dir_

                hit_tp = np.where(rel >= tp_thr)[0]
                hit_sl = np.where(rel <= -sl_thr)[0]
                tp_ix = hit_tp[0] if hit_tp.size else None
                sl_ix = hit_sl[0] if hit_sl.size else None

                if tp_ix is not None and (sl_ix is None or tp_ix < sl_ix):
                    # -------- WIN ----------
                    wins += 1
                    hold_lengths.append(int(tp_ix) + 1)
                    pnl_rel =  tp_thr
                    win_list.append(pnl_rel)
                elif sl_ix is not None and (tp_ix is None or sl_ix < tp_ix):
                    # -------- LOSS ---------
                    losses += 1
                    pnl_rel = -sl_thr
                    loss_list.append(pnl_rel)
                else:
                    # -------- EXPIRE => LOSS (isteğe göre tut) ----------
                    expires += 1
                    losses  += 1
                    pnl_rel = float(rel[-1])
                    loss_list.append(pnl_rel)

                pnl_list.append(pnl_rel)

            total   = wins + losses
            if total == 0:          # bazen hiç trade olmayabilir
                continue

            winrate   = wins / total * 100
            avg_hold  = int(np.mean(hold_lengths)) if hold_lengths else 0

            ret_series = np.array(pnl_list)             # net % (kaldıraç sonrası)
            ret_abs    = ret_series * lev * CAPITAL     # $ seri (nominal 100$)

            sum_rel = ret_series.sum()
            avg_rel = sum_rel / total
            sum_abs = ret_abs.sum()
            avg_abs = sum_abs / total

            avg_win_rel  = np.mean(win_list)*100  if win_list  else 0.0
            avg_loss_rel = np.mean(loss_list)*100 if loss_list else 0.0

            # — Profit Factor & Expectancy —
            profit_factor = (-ret_series[ret_series>0].sum() /
                            ret_series[ret_series<0].sum()) if ret_series[ret_series<0].sum()!=0 else np.inf
            expectancy = (wins/total)*avg_win_rel + (losses/total)*avg_loss_rel

            # — Risk metrikleri —
            stdev = np.std(ret_series, ddof=1) * 100
            downside = np.std(ret_series[ret_series<0], ddof=1) * 100 if (ret_series<0).any() else 0.0
            sharpe  = 0.0 if stdev==0 else (avg_rel / stdev) * np.sqrt(DAY_BARS/LOOK)
            sortino = 0.0 if downside==0 else (avg_rel / downside) * np.sqrt(DAY_BARS/LOOK)

            # — Max Drawdown —
            equity_curve = np.cumprod(1 + ret_series)
            rolling_max  = np.maximum.accumulate(equity_curve)
            dd_series    = equity_curve/rolling_max - 1
            max_dd = dd_series.min()*100        # negatif değer

            results.append({
                "lev"        : int(lev),
                "tp"         : tp_pct,
                "sl"         : sl_pct,
                "WIN"        : int(wins),
                "LOSS"       : int(losses),
                "EXPIRE"     : int(expires),
                "TOTAL"      : int(total),
                "WIN_RATE"   : round(winrate, 3),
                "AVG_HOLD"   : avg_hold,
                "AVG_PNL%"   : round(avg_rel*100, 5),
                "AVG_PNL$"   : round(avg_abs, 5),
                "AVG_WIN%"   : round(avg_win_rel, 5),
                "AVG_LOSS%"  : round(avg_loss_rel, 5),
                "PROFIT_FACTOR": round(profit_factor, 5),
                "EXPECTANCY%": round(expectancy, 5),
                "STDEV%"     : round(stdev, 5),
                "SHARPE"     : round(sharpe, 4),
                "SORTINO"    : round(sortino, 4),
                "MAX_DD%"    : round(max_dd, 3)
            })

# -------------------- yazdır & özet --------------------
out = SIMU / f"results_LOOK{LOOK}_LEV.jsonl"
with out.open("w", encoding="utf8") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

best_wr  = max(results, key=lambda x: x["WIN_RATE"])
best_exp = max(results, key=lambda x: x["EXPECTANCY%"])

print(f"✓  {len(results):,} kombinasyon değerlendirildi  →  {out.name}")
print(f"🏆  En yüksek WIN_RATE : lev={best_wr['lev']}× TP={best_wr['tp']}% "
      f"SL={best_wr['sl']}%  → {best_wr['WIN_RATE']:.2f}% "
      f"(AvgPnL$ {best_wr['AVG_PNL$']:.2f})")
print(f"🏆  En yüksek EXPECTANCY: lev={best_exp['lev']}× TP={best_exp['tp']}% "
      f"SL={best_exp['sl']}%  → {best_exp['EXPECTANCY%']:.3f}% "
      f"(ProfitFactor {best_exp['PROFIT_FACTOR']:.2f})")

# --------- İstersen buradan sonra strateji kırılımı ekleyebilirsin ----------
# if strat_id is not None:
#     for sid in np.unique(strat_id):
#         mask = strat_id == sid
#         ...  aynı hesabı sadece mask'li trade'ler üzerinde yap
