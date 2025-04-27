"""
BTC 1-dakikalık veride sinyal üreten tüm işlemler için:
* entry_price
* forward price path (LOOK bars)
* işlem yönü (+1 BUY, -1 SELL)
* max favourable / adverse excursion (MFE / MAE, %)

İlk önce bunu çalıştırın; sonucu simutations/ klasörüne .npy dosyaları
olarak yazar.
"""
from pathlib import Path
import sys, numpy as np, pandas as pd
from multiple import *
from gpt import *

# --------------------------------- parametreler ---------------------------------
LOOK   = 110      # ileriye bakılan bar sayısı   (python precompute_excurcions.py --look 200)
WIN    = 100      # geriye bakılan pencere
# -------------------------------------------------------------------------------

# komut satırından --look N
if "--look" in sys.argv:
    LOOK = int(sys.argv[sys.argv.index("--look") + 1])

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data/BTC_1minute.csv"
df   = pd.read_csv(DATA)

close  = df.close .astype(float).to_numpy()
high   = df.high  .astype(float).to_numpy()
low    = df.low   .astype(float).to_numpy()
volume = df.volume.astype(float).to_numpy()

STRATEGIES = {
   "supertrend_strategy": supertrend_strategy,
}

STRAT_ID = {name: i for i, name in enumerate(STRATEGIES.keys())}
strat_ids = []

entry_prices, dirs, mfe_list, mae_list = [], [], [], []
paths_fwd = []

for idx in range(WIN, len(close) - LOOK):
    c_win = close [idx-WIN:idx]
    h_win = high  [idx-WIN:idx]
    l_win = low   [idx-WIN:idx]
    v_win = volume[idx-WIN:idx]

    for name,f in STRATEGIES.items():
        sig = f(c_win, h_win, l_win, v_win)
        if sig not in ("BUY", "SELL"):
            continue

        direction =  1 if sig == "BUY"  else -1
        fwd_prices = close[idx+1 : idx+1+LOOK]

        rel = (fwd_prices / close[idx] - 1.0) * direction   # % yönlü getiri
        mfe = rel.max() * 100
        mae = -rel.min() * 100

        entry_prices.append(close[idx])
        dirs.append(direction)
        paths_fwd.append(fwd_prices)
        mfe_list.append(mfe)
        mae_list.append(mae)
        strat_ids.append(STRAT_ID[name]) 

out = ROOT / "simutations"
out.mkdir(exist_ok=True)

np.save(out/"entry.npy",  np.array(entry_prices, dtype=np.float32))
np.save(out/"dirs.npy",   np.array(dirs,        dtype=np.int8))
np.save(out/"prices.npy", np.array(paths_fwd,   dtype=np.float32))
np.save(out/"mfe.npy",    np.array(mfe_list,    dtype=np.float32))
np.save(out/"mae.npy",    np.array(mae_list,    dtype=np.float32))
np.save(out/"strat.npy",  np.array(strat_ids, dtype=np.int8))   # ③


print(f"✓  {len(entry_prices):,} trade kaydedildi  →  {out.relative_to(ROOT)}")
