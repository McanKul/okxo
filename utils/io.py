# utils/io.py  (yeni dosya)
from pathlib import Path
import pandas as pd

def load_ohlcv_csv(path: Path) -> pd.DataFrame:
    """
    Binance spot/futures veya kendi arşiv CSV’lerini içeri alır.
    - Zaman kolonu olarak: timestamp | open_time | date | time ... ilk eşleşeni kullanır
    - Metin ISO-8601 ise doğrudan parse edilir
    - Sayısal (ms) ise unit="ms" ile dönüştürülür
    - Gereksiz kolonları atar, sütun adlarını lowercase yapar
    Dönen DF => datetime index + ['open','high','low','close','volume']
    """
    df = pd.read_csv(path)
    cols_lower = {c.lower(): c for c in df.columns}

    # ---- timestamp kolonu bul -------------------------------------------------
    ts_col = next((cols_lower[k] for k in
                   ("timestamp", "open_time", "time", "date")
                   if k in cols_lower), df.columns[0])

    # ---- datetime’e çevir ------------------------------------------------------
    if pd.api.types.is_numeric_dtype(df[ts_col]):
        df[ts_col] = pd.to_datetime(df[ts_col], unit="ms")
    else:
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")

    df = df.set_index(ts_col)

    # ---- isimleri normalize et -------------------------------------------------
    rename_map = {c: c.lower() for c in df.columns}
    df = df.rename(columns=rename_map)

    keep = ["open", "high", "low", "close", "volume"]
    missing = [k for k in keep if k not in df.columns]
    if missing:
        raise ValueError(f"CSV eksik kolon(lar): {missing}")

    return df[keep].astype(float)
