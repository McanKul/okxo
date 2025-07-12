#!/usr/bin/env python3
import os, threading
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as anim
from collections import deque
from binance import Client
from binance import ThreadedWebsocketManager  # python-binance ≥1.0.19
"""
bize tick verilerini görmek için kullanılıyor.
#todo solid kavramlarına uygun hale getirilecek.. ve ayrı bir dosyaya alınacka şimdilik burada kalabilir
"""
# ───── Parametreler ──────────────────────────────────────────────────────────
SYMBOL       = "BTCUSDT"      # BÜYÜK harf!
INTERVAL     = "1m"
MAX_POINTS   = 120            # grafikte tutulacak mum adedi
UPDATE_MS    = 1_000          # ms: grafik yenileme süresi

# ───── Veri yapıları ────────────────────────────────────────────────────────
data_lock = threading.Lock()
times, closes = deque(maxlen=MAX_POINTS), deque(maxlen=MAX_POINTS)

# ───── Başlangıçta son MAX_POINTS mumu REST ile doldur ──────────────────────
client = Client()                         # key/secret gerekmez, sadece okuma
hist = client.get_klines(symbol=SYMBOL,
                         interval=Client.KLINE_INTERVAL_1MINUTE,
                         limit=MAX_POINTS)
for r in hist:
    times.append(pd.to_datetime(r[0], unit="ms"))
    closes.append(float(r[4]))

# ───── WebSocket callback ───────────────────────────────────────────────────
def handle_socket(msg):
    """Her gelen kline mesajında zaman & close'u güncelle."""
    if msg.get("e") != "kline":
        return
    k = msg["k"]
    t = pd.to_datetime(k["t"], unit="ms")
    c = float(k["c"])

    with data_lock:
        if times and t == times[-1]:
            closes[-1] = c       # aynı dakika → fiyat güncelle
        else:
            times.append(t)
            closes.append(c)

# ───── WebSocket'i başlat ───────────────────────────────────────────────────
twm = ThreadedWebsocketManager()
twm.start()
twm.start_kline_socket(callback=handle_socket,
                       symbol=SYMBOL,
                       interval=INTERVAL)

# ───── Matplotlib canlı çizgi grafiği ───────────────────────────────────────
plt.style.use("ggplot")
fig, ax = plt.subplots()
line, = ax.plot([], [], lw=1.5)

def init():
    ax.set_xlabel("Time");  ax.set_ylabel("Close")
    return line,

def update(_):
    with data_lock:
        if not times: return line,
        x, y = list(times), list(closes)


    line.set_data(x, y)
    ax.relim();  ax.autoscale_view()
    ax.set_title(f"{SYMBOL} close = {y[-1]:,.2f}")
    fig.autofmt_xdate()
    return line,

ani = anim.FuncAnimation(fig, update, init_func=init,
                         interval=UPDATE_MS, blit=False,
                         cache_frame_data=False)     # uyarıyı da susturur
plt.show()
